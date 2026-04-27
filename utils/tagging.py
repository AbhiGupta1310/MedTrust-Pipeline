"""
Topic Tagging Module
Extracts relevant topic tags from text content using KeyBERT.
Falls back to TF-IDF based extraction if KeyBERT is unavailable.
"""

import re
import logging

logger = logging.getLogger(__name__)


def extract_topics(text: str, top_n: int = 5) -> list[str]:
    """
    Extract topic tags from text content.
    
    Uses KeyBERT for semantic keyword extraction. Falls back to 
    a simple TF-IDF approach if KeyBERT is not available.
    
    Args:
        text: The text content to extract topics from
        top_n: Number of top topics to return
        
    Returns:
        List of topic tag strings
    """
    if not text or not text.strip():
        return []

    # Clean text for processing
    clean_text = _clean_text(text)

    if len(clean_text.split()) < 10:
        return _extract_simple(clean_text, top_n)

    try:
        return _extract_keybert(clean_text, top_n)
    except Exception as e:
        logger.warning(f"KeyBERT extraction failed: {e}. Falling back to simple extraction.")
        return _extract_simple(clean_text, top_n)


_kb_model = None

def _get_keybert_model():
    """Lazy-load KeyBERT model as a singleton."""
    global _kb_model
    if _kb_model is None:
        from keybert import KeyBERT
        _kb_model = KeyBERT()
    return _kb_model


def _extract_keybert(text: str, top_n: int) -> list[str]:
    """Extract keywords using KeyBERT."""
    model = _get_keybert_model()
    keywords = model.extract_keywords(
        text,
        keyphrase_ngram_range=(1, 2),
        stop_words="english",
        top_n=top_n,
        use_mmr=True,           # Maximal Marginal Relevance for diversity
        diversity=0.5,
    )

    # KeyBERT returns list of (keyword, score) tuples
    tags = [kw[0].title() for kw in keywords]
    return tags


def _extract_simple(text: str, top_n: int) -> list[str]:
    """
    Simple TF-based keyword extraction as fallback.
    Uses word frequency after removing stop words.
    """
    STOP_WORDS = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "can", "shall", "to", "of", "in", "for",
        "on", "with", "at", "by", "from", "as", "into", "through", "during",
        "before", "after", "above", "below", "between", "out", "off", "over",
        "under", "again", "further", "then", "once", "here", "there", "when",
        "where", "why", "how", "all", "each", "every", "both", "few", "more",
        "most", "other", "some", "such", "no", "nor", "not", "only", "own",
        "same", "so", "than", "too", "very", "just", "because", "but", "and",
        "or", "if", "while", "about", "up", "also", "it", "its", "this",
        "that", "these", "those", "he", "she", "they", "we", "you", "i",
        "me", "my", "your", "his", "her", "their", "our", "us", "them",
        "what", "which", "who", "whom", "new", "one", "two", "use", "used",
        "using", "many", "much", "well", "like", "make", "made", "know",
    }

    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    filtered = [w for w in words if w not in STOP_WORDS]

    # Count frequencies
    freq = {}
    for word in filtered:
        freq[word] = freq.get(word, 0) + 1

    # Sort by frequency descending
    sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)

    tags = [word.title() for word, count in sorted_words[:top_n]]
    return tags


def _clean_text(text: str) -> str:
    """Clean text for topic extraction."""
    # Remove URLs
    text = re.sub(r'https?://\S+', '', text)
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


if __name__ == "__main__":
    sample = """
    Artificial intelligence and machine learning are transforming healthcare.
    Deep learning models can now analyze medical images with remarkable accuracy.
    Natural language processing enables automated analysis of clinical notes.
    These AI systems are being deployed in hospitals for diagnosis and treatment planning.
    """
    topics = extract_topics(sample, top_n=5)
    print(f"Extracted topics: {topics}")
