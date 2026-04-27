from __future__ import annotations

"""
Blog Scraper Module
Extracts article content, metadata, and author information from blog URLs.
Uses newspaper3k as primary extractor with an advanced LLM + Pydantic fallback for resilience.
"""

import logging
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from typing import Optional
from pydantic import BaseModel, Field

from utils.llm_client import get_instructor_client, DEFAULT_LLM_MODEL

logger = logging.getLogger(__name__)


# Define the Strict Output Schema for the LLM
class ArticleExtraction(BaseModel):
    title: str = Field(description="The main title of the article")
    author: str = Field(description="The primary author(s) of the article. Put 'Unknown' if not clearly stated.")
    published_date: Optional[str] = Field(description="The publication date formatted as YYYY-MM-DD. Null if not found.")
    description: str = Field(description="A brief 1-2 sentence summary or meta description of the article.")
    content: str = Field(description="The main body text of the article. Cleanly formatted, completely devoid of navigation, ads, or footer menus.")


def scrape_blog(url: str) -> dict:
    """
    Scrape a blog post and extract structured data.
    
    Args:
        url: URL of the blog post to scrape
        
    Returns:
        Dictionary with extracted blog data
    """
    logger.info(f"Scraping blog: {url}")

    try:
        # First attempt: standard lightweight heuristic scraping
        data = _scrape_with_newspaper(url)
    except Exception as e:
        logger.warning(f"newspaper3k failed for {url}: {e}. Falling back to Advanced LLM Extraction (Instructor)...")
        data = _scrape_with_llm(url)

    # Ensure we have content
    if not data.get("content"):
        logger.warning(f"No content extracted from {url}")
        data["content"] = ""

    data["source_url"] = url
    data["source_type"] = "blog"

    return data


def _scrape_with_newspaper(url: str) -> dict:
    """Extract blog content using newspaper3k (Fast heuristic approach)."""
    from newspaper import Article

    article = Article(url)
    article.download()
    article.parse()

    # Extract author
    author = "Unknown"
    if article.authors:
        author = ", ".join(article.authors)

    # Extract publish date
    published_date = None
    if article.publish_date:
        published_date = article.publish_date.strftime("%Y-%m-%d")

    return {
        "author": author,
        "published_date": published_date,
        "title": article.title or "",
        "description": article.meta_description or "",
        "content": article.text or "",
    }


def _scrape_with_llm(url: str) -> dict:
    """Fallback: Robust extraction utilizing LLMs to pull cleanly structured data from messy HTML strings."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()
    
    # Use BS4 just to strip away obvious javascript/css tags so the LLM context window isn't bloated
    soup = BeautifulSoup(response.text, "lxml")
    for tag_name in ["nav", "footer", "header", "script", "style", "noscript", "svg"]:
        for tag in soup.find_all(tag_name):
            tag.decompose()
            
    raw_text = soup.get_text(separator="\n\n", strip=True)
    
    # Ensure text fits in context window (e.g. max 50k chars for mini models)
    if len(raw_text) > 80000:
        raw_text = raw_text[:80000]

    # Initialize Instructor client
    client = get_instructor_client()
    
    logger.info("Executing Instructor LLM request for semantic data extraction...")
    
    try:
        extraction: ArticleExtraction = client.chat.completions.create(
            model=DEFAULT_LLM_MODEL,
            response_model=ArticleExtraction,
            messages=[
                {"role": "system", "content": "You are a perfect data-extraction agent. Your job is to extract the article title, author, date, and core text content from a raw HTML text dump. Return ONLY the content of the article body, omitting any sidebar links, cookie banners, or unrelated text."},
                {"role": "user", "content": f"Extract the data from this webpage text:\n\n{raw_text}"}
            ],
            temperature=0.0
        )
        
        return {
            "author": extraction.author,
            "published_date": extraction.published_date,
            "title": extraction.title,
            "description": extraction.description,
            "content": extraction.content,
        }
        
    except Exception as e:
        logger.error(f"LLM Extraction absolutely failed: {e}")
        # Final catastrophic fallback - return error marker instead of raw HTML
        return {
            "author": "Unknown",
            "published_date": None,
            "title": "Extraction Failed",
            "description": "The system was unable to parse this article content.",
            "content": "",
            "error": str(e)
        }

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_url = "https://www.technologyreview.com/2025/01/08/1109188/whats-next-for-ai-in-2025/"
    result = scrape_blog(test_url)
    print(f"Title: {result.get('title')}")
    print(f"Author: {result.get('author')}")
    print(f"Date: {result.get('published_date')}")
    print(f"Content length: {len(result.get('content', ''))}")
    print(f"Content preview: {result.get('content', '')[:200]}...")
