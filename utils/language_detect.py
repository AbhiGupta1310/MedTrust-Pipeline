"""
Language Detection Module
Detects the language and infers geographic region from content.
"""

import logging

logger = logging.getLogger(__name__)

# Language to region mapping (most common association)
LANGUAGE_REGION_MAP = {
    "en": "Global (English)",
    "es": "Latin America / Spain",
    "fr": "France / Francophone Africa",
    "de": "Germany / DACH",
    "pt": "Brazil / Portugal",
    "zh-cn": "China",
    "zh-tw": "Taiwan",
    "ja": "Japan",
    "ko": "South Korea",
    "ar": "Middle East / North Africa",
    "hi": "India",
    "ru": "Russia",
    "it": "Italy",
    "nl": "Netherlands",
    "sv": "Sweden",
    "pl": "Poland",
    "tr": "Turkey",
}


def detect_language(text: str) -> str:
    """
    Detect the language of the given text.
    
    Args:
        text: Text content to detect language of
        
    Returns:
        ISO 639-1 language code (e.g., 'en', 'es', 'fr')
    """
    if not text or not text.strip():
        return "unknown"

    try:
        from langdetect import detect
        lang = detect(text)
        return lang
    except Exception as e:
        logger.warning(f"Language detection failed: {e}")
        return "unknown"


def detect_region(text: str, language: str = None) -> str:
    """
    Infer geographic region based on detected language.
    
    Args:
        text: Text content (used for language detection if language not provided)
        language: Pre-detected language code (optional)
        
    Returns:
        Geographic region string
    """
    if language is None:
        language = detect_language(text)

    return LANGUAGE_REGION_MAP.get(language, "Unknown")


if __name__ == "__main__":
    samples = [
        "Artificial intelligence is transforming the healthcare industry worldwide.",
        "La inteligencia artificial está transformando la industria de la salud.",
        "L'intelligence artificielle transforme le secteur de la santé.",
    ]

    for sample in samples:
        lang = detect_language(sample)
        region = detect_region(sample, lang)
        print(f"Language: {lang}, Region: {region}")
        print(f"  Text: {sample[:60]}...\n")
