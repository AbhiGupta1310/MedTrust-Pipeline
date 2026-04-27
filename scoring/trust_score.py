from __future__ import annotations

"""
Trust Score System
Calculates a trust/reliability score (0-1) for scraped content based on
multiple credibility factors (heuristics) AND an LLM-powered Fact Checking layer
to analyze bias, logic, and unverified claims.
"""

import logging
import re
from datetime import datetime
from urllib.parse import urlparse
from typing import Optional
from pydantic import BaseModel, Field

from config import (
    TRUST_WEIGHTS,
    HIGH_AUTHORITY_DOMAINS,
    MEDIUM_AUTHORITY_DOMAINS,
    LOW_AUTHORITY_DOMAINS,
    KNOWN_ORGANIZATIONS,
    KNOWN_AUTHORS,
    MEDICAL_DISCLAIMER_KEYWORDS,
    KNOWN_INSTITUTIONS,
)

from utils.llm_client import get_instructor_client, DEFAULT_LLM_MODEL

logger = logging.getLogger(__name__)


# Schema for LLM Fact-Checking layer
class FactCheckResult(BaseModel):
    logical_fallacies_present: bool = Field(description="Are there glaring logical fallacies in text?")
    fallacy_description: str = Field(description="Short description of the fallacies, or empty if none.")
    unverified_medical_claims: bool = Field(description="Does it make health/medical claims without citation?")
    overall_bias_score: float = Field(description="A score from 0.0 (neutral) to 1.0 (extremely biased/propaganda). Consider promotional language, one-sided presentation, and conflicts of interest.")
    evidence_quality: float = Field(description="Score from 0.0 (no evidence, speculative) to 1.0 (rigorous, well-cited, peer-reviewed methodology). Evaluate citation density, methodology rigor, and statistical backing.")


def calculate_trust_score(source_data: dict) -> dict:
    """
    Calculate the trust score for a scraped source.
    """
    url = source_data.get("source_url", "")
    source_type = source_data.get("source_type", "")
    author = source_data.get("author", "")
    content = source_data.get("content", "")
    published_date = source_data.get("published_date")
    citation_count = source_data.get("citation_count", 0)
    affiliations = source_data.get("affiliations", [])
    coi_statement = source_data.get("conflict_of_interest", "")

    # 1. Calculate heuristic factor scores
    author_score = score_author_credibility(author, source_type, affiliations)
    citation_score = score_citations(citation_count, source_type, published_date)
    domain_score = score_domain_authority(url)
    recency_score_val = score_recency(published_date)
    disclaimer_score = score_medical_disclaimer(content, source_type)

    # 2. Heuristic specific quality penalty
    heuristic_penalty = _calculate_quality_penalty(content, source_data)

    # 2.5. Non-English Content Penalty
    if content:
        try:
            from langdetect import detect, LangDetectException
            lang = detect(content)
            if lang != "en":
                heuristic_penalty += 0.05
                logger.info("Non-English content detected, applied 0.05 penalty.")
        except Exception:
            pass

    # 3. Conflict of Interest penalty
    coi_penalty = 0.0
    if coi_statement and len(coi_statement.strip()) > 0:
        # Only penalize if the COI indicates actual financial/commercial interest
        coi_lower = coi_statement.lower()
        conflict_keywords = ["shareholder", "cofounder", "co-founder", "consultant",
                             "advisory", "patent", "equity", "honoraria", "funding",
                             "employee", "stock", "financial interest", "commercial"]
        if any(kw in coi_lower for kw in conflict_keywords):
            coi_penalty = 0.05
            logger.info(f"COI with financial conflict detected, applying {coi_penalty} penalty")

    # 4. LLM Fact-Checking Layer
    llm_fact_check = _llm_fact_check(content, coi_statement)

    # Convert LLM feedback into an additional mathematical penalty
    llm_penalty = 0.0
    if llm_fact_check.logical_fallacies_present:
        llm_penalty += 0.15
    if llm_fact_check.unverified_medical_claims:
        llm_penalty += 0.25
    llm_penalty += (llm_fact_check.overall_bias_score * 0.3)  # Max 0.3 penalty for extreme bias
    # Low evidence quality increases penalty
    evidence_penalty = (1.0 - llm_fact_check.evidence_quality) * 0.1  # Max 0.1 for no evidence
    llm_penalty += evidence_penalty

    total_penalty = min(heuristic_penalty + coi_penalty + llm_penalty, 0.8)

    # Weighted sum
    weights = TRUST_WEIGHTS
    raw_score = (
        weights["author_credibility"] * author_score
        + weights["citation_count"] * citation_score
        + weights["domain_authority"] * domain_score
        + weights["recency"] * recency_score_val
        + weights["medical_disclaimer"] * disclaimer_score
    )

    # Apply penalties
    final_score = max(0.0, min(1.0, raw_score * (1 - total_penalty)))
    final_score = round(final_score, 3)

    return {
        "trust_score": final_score,
        "breakdown": {
            "author_credibility": {
                "score": round(author_score, 3),
                "weight": weights["author_credibility"],
                "weighted": round(author_score * weights["author_credibility"], 3),
            },
            "citation_count": {
                "score": round(citation_score, 3),
                "weight": weights["citation_count"],
                "weighted": round(citation_score * weights["citation_count"], 3),
            },
            "domain_authority": {
                "score": round(domain_score, 3),
                "weight": weights["domain_authority"],
                "weighted": round(domain_score * weights["domain_authority"], 3),
            },
            "recency": {
                "score": round(recency_score_val, 3),
                "weight": weights["recency"],
                "weighted": round(recency_score_val * weights["recency"], 3),
            },
            "medical_disclaimer": {
                "score": round(disclaimer_score, 3),
                "weight": weights["medical_disclaimer"],
                "weighted": round(disclaimer_score * weights["medical_disclaimer"], 3),
            },
            "heuristic_quality_penalty": round(heuristic_penalty, 3),
            "coi_penalty": round(coi_penalty, 3),
            "llm_factcheck_penalty": round(llm_penalty, 3),
            "llm_bias_score": round(llm_fact_check.overall_bias_score, 3),
            "llm_evidence_quality": round(llm_fact_check.evidence_quality, 3),
            "llm_fallacy_detected": llm_fact_check.logical_fallacies_present,
            "conflict_of_interest": coi_statement if coi_statement else None,
        },
    }

def _llm_fact_check(content: str, coi_statement: str = "") -> FactCheckResult:
    """
    Passes content to an LLM to evaluate bias, unverified claims, and logic.
    COI information is passed as context for more accurate evaluation.
    """
    if not content or len(content) < 50:
        return FactCheckResult(
            logical_fallacies_present=False, 
            fallacy_description="", 
            unverified_medical_claims=False, 
            overall_bias_score=0.0,
            evidence_quality=0.5
        )
        
    client = get_instructor_client()
    
    # Cap text length to prevent context explosion
    eval_text = content[:15000]
    
    # Build context-aware system prompt
    coi_context = ""
    if coi_statement:
        coi_context = (
            f"\n\nIMPORTANT CONTEXT: The author(s) have declared the following conflict of interest: "
            f"'{coi_statement}'. Factor this into your bias evaluation — content from authors "
            f"with financial stakes in commercial outcomes should receive higher bias scores."
        )
    
    try:
        logger.info("Executing LLM Fact-Check routine...")
        result = client.chat.completions.create(
            model=DEFAULT_LLM_MODEL,
            response_model=FactCheckResult,
            messages=[
                {
                    "role": "system", 
                    "content": (
                        "You are an expert scientific peer-reviewer and logician. "
                        "Analyze the provided text for logical fallacies, extreme biases, and unverified medical claims. "
                        "CRITICAL EXCEPTION: If the author is explicitly quoting a fallacy to debunk it, "
                        "or presenting false information as an *example* of an error (e.g., discussing AI hallucinations "
                        "or analyzing misinformation), DO NOT flag it as a fallacy committed by the author. "
                        "Evaluate the author's primary argument, not the examples they critique. "
                        "For evidence_quality: examine how well claims are supported — does it cite specific studies, "
                        "provide data/statistics, describe methodology? Pure opinion scores low, "
                        "rigorous peer-reviewed research with methodology details scores high."
                        + coi_context
                    )
                },
                {"role": "user", "content": f"Review this text: {eval_text}"}
            ],
            temperature=0.0
        )
        return result
    except Exception as e:
        logger.warning(f"LLM Fact-Check failed: {e}. Defaulting to neutral.")
        return FactCheckResult(
            logical_fallacies_present=False, 
            fallacy_description="Fact-check failed due to API error", 
            unverified_medical_claims=False, 
            overall_bias_score=0.0,
            evidence_quality=0.5
        )


# ============================================================
# INDIVIDUAL FACTOR SCORING FUNCTIONS
# ============================================================


def score_author_credibility(author: str, source_type: str, affiliations: list = None) -> float:
    """Score author credibility based on name matching AND institutional affiliation."""
    if not author or author.strip().lower() in ("unknown", ""):
        return 0.2

    authors = [a.strip() for a in author.split(",")]

    if len(authors) > 1:
        scores = [_score_single_author(a) for a in authors]
        base_score = sum(scores) / len(scores)
    else:
        base_score = _score_single_author(author)

    # Boost score if affiliations match known research institutions
    if affiliations:
        aff_text = " ".join(affiliations).lower()
        for inst in KNOWN_INSTITUTIONS:
            if inst.lower() in aff_text:
                base_score = max(base_score, 0.8)
                break

    return round(base_score, 3)


def _score_single_author(author: str) -> float:
    author_lower = author.lower()
    for org in KNOWN_ORGANIZATIONS:
        if org.lower() in author_lower: return 1.0
    for known in KNOWN_AUTHORS:
        if known.lower() in author_lower: return 0.85
    return 0.3


def _parse_date(date_str: str | None) -> datetime | None:
    """Helper to parse various date formats reliably."""
    if not date_str:
        return None
    
    if isinstance(date_str, datetime):
        return date_str

    for fmt in ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"]:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
            
    try:
        from dateutil import parser as date_parser
        return date_parser.parse(date_str)
    except Exception:
        return None


def score_citations(citation_count: int | None, source_type: str, published_date: str = None) -> float:
    """Age-adjusted citation scoring: normalizes by publication age."""
    if source_type != "pubmed": return 0.5  
    if citation_count is None or citation_count <= 0: return 0.3

    # Calculate age-adjusted citation rate
    dt = _parse_date(published_date)
    years_old = max(0.5, (datetime.now() - dt).days / 365.25) if dt else 1.0

    citations_per_year = citation_count / years_old
    # 10+ citations/year = perfect score, linearly interpolated
    score = min(1.0, citations_per_year / 10.0)
    return max(round(score, 3), 0.3)


def score_domain_authority(url: str) -> float:
    if not url: return 0.3
    try:
        domain = urlparse(url).netloc.lower().replace("www.", "")
    except Exception:
        return 0.3

    for high_domain in HIGH_AUTHORITY_DOMAINS:
        if high_domain in domain or domain.endswith(high_domain): return 1.0
    for med_domain in MEDIUM_AUTHORITY_DOMAINS:
        if med_domain in domain or domain.endswith(med_domain): return 0.6
    for low_domain in LOW_AUTHORITY_DOMAINS:
        if low_domain in domain or domain.endswith(low_domain): return 0.3

    return 0.4  


def score_recency(published_date: str | None) -> float:
    """Score content based on how recently it was published."""
    dt = _parse_date(published_date)
    if not dt:
        return 0.2
        
    try:
        age_days = (datetime.now() - dt).days
        if age_days <= 180: return 1.0  # Includes future dates (highly relevant updates)
        elif age_days < 365: return 0.8
        elif age_days < 730: return 0.6
        elif age_days < 1095: return 0.4
        else: return 0.2
    except Exception:
        return 0.2


def score_medical_disclaimer(content: str, source_type: str) -> float:
    if source_type == "pubmed": return 1.0  
    if not content: return 0.4

    text_lower = content.lower()
    for keyword in MEDICAL_DISCLAIMER_KEYWORDS:
        if keyword.lower() in text_lower: return 1.0

    health_keywords = [
        "health", "medical", "disease", "treatment", "symptom",
        "diagnosis", "therapy", "clinical", "patient", "drug",
        "medication", "exercise", "nutrition", "diet", "vitamin",
    ]

    health_count = sum(1 for kw in health_keywords if kw in text_lower)
    if health_count >= 3: return 0.4
    else: return 0.7


# ============================================================
# ABUSE PREVENTION / QUALITY CHECKS
# ============================================================

def _calculate_quality_penalty(content: str, source_data: dict) -> float:
    penalty = 0.0
    if not content: return 0.3 

    if source_data.get("source_type") == "youtube" and source_data.get("transcript_available") is False:
        penalty += 0.2
        logger.warning("YouTube video missing transcript. Applying 0.2 penalty.")

    word_count = len(content.split())
    if word_count < 50: penalty += 0.15
    elif word_count < 100: penalty += 0.05

    if word_count > 50:
        words = re.findall(r'\b[a-zA-Z]{3,}\b', content.lower())
        word_freq = {}
        for w in words: word_freq[w] = word_freq.get(w, 0) + 1

        max_freq = max(word_freq.values()) if word_freq else 0
        if max_freq / max(word_count, 1) > 0.08:
            penalty += 0.1

    if source_data.get("source_type") == "blog":
        link_count = content.lower().count("http")
        if word_count > 0 and link_count / (word_count / 100) > 5:
            penalty += 0.05

    return min(penalty, 0.3)


def get_trust_label(score: float) -> str:
    if score >= 0.8: return "High Trust"
    elif score >= 0.6: return "Moderate Trust"
    elif score >= 0.4: return "Low Trust"
    else: return "Very Low Trust"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sample_source = {
        "source_url": "https://example.com/ai-blog",
        "source_type": "blog",
        "author": "Tech Expert",
        "published_date": "2024-01-01",
        "content": "AI is taking over the world and it will be amazing for everyone. No logical fallacies here!"
    }
    print("Testing Trust Score Calculation...")
    result = calculate_trust_score(sample_source)
    print(f"Trust Score: {result['trust_score']}")
    print(f"Breakdown: {result['breakdown']}")
