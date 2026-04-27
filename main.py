"""
Main Pipeline
Orchestrates the full data scraping and trust scoring pipeline.
Runs all scrapers, applies topic tagging, chunking, language detection,
and trust scoring. Saves structured JSON output.
"""

import json
import logging
import os
import re
from datetime import datetime

from config import (
    BLOG_URLS, YOUTUBE_URLS, PUBMED_IDS, ENTREZ_EMAIL,
    MAX_CHUNK_SIZE, TOP_N_TOPICS, GENERIC_MESH_TERMS,
)
from scraper.blog_scraper import scrape_blog
from scraper.youtube_scraper import scrape_youtube
from scraper.pubmed_scraper import scrape_pubmed
from scoring.trust_score import calculate_trust_score, get_trust_label
from utils.tagging import extract_topics
from utils.chunking import chunk_content
from utils.language_detect import detect_language, detect_region

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def _strip_html(text: str) -> str:
    """Remove HTML/XML tags from text (e.g. <i>, <sup>, <b>)."""
    if not text:
        return text
    return re.sub(r'<[^>]+>', '', text)


def process_source(raw_data: dict) -> dict:
    """
    Process a raw scraped source: add language, topics, chunks, and trust score.
    """
    content = _strip_html(raw_data.get("content", ""))
    raw_data["content"] = content  # update in-place so scoring uses clean text
    source_type = raw_data.get("source_type", "")

    # Language detection
    language = detect_language(content)
    region = detect_region(content, language)

    # Topic tagging — for PubMed: merge article keywords + filtered MeSH terms
    if source_type == "pubmed":
        article_keywords = raw_data.get("article_keywords", [])
        mesh_terms = raw_data.get("mesh_terms", [])
        # Filter out generic/useless MeSH terms
        filtered_mesh = [t for t in mesh_terms if t not in GENERIC_MESH_TERMS]
        # Merge: article keywords first (more specific), then filtered MeSH
        combined = article_keywords + filtered_mesh
        # Deduplicate while preserving order
        seen = set()
        topic_tags = []
        for tag in combined:
            tag_lower = tag.lower()
            if tag_lower not in seen:
                seen.add(tag_lower)
                topic_tags.append(tag)
            if len(topic_tags) >= TOP_N_TOPICS:
                break
    else:
        topic_tags = extract_topics(content, top_n=TOP_N_TOPICS)

    # Content chunking
    content_chunks = chunk_content(content, max_chunk_size=MAX_CHUNK_SIZE)

    # Trust score calculation
    trust_result = calculate_trust_score(raw_data)
    trust_score = trust_result["trust_score"]

    # Build the final structured output matching the assignment schema
    result = {
        "source_url": raw_data.get("source_url", ""),
        "source_type": source_type,
        "author": raw_data.get("author", "Unknown"),
        "published_date": raw_data.get("published_date"),
        "language": language,
        "region": region,
        "topic_tags": topic_tags,
        "trust_score": trust_score,
        "trust_label": get_trust_label(trust_score),
        "trust_breakdown": trust_result["breakdown"],
        "content_chunks": content_chunks,
        "content": content,
        # Extra metadata
        "title": _strip_html(raw_data.get("title", "")),
        "description": _strip_html(raw_data.get("description", "")),
        "scrape_timestamp": datetime.now().isoformat(),
    }

    # Include PubMed-specific fields when available
    if source_type == "pubmed":
        result["journal"] = raw_data.get("journal", "")
        result["doi"] = raw_data.get("doi", "")
        result["pmcid"] = raw_data.get("pmcid", "")
        result["citation_count"] = raw_data.get("citation_count", 0)
        result["pmid"] = raw_data.get("pmid", "")
        coi = raw_data.get("conflict_of_interest", "")
        if coi:
            result["conflict_of_interest"] = coi

    return result


def process_single_url(url: str, source_type: str = None) -> dict:
    """
    Dynamically process a single URL instead of a hardcoded batch.
    """
    if not source_type:
        if "youtube.com" in url or "youtu.be" in url:
            source_type = "youtube"
        elif "pubmed.ncbi.nlm.nih.gov" in url:
            source_type = "pubmed"
        else:
            source_type = "blog"

    try:
        if source_type == "youtube":
            raw = scrape_youtube(url)
        elif source_type == "pubmed":
            # Extract PMID from URL if possible
            pmid = url.strip("/").split("/")[-1]
            if not pmid.isdigit():
                raise ValueError("Could not extract PMID from URL")
            raw = scrape_pubmed(pmid, email=ENTREZ_EMAIL)
        else:
            raw = scrape_blog(url)

        return process_source(raw)

    except Exception as e:
        logger.error(f"Failed to process {url}: {e}")
        return {
            "source_url": url,
            "source_type": source_type,
            "error": str(e),
            "trust_score": 0.0,
            "scrape_timestamp": datetime.now().isoformat()
        }


def run_pipeline() -> dict:
    """
    Run the full scraping and scoring pipeline.
    """
    all_sources = []

    logger.info("=" * 60)
    logger.info("PHASE 1: Scraping Blog Posts")
    logger.info("=" * 60)

    for url in BLOG_URLS:
        processed = process_single_url(url, "blog")
        all_sources.append(processed)

    logger.info("=" * 60)
    logger.info("PHASE 2: Scraping YouTube Videos")
    logger.info("=" * 60)

    for url in YOUTUBE_URLS:
        processed = process_single_url(url, "youtube")
        all_sources.append(processed)

    logger.info("=" * 60)
    logger.info("PHASE 3: Scraping PubMed Articles")
    logger.info("=" * 60)

    for pmid in PUBMED_IDS:
        url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        processed = process_single_url(url, "pubmed")
        all_sources.append(processed)

    # Reconstruct the result dictionary by filtering all_sources
    return {
        "all": all_sources,
        "blogs": [s for s in all_sources if s.get("source_type") == "blog"],
        "youtube": [s for s in all_sources if s.get("source_type") == "youtube"],
        "pubmed": [s for s in all_sources if s.get("source_type") == "pubmed"],
    }


def save_output(results: dict, output_dir: str = "output"):
    os.makedirs(output_dir, exist_ok=True)
    files = {
        "scraped_data.json": results["all"],
        "blogs.json": results["blogs"],
        "youtube.json": results["youtube"],
        "pubmed.json": results["pubmed"],
    }
    for filename, data in files.items():
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)


def main():
    results = run_pipeline()
    save_output(results)
    return results


if __name__ == "__main__":
    main()
