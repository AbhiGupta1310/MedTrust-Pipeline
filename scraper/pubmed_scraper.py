from __future__ import annotations

"""
PubMed Scraper Module
Extracts article metadata and abstracts from PubMed using the NCBI Entrez API.
Uses Biopython's Bio.Entrez for structured XML data retrieval.
"""

import logging
import re
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)


def scrape_pubmed(pmid: str, email: str = "user@example.com") -> dict:
    """
    Scrape a PubMed article by its PMID.
    
    Args:
        pmid: PubMed ID of the article
        email: Email for NCBI Entrez API (required by NCBI)
        
    Returns:
        Dictionary with extracted article data
    """
    logger.info(f"Scraping PubMed article: {pmid}")

    try:
        return _scrape_with_biopython(pmid, email)
    except Exception as e:
        logger.warning(f"Biopython failed for PMID {pmid}: {e}. Trying direct API...")
        return _scrape_with_requests(pmid, email)


def _strip_html_tags(text: str) -> str:
    """Remove HTML/XML tags (e.g. <i>, <sup>, <b>) from text."""
    if not text:
        return text
    return re.sub(r'<[^>]+>', '', text)


def _scrape_with_biopython(pmid: str, email: str) -> dict:
    """Extract PubMed data using Biopython's Entrez module."""
    from Bio import Entrez

    Entrez.email = email

    # Fetch article data
    handle = Entrez.efetch(db="pubmed", id=pmid, rettype="xml", retmode="xml")
    records = Entrez.read(handle)
    handle.close()

    article_data = records["PubmedArticle"][0]
    medline = article_data["MedlineCitation"]
    article = medline["Article"]

    # Extract authors
    authors = _extract_authors_bio(article)

    # Extract publication date
    published_date = _extract_date_bio(article)

    # Extract abstract (with HTML stripped)
    abstract = _strip_html_tags(_extract_abstract_bio(article))

    # Extract journal (with parenthetical disambiguator if present)
    journal = ""
    if "Journal" in article:
        journal_title = str(article["Journal"].get("Title", ""))
        iso_abbrev = str(article["Journal"].get("ISOAbbreviation", ""))
        # Use ISO abbreviation's parenthetical if the full title doesn't have one
        # e.g. Title="Genes", ISOAbbreviation="Genes (Basel)" → "Genes (Basel)"
        if "(" in iso_abbrev and "(" not in journal_title:
            paren = iso_abbrev[iso_abbrev.index("("):]
            journal = f"{journal_title} {paren}"
        else:
            journal = journal_title

    # Extract title (strip HTML tags like <i>)
    title = _strip_html_tags(str(article.get("ArticleTitle", "")))

    # Extract keywords (MeSH terms)
    mesh_terms = _extract_mesh_terms(medline)

    # Extract article-specific keywords (from KeywordList)
    article_keywords = _extract_keywords_bio(medline)

    # Extract author affiliations
    affiliations = _extract_affiliations_bio(article)

    # Extract Conflict of Interest statement
    coi = _extract_coi(medline)

    # Extract DOI and PMCID from article identifiers
    doi, pmcid = _extract_article_ids(article_data)

    # Get citation count (from PubMed Central if available)
    citation_count = _get_citation_count(pmid, email)

    return {
        "source_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        "source_type": "pubmed",
        "author": authors,
        "published_date": published_date,
        "title": title,
        "description": _strip_html_tags(abstract[:300] + "..." if len(abstract) > 300 else abstract),
        "content": abstract,
        "journal": journal,
        "mesh_terms": mesh_terms,
        "article_keywords": article_keywords,
        "affiliations": affiliations,
        "conflict_of_interest": coi,
        "doi": doi,
        "pmcid": pmcid,
        "citation_count": citation_count,
        "pmid": pmid,
    }


def _extract_authors_bio(article: dict) -> str:
    """Extract author names from Biopython article data."""
    try:
        author_list = article.get("AuthorList", [])
        names = []
        for author in author_list:
            last = str(author.get("LastName", ""))
            fore = str(author.get("ForeName", ""))
            initials = str(author.get("Initials", ""))
            if last:
                name = f"{fore} {last}" if fore else f"{initials} {last}"
                names.append(name.strip())

        if names:
            return ", ".join(names)
    except Exception as e:
        logger.warning(f"Author extraction failed: {e}")

    return "Unknown"


def _extract_date_bio(article: dict) -> Optional[str]:
    """Extract publication date from article data."""
    try:
        # Try ArticleDate first
        if "ArticleDate" in article and article["ArticleDate"]:
            date_obj = article["ArticleDate"][0]
            year = str(date_obj.get("Year", ""))
            month = str(date_obj.get("Month", "01")).zfill(2)
            day = str(date_obj.get("Day", "01")).zfill(2)
            return f"{year}-{month}-{day}"

        # Try Journal PubDate
        if "Journal" in article and "JournalIssue" in article["Journal"]:
            pub_date = article["Journal"]["JournalIssue"].get("PubDate", {})
            year = str(pub_date.get("Year", ""))
            if year:
                month = str(pub_date.get("Month", "01"))
                # Convert month name to number if needed
                month = _month_to_number(month)
                day = str(pub_date.get("Day", "01")).zfill(2)
                return f"{year}-{month}-{day}"

    except Exception as e:
        logger.warning(f"Date extraction failed: {e}")

    return None


def _extract_abstract_bio(article: dict) -> str:
    """Extract abstract text from article data, stripping any inline HTML."""
    try:
        abstract_parts = article.get("Abstract", {}).get("AbstractText", [])
        if abstract_parts:
            parts = []
            for part in abstract_parts:
                text = _strip_html_tags(str(part))
                # Check if this part has a label (e.g., "BACKGROUND", "METHODS")
                if hasattr(part, "attributes") and "Label" in part.attributes:
                    label = part.attributes["Label"]
                    text = f"{label}: {text}"
                parts.append(text)
            return "\n\n".join(parts)
    except Exception as e:
        logger.warning(f"Abstract extraction failed: {e}")

    return ""


def _extract_mesh_terms(medline: dict) -> list[str]:
    """Extract MeSH terms (controlled vocabulary keywords)."""
    terms = []
    try:
        mesh_list = medline.get("MeshHeadingList", [])
        for heading in mesh_list:
            descriptor = heading.get("DescriptorName", "")
            if descriptor:
                terms.append(str(descriptor))
    except Exception as e:
        logger.warning(f"MeSH term extraction failed: {e}")

    return terms


def _extract_keywords_bio(medline: dict) -> list[str]:
    """Extract article-specific keywords from KeywordList."""
    keywords = []
    try:
        keyword_lists = medline.get("KeywordList", [])
        for kw_list in keyword_lists:
            for kw in kw_list:
                keyword = _strip_html_tags(str(kw)).strip()
                if keyword:
                    keywords.append(keyword)
    except Exception as e:
        logger.warning(f"Keyword extraction failed: {e}")

    return keywords


def _extract_affiliations_bio(article: dict) -> list[str]:
    """Extract unique author affiliations from article data."""
    affiliations = []
    seen = set()
    try:
        author_list = article.get("AuthorList", [])
        for author in author_list:
            aff_infos = author.get("AffiliationInfo", [])
            for aff_info in aff_infos:
                aff = str(aff_info.get("Affiliation", "")).strip()
                if aff and aff not in seen:
                    seen.add(aff)
                    affiliations.append(aff)
    except Exception as e:
        logger.warning(f"Affiliation extraction failed: {e}")

    return affiliations


def _extract_coi(medline: dict) -> str:
    """Extract Conflict of Interest statement."""
    try:
        coi = str(medline.get("CoiStatement", "")).strip()
        return coi
    except Exception:
        return ""


def _extract_article_ids(article_data: dict) -> tuple[str, str]:
    """Extract DOI and PMCID from the PubmedData ArticleIdList."""
    doi = ""
    pmcid = ""
    try:
        article_ids = article_data.get("PubmedData", {}).get("ArticleIdList", [])
        for aid in article_ids:
            aid_str = str(aid)
            if hasattr(aid, "attributes"):
                id_type = aid.attributes.get("IdType", "")
                if id_type == "doi":
                    doi = aid_str
                elif id_type == "pmc":
                    pmcid = aid_str
    except Exception as e:
        logger.warning(f"Article ID extraction failed: {e}")

    return doi, pmcid


def _get_citation_count(pmid: str, email: str) -> int:
    """Get the number of citations for a PubMed article."""
    try:
        from Bio import Entrez

        Entrez.email = email
        handle = Entrez.elink(dbfrom="pubmed", id=pmid, linkname="pubmed_pubmed_citedin")
        result = Entrez.read(handle)
        handle.close()

        if result and result[0].get("LinkSetDb"):
            links = result[0]["LinkSetDb"][0].get("Link", [])
            return len(links)

    except Exception as e:
        logger.warning(f"Citation count retrieval failed for {pmid}: {e}")

    return 0


def _scrape_with_requests(pmid: str, email: str) -> dict:
    """Fallback: Extract PubMed data using direct API requests."""
    import requests

    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    params = {
        "db": "pubmed",
        "id": pmid,
        "rettype": "xml",
        "retmode": "xml",
        "email": email,
    }

    response = requests.get(f"{base_url}/efetch.fcgi", params=params, timeout=15)
    response.raise_for_status()

    root = ET.fromstring(response.text)
    article_el = root.find(".//Article")

    if article_el is None:
        return {
            "source_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "source_type": "pubmed",
            "author": "Unknown",
            "published_date": None,
            "title": "",
            "description": "",
            "content": "",
            "error": "Could not parse article data",
        }

    # Title
    title_el = article_el.find("ArticleTitle")
    title = title_el.text if title_el is not None else ""

    # Authors
    authors = []
    for author_el in article_el.findall(".//Author"):
        last = author_el.findtext("LastName", "")
        fore = author_el.findtext("ForeName", "")
        if last:
            authors.append(f"{fore} {last}".strip())

    # Abstract (strip HTML tags)
    abstract_parts = []
    for abstract_el in article_el.findall(".//AbstractText"):
        label = abstract_el.get("Label", "")
        # Get full inner text including sub-elements via itertext()
        text = "".join(abstract_el.itertext()) or ""
        text = _strip_html_tags(text)
        if label:
            abstract_parts.append(f"{label}: {text}")
        else:
            abstract_parts.append(text)

    abstract = "\n\n".join(abstract_parts)

    # Journal (with parenthetical if available)
    journal_el = article_el.find(".//Journal/Title")
    journal = journal_el.text if journal_el is not None else ""
    iso_el = article_el.find(".//Journal/ISOAbbreviation")
    if iso_el is not None and iso_el.text:
        if "(" in iso_el.text and "(" not in (journal or ""):
            paren = iso_el.text[iso_el.text.index("("):]
            journal = f"{journal} {paren}"

    # Title (strip HTML)
    title = _strip_html_tags(title or "")

    # Date
    date_el = article_el.find(".//ArticleDate")
    published_date = None
    if date_el is not None:
        year = date_el.findtext("Year", "")
        month = date_el.findtext("Month", "01").zfill(2)
        day = date_el.findtext("Day", "01").zfill(2)
        if year:
            published_date = f"{year}-{month}-{day}"

    # DOI
    doi = ""
    doi_els = root.findall(".//ArticleId[@IdType='doi']")
    if doi_els:
        doi = doi_els[0].text or ""

    # PMCID
    pmcid = ""
    pmc_els = root.findall(".//ArticleId[@IdType='pmc']")
    if pmc_els:
        pmcid = pmc_els[0].text or ""

    # COI statement
    coi_el = root.find(".//CoiStatement")
    coi = coi_el.text if coi_el is not None else ""

    return {
        "source_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        "source_type": "pubmed",
        "author": ", ".join(authors) if authors else "Unknown",
        "published_date": published_date,
        "title": title,
        "description": _strip_html_tags(abstract[:300] + "..." if len(abstract) > 300 else abstract),
        "content": abstract,
        "journal": journal,
        "doi": doi,
        "pmcid": pmcid,
        "conflict_of_interest": coi,
        "affiliations": [],
        "article_keywords": [],
        "mesh_terms": [],
        "citation_count": 0,
        "pmid": pmid,
    }


def _month_to_number(month: str) -> str:
    """Convert month name or abbreviation to zero-padded number."""
    month_map = {
        "jan": "01", "feb": "02", "mar": "03", "apr": "04",
        "may": "05", "jun": "06", "jul": "07", "aug": "08",
        "sep": "09", "oct": "10", "nov": "11", "dec": "12",
    }

    if month.isdigit():
        return month.zfill(2)

    return month_map.get(month[:3].lower(), "01")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_pmid = "37286606"
    result = scrape_pubmed(test_pmid)
    print(f"Title: {result.get('title')}")
    print(f"Authors: {result.get('author')}")
    print(f"Journal: {result.get('journal')}")
    print(f"Date: {result.get('published_date')}")
    print(f"Citations: {result.get('citation_count')}")
    print(f"Content preview: {result.get('content', '')[:200]}...")
