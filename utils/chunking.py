import re

def chunk_content(text: str, max_chunk_size: int = 500) -> list[str]:
    """
    Split text into smaller chunks.
    
    Strategy:
    1. First split by double newlines (paragraphs)
    2. If a paragraph exceeds max_chunk_size, split by sentences
    3. Merge very small chunks with the next one
    
    Args:
        text: The full text content to chunk
        max_chunk_size: Maximum characters per chunk
        
    Returns:
        List of text chunks
    """
    if not text or not text.strip():
        return []

    # Normalize whitespace
    text = text.strip()

    # Split by double newlines (paragraphs)
    paragraphs = text.split("\n\n")

    chunks = []
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(para) <= max_chunk_size:
            chunks.append(para)
        else:
            # Split long paragraphs by sentences
            chunks.extend(_split_by_sentences(para, max_chunk_size))

    # Merge very short chunks (< 50 chars) with the next chunk
    merged = _merge_short_chunks(chunks, min_size=50)

    return merged


def _split_by_sentences(text: str, max_size: int) -> list[str]:
    """Split text by sentence boundaries when it exceeds max_size."""
    # Split on sentence-ending punctuation followed by space
    sentences = re.split(r'(?<=[.!?])\s+', text)

    chunks = []
    current = ""

    for sentence in sentences:
        if not sentence.strip():
            continue

        if len(current) + len(sentence) + 1 > max_size and current:
            chunks.append(current.strip())
            current = sentence
        else:
            current = (current + " " + sentence).strip() if current else sentence

    if current.strip():
        chunks.append(current.strip())

    return chunks


def _merge_short_chunks(chunks: list[str], min_size: int = 50) -> list[str]:
    """Merge chunks that are too short with the following chunk."""
    if not chunks:
        return []

    merged = []
    buffer = ""

    for chunk in chunks:
        if buffer:
            buffer = buffer + "\n\n" + chunk
            if len(buffer) >= min_size:
                merged.append(buffer)
                buffer = ""
        elif len(chunk) < min_size:
            buffer = chunk
        else:
            merged.append(chunk)

    # Don't lose the last buffer
    if buffer:
        if merged:
            merged[-1] = merged[-1] + "\n\n" + buffer
        else:
            merged.append(buffer)

    return merged


if __name__ == "__main__":
    # Quick test
    sample = """This is the first paragraph of the article. It discusses important concepts in artificial intelligence and machine learning.

This is the second paragraph. It goes into more detail about neural networks and deep learning architectures.

This is a very long paragraph that should be split into multiple chunks. Machine learning is a subset of artificial intelligence that provides systems the ability to automatically learn and improve from experience without being explicitly programmed. Machine learning focuses on the development of computer programs that can access data and use it to learn for themselves. The process of learning begins with observations or data, such as examples, direct experience, or instruction, in order to look for patterns in data and make better decisions in the future based on the examples that we provide.

Short."""

    chunks = chunk_content(sample, max_chunk_size=300)
    for i, chunk in enumerate(chunks):
        print(f"\n--- Chunk {i+1} ({len(chunk)} chars) ---")
        print(chunk)
