import re
from typing import List, Tuple, Optional


def chunk_text(text: str) -> List[Tuple[str, Optional[str]]]:
    """
    Decide automatically whether to use fixed or dynamic chunking
    based on document structure.
    Returns a list of (chunk_content, heading_name).
    """

    # If document has many headings → dynamic chunking
    heading_count = len(_detect_headings(text))

    if heading_count >= 3:
        return dynamic_chunk(text)

    # Fallback to sentence-aware chunking with no heading metadata
    chunks = sentence_aware_chunk(text)
    return [(chunk, None) for chunk in chunks]


def fixed_chunk(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap

    return chunks


def dynamic_chunk(text: str) -> List[Tuple[str, Optional[str]]]:
    """
    Split text based on headings and paragraph/sentence boundaries.
    """
    headings = _detect_headings(text)
    
    if not headings:
        chunks = sentence_aware_chunk(text)
        return [(c, None) for c in chunks]

    # Sort headings by their position in the text
    headings.sort(key=lambda x: x[1])
    
    chunks_with_metadata = []
    positions = [pos for _, pos in headings]
    
    # Check if there is content before the first heading
    if positions[0] > 0:
        preamble = text[0:positions[0]].strip()
        if len(preamble) > 50:
            preamble_chunks = sentence_aware_chunk(preamble)
            chunks_with_metadata.extend([(c, "Introduction") for c in preamble_chunks])

    # Split text into chunks based on heading positions
    for i in range(len(positions)):
        start = positions[i]
        end = positions[i + 1] if i + 1 < len(positions) else len(text)
        section = text[start:end].strip()
        
        current_heading = headings[i][0] # The heading text itself
        
        # Remove the heading from the section text to avoid duplication if desired,
        # but often it's good to keep it. We'll keep it for context in the chunk too,
        # or we can strip it. Let's keep it in the text.
        
        if len(section) > 50: 
            # If section is too long, split it using sentence awareness
            section_chunks = sentence_aware_chunk(section)
            chunks_with_metadata.extend([(c, current_heading) for c in section_chunks])

    return chunks_with_metadata

def sentence_aware_chunk(text: str, chunk_size: int = 800, overlap: int = 100) -> List[str]:
    """
    Chunk text respecting Arabic sentence boundaries (. ! ؟)
    """
    # Split by sentence delimiters. The lookbehind ensures we keep the delimiter.
    # Also split by newlines as a fallback for structure without punctuation
    sentences = re.split(r'(?<=[.!؟\n])\s+', text)
    
    # Fallback: if no punctuation found and text is long, force split by spaces
    if len(sentences) == 1 and len(text) > chunk_size:
         sentences = re.split(r'\s+', text)
    
    chunks = []
    current_chunk = []
    current_length = 0
    
    for sentence in sentences:
        sentence_len = len(sentence)
        
        if current_length + sentence_len > chunk_size and current_chunk:
            # Join the current chunk and add to list
            chunks.append(" ".join(current_chunk))
            
            # Start new chunk with overlap
            # Context preservation: Keep last few sentences up to roughly 'overlap' characters
            overlap_sentences = []
            overlap_char_count = 0
            
            # Go backwards from the end of the current chunk
            for sent in reversed(current_chunk):
                sent_len = len(sent)
                # Ensure overlap is significant but not excessive (e.g., max 50% of chunk size)
                if overlap_char_count + sent_len <= max(overlap, chunk_size // 2):
                    overlap_sentences.insert(0, sent)
                    overlap_char_count += sent_len
                else:
                    break
            
            current_chunk = overlap_sentences + [sentence]
            current_length = overlap_char_count + sentence_len
        else:
            current_chunk.append(sentence)
            current_length += sentence_len
            
    if current_chunk:
        chunks.append(" ".join(current_chunk))
        
    return chunks


def _detect_headings(text: str):
    """
    Detect headings like Chapter 1, الفصل الأول, مقدمة, etc.
    """
    # Combined patterns into a single regex to maintain natural order
    pattern = r"(Chapter\s+\d+|الفصل\s+\S+|مقدمة|خاتمة|الملخص)"
    
    headings = []
    for match in re.finditer(pattern, text):
        headings.append((match.group(), match.start()))

    return headings
