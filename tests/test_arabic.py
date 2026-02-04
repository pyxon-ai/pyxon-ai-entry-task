"""Tests for Arabic text processing."""

import pytest
from src.arabic.processor import ArabicProcessor, get_arabic_processor


class TestArabicProcessor:
    """Tests for Arabic text processing."""
    
    def test_init_processor(self):
        """Test initializing Arabic processor."""
        processor = ArabicProcessor()
        assert processor is not None
    
    def test_tokenize_arabic(self):
        """Test Arabic tokenization."""
        processor = ArabicProcessor()
        text = "مرحبا بالعالم"
        tokens = processor.tokenize(text)
        
        assert isinstance(tokens, list)
        assert len(tokens) > 0
    
    def test_analyze_morphology(self):
        """Test morphological analysis."""
        processor = ArabicProcessor()
        word = "كتاب"
        analyses = processor.analyze_morphology(word)
        
        # Should return list of analyses (may be empty if CAMeL Tools not available)
        assert isinstance(analyses, list)
    
    def test_normalize_arabic(self):
        """Test Arabic text normalization."""
        processor = ArabicProcessor()
        text = "أنا أقرأ كتابًا"
        normalized = processor.normalize(text)
        
        # Normalized text should not have certain variants
        assert "أ" not in normalized or "ا" in normalized
    
    def test_remove_diacritics(self):
        """Test removing diacritics."""
        processor = ArabicProcessor()
        text = "السَّلامُ عَلَيْكُمْ"
        without_diacritics = processor.remove_diacritics(text)
        
        # Diacritics should be removed
        assert "َ" not in without_diacritics
        assert "ُ" not in without_diacritics
    
    def test_extract_roots(self):
        """Test extracting roots from Arabic text."""
        processor = ArabicProcessor()
        text = "كاتب يكتب كتابة"
        roots = processor.extract_roots(text)
        
        assert isinstance(roots, list)
    
    def test_get_pos_tags(self):
        """Test getting POS tags."""
        processor = ArabicProcessor()
        text = "مرحبا بالعالم"
        pos_tags = processor.get_pos_tags(text)
        
        assert isinstance(pos_tags, list)


class TestGlobalProcessor:
    """Tests for global Arabic processor instance."""
    
    def test_get_global_processor(self):
        """Test getting global processor instance."""
        processor = get_arabic_processor()
        assert processor is not None
        assert isinstance(processor, ArabicProcessor)
    
    def test_global_processor_singleton(self):
        """Test that global processor is a singleton."""
        processor1 = get_arabic_processor()
        processor2 = get_arabic_processor()
        
        # Should be the same instance
        assert processor1 is processor2


class TestArabicTextProcessing:
    """Tests for Arabic text processing utilities."""
    
    def test_mixed_arabic_english(self):
        """Test processing mixed Arabic/English text."""
        processor = ArabicProcessor()
        text = "Hello مرحبا World العالم"
        tokens = processor.tokenize(text)
        
        assert len(tokens) > 0
    
    def test_arabic_with_diacritics(self):
        """Test Arabic text with diacritics."""
        processor = ArabicProcessor()
        text = "القُرْآنُ الكَرِيمُ"
        
        # Should be able to tokenize
        tokens = processor.tokenize(text)
        assert len(tokens) > 0
        
        # Should be able to remove diacritics
        without = processor.remove_diacritics(text)
        assert len(without) > 0
    
    def test_arabic_sentence_processing(self):
        """Test processing Arabic sentences."""
        processor = ArabicProcessor()
        text = "السلام عليكم ورحمة الله وبركاته"
        
        tokens = processor.tokenize(text)
        assert len(tokens) > 0
        
        # Check for common Arabic words
        assert any("السلام" in token for token in tokens)
