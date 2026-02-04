"""Text processing utilities for Arabic support."""

import re
from typing import List, Tuple


# Arabic Unicode ranges
ARABIC_RANGE = (0x0600, 0x06FF)
ARABIC_EXTENDED_RANGE = (0x0750, 0x077F)
ARABIC_PRESENTATION_RANGE = (0xFB50, 0xFDFF)
ARABIC_PRESENTATION_FORMS_B = (0xFE70, 0xFEFF)

# Arabic diacritics (harakat)
DIACRITICS = {
    '\u064E',  # Fatha
    '\u064F',  # Damma
    '\u0650',  # Kasra
    '\u0651',  # Shadda
    '\u0652',  # Sukun
    '\u064B',  # Tanween Fathatan
    '\u064C',  # Tanween Dammatan
    '\u064D',  # Tanween Kasratan
    '\u0670',  # Dagger Alif (superscript)
}


def is_arabic_char(char: str) -> bool:
    """Check if a character is Arabic."""
    code = ord(char)
    return (
        ARABIC_RANGE[0] <= code <= ARABIC_RANGE[1] or
        ARABIC_EXTENDED_RANGE[0] <= code <= ARABIC_EXTENDED_RANGE[1] or
        ARABIC_PRESENTATION_RANGE[0] <= code <= ARABIC_PRESENTATION_RANGE[1] or
        ARABIC_PRESENTATION_FORMS_B[0] <= code <= ARABIC_PRESENTATION_FORMS_B[1]
    )


def detect_arabic(text: str, threshold: float = 0.1) -> bool:
    """
    Detect if text contains Arabic content.
    
    Args:
        text: Text to analyze
        threshold: Minimum ratio of Arabic characters to consider text as Arabic
    
    Returns:
        True if text contains significant Arabic content
    """
    if not text:
        return False
    
    arabic_chars = sum(1 for char in text if is_arabic_char(char))
    total_chars = len(text)
    
    # Ignore whitespace and punctuation for ratio calculation
    meaningful_chars = sum(1 for char in text if char.strip())
    
    if meaningful_chars == 0:
        return False
    
    arabic_ratio = arabic_chars / meaningful_chars
    return arabic_ratio >= threshold


def detect_diacritics(text: str) -> bool:
    """
    Detect if text contains Arabic diacritics (harakat).
    
    Args:
        text: Text to analyze
    
    Returns:
        True if text contains diacritics
    """
    return any(char in DIACRITICS for char in text)


def remove_diacritics(text: str) -> str:
    """
    Remove Arabic diacritics from text.
    
    Args:
        text: Text to process
    
    Returns:
        Text without diacritics
    """
    return ''.join(char for char in text if char not in DIACRITICS)


def normalize_arabic_text(text: str) -> str:
    """
    Normalize Arabic text by:
    - Normalizing alef variants
    - Normalizing heh variants
    - Normalizing yeh variants
    - Removing diacritics
    
    Args:
        text: Text to normalize
    
    Returns:
        Normalized text
    """
    # Normalize alef variants
    text = re.sub(r'[أإآ]', 'ا', text)

    # Normalize heh variants
    text = re.sub(r'[هة]', 'ة', text)

    # Normalize yeh variants
    text = re.sub(r'[يى]', 'ي', text)

    # Convert tanween fathatan on alif (اً) to ta marbuta (ة)
    text = re.sub('\u0627\u064B', 'ة', text)
    # Handle case where tanween comes before alif (ًا)
    text = re.sub('\u064B\u0627', 'ة', text)

    # Remove diacritics
    text = remove_diacritics(text)
    
    return text


def count_arabic_words(text: str) -> int:
    """Count Arabic words in text."""
    arabic_words = []
    for word in text.split():
        if any(is_arabic_char(char) for char in word):
            arabic_words.append(word)
    return len(arabic_words)


def extract_sentences(text: str, language: str = "ar") -> List[str]:
    """
    Extract sentences from text.
    
    Args:
        text: Text to process
        language: Language code ('ar' for Arabic, 'en' for English)
    
    Returns:
        List of sentences
    """
    if language == "ar":
        # Arabic sentence delimiters
        delimiters = r'[.!?؟]+'
    else:
        # English sentence delimiters
        delimiters = r'[.!?]+'
    
    sentences = re.split(delimiters, text)
    return [s.strip() for s in sentences if s.strip()]


def clean_whitespace(text: str) -> str:
    """Clean up whitespace in text."""
    # Replace multiple spaces with single space
    text = re.sub(r'\s+', ' ', text)
    # Remove leading/trailing whitespace
    text = text.strip()
    return text


def estimate_tokens(text: str) -> int:
    """
    Estimate token count for text.
    Simple approximation: ~4 characters per token for Arabic, ~4 for English.
    """
    # Check if text is predominantly Arabic
    is_arabic = detect_arabic(text)
    
    # Simple approximation
    return len(text) // 4
