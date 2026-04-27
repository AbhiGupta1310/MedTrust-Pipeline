from __future__ import annotations

"""
YouTube Scraper Module
Extracts video metadata and transcripts from YouTube URLs.
Uses yt-dlp for metadata and youtube-transcript-api for transcripts.
"""

import logging
import re
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


def scrape_youtube(url: str) -> dict:
    """
    Scrape a YouTube video for metadata and transcript.
    """
    logger.info(f"Scraping YouTube video: {url}")

    video_id = _extract_video_id(url)
    if not video_id:
        raise ValueError(f"Could not extract video ID from URL: {url}")

    # Get metadata using yt-dlp
    metadata = _get_metadata(url)

    # Get transcript
    transcript_text = _get_transcript(video_id)

    # Use description as fallback content ONLY if transcript unavailable
    if transcript_text:
        content = transcript_text
        content_source = "transcript"
    else:
        logger.warning(f"No transcript found for {video_id}, falling back to description.")
        content = metadata.get("description", "")
        content_source = "description"

    return {
        "source_url": url,
        "source_type": "youtube",
        "author": metadata.get("channel", "Unknown"),
        "published_date": metadata.get("upload_date"),
        "title": metadata.get("title", ""),
        "description": metadata.get("description", ""),
        "content": content,
        "content_source": content_source,
        "transcript_available": bool(transcript_text),
        "duration": metadata.get("duration"),
        "view_count": metadata.get("view_count"),
    }


def _extract_video_id(url: str) -> Optional[str]:
    """Extract video ID from various YouTube URL formats."""
    patterns = [
        r'(?:v=|/v/|youtu\.be/)([a-zA-Z0-9_-]{11})',
        r'(?:embed/)([a-zA-Z0-9_-]{11})',
        r'(?:shorts/)([a-zA-Z0-9_-]{11})',
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    return None


def _get_metadata(url: str) -> dict:
    """Extract video metadata using yt-dlp."""
    try:
        import yt_dlp

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "extract_flat": False,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            upload_date = None
            if info.get("upload_date"):
                try:
                    dt = datetime.strptime(info["upload_date"], "%Y%m%d")
                    upload_date = dt.strftime("%Y-%m-%d")
                except ValueError:
                    upload_date = info["upload_date"]

            return {
                "title": info.get("title", ""),
                "channel": info.get("channel") or info.get("uploader") or "Unknown",
                "description": info.get("description", ""),
                "upload_date": upload_date,
                "duration": info.get("duration"),
                "view_count": info.get("view_count"),
                "like_count": info.get("like_count"),
                "tags": info.get("tags", []),
            }

    except Exception as e:
        logger.warning(f"yt-dlp metadata extraction failed: {e}")
        return _get_metadata_fallback(url)


def _get_metadata_fallback(url: str) -> dict:
    """Fallback metadata extraction using page HTML."""
    try:
        import requests
        from bs4 import BeautifulSoup

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, "lxml")

        title = ""
        og_title = soup.find("meta", property="og:title")
        if og_title: title = og_title.get("content", "")

        description = ""
        og_desc = soup.find("meta", property="og:description")
        if og_desc: description = og_desc.get("content", "")

        channel = ""
        link_author = soup.find("link", itemprop="name")
        if link_author: channel = link_author.get("content", "")

        return {
            "title": title,
            "channel": channel or "Unknown",
            "description": description,
            "upload_date": None,
            "duration": None,
            "view_count": None,
        }

    except Exception:
        return {"title": "", "channel": "Unknown", "description": "", "upload_date": None, "duration": None, "view_count": None}


def _clean_text(text: str) -> str:
    """Helper to clean transcript text."""
    if not text:
        return ""
    # Remove bracketed text like [Music] or [Applause]
    text = re.sub(r'\[.*?\]', '', text)
    # Normalize whitespace
    return re.sub(r'\s+', ' ', text).strip()


def _get_transcript(video_id: str) -> str:
    """
    Detailed transcript retrieval with multi-language fallback and cleaning.
    """
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        
        logger.info(f"Attempting transcript retrieval for ID: {video_id}")
        
        # 1. Try to get a list of all available transcripts
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
            # 2. Try to find an English transcript (manually created, then auto-generated)
            try:
                transcript_obj = transcript_list.find_manually_created_transcript(['en'])
            except Exception:
                try:
                    transcript_obj = transcript_list.find_generated_transcript(['en'])
                except Exception:
                    # 3. Last resort: get first available transcript safely
                    try:
                        transcript_obj = next(iter(transcript_list))
                    except StopIteration:
                        logger.warning(f"No transcripts found for {video_id}")
                        return ""
            
            transcript_data = transcript_obj.fetch()
            
            if transcript_data:
                raw_text = " ".join(t.get('text', str(t)) if isinstance(t, dict) else str(t) for t in transcript_data)
                clean_text = _clean_text(raw_text)
                logger.info(f"Successfully retrieved transcript ({len(clean_text)} chars)")
                return clean_text
                
        except Exception as e:
            logger.warning(f"Detailed transcript retrieval failed: {e}. Trying direct fetch.")
            # Fallback to direct fetch
            try:
                transcript_data = YouTubeTranscriptApi.get_transcript(video_id)
                if transcript_data:
                     raw_text = " ".join(t.get('text', str(t)) if isinstance(t, dict) else str(t) for t in transcript_data)
                     return _clean_text(raw_text)
            except Exception as e2:
                logger.error(f"Fallback transcript fetch failed: {e2}")

    except Exception as e:
        logger.error(f"Transcript extraction totally failed: {e}")

    return ""
