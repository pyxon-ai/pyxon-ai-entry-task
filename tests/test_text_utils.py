"""Tests for text utilities."""

import pytest
from src.utils.text_utils import (
    detect_arabic,
    detect_diacritics,
    remove_diacritics,
    normalize_arabic_text,
    count_arabic_words,
    extract_sentences,
    clean_whitespace,
    estimate_tokens,
)


class TestArabicDetection:
    """Tests for Arabic text detection."""
    
    def test_detect_arabic_true(self):
        """Test detection of Arabic text."""
        text = "مرحبا بالعالم"
        assert detect_arabic(text) is True
    
    def test_detect_arabic_false(self):
        """Test detection of non-Arabic text."""
        text = "Hello World"
        assert detect_arabic(text) is False
    
    def test_detect_mixed_text(self):
        """Test detection of mixed Arabic/English text."""
        text = "Hello مرحبا World"
        assert detect_arabic(text) is True


class TestDiacritics:
    """Tests for diacritics handling."""
    
    def test_detect_diacritics_true(self):
        """Test detection of text with diacritics."""
        text = "السَّلامُ عَلَيْكُمْ"
        assert detect_diacritics(text) is True
    
    def test_detect_diacritics_false(self):
        """Test detection of text without diacritics."""
        text = "السلام عليكم"
        assert detect_diacritics(text) is False
    
    def test_remove_diacritics(self):
        """Test removal of diacritics."""
        text = "السَّلامُ عَلَيْكُمْ"
        result = remove_diacritics(text)
        assert result == "السلام عليكم"


class TestNormalization:
    """Tests for text normalization."""
    
    def test_normalize_arabic_text(self):
        """Test Arabic text normalization."""
        text = "أنا أقرأ كتابًا"
        result = normalize_arabic_text(text)
        assert "أ" not in result  # Alef variants normalized
        assert "ة" in result  # Heh variants normalized


class TestWordCount:
    """Tests for word counting."""
    
    def test_count_arabic_words(self):
        """Test counting Arabic words."""
        text = "مرحبا بالعالم"
        count = count_arabic_words(text)
        assert count == 2
    
    def test_count_mixed_words(self):
        """Test counting mixed Arabic/English words."""
        text = "Hello مرحبا World"
        count = count_arabic_words(text)
        assert count == 1


class TestSentenceExtraction:
    """Tests for sentence extraction."""
    
    def test_extract_arabic_sentences(self):
        """Test extracting Arabic sentences."""
        text = "مرحبا. كيف حالك؟ أنا بخير."
        sentences = extract_sentences(text, language="ar")
        assert len(sentences) == 3
    
    def test_extract_english_sentences(self):
        """Test extracting English sentences."""
        text = "Hello. How are you? I am fine."
        sentences = extract_sentences(text, language="en")
        assert len(sentences) == 3


class TestWhitespaceCleaning:
    """Tests for whitespace cleaning."""
    
    def test_clean_whitespace(self):
        """Test cleaning whitespace."""
        text = "Hello    World\n\nHow  are  you?"
        result = clean_whitespace(text)
        assert "  " not in result
        assert "\n\n" not in result


class TestTokenEstimation:
    """Tests for token estimation."""
    
    def test_estimate_tokens_arabic(self):
        """Test token estimation for Arabic text."""
        text = "مرحبا بالعالم" * 10
        tokens = estimate_tokens(text)
        assert tokens > 0
    
    def test_estimate_tokens_english(self):
        """Test token estimation for English text."""
        text = "Hello World" * 10
        tokens = estimate_tokens(text)
        assert tokens > 0
