"""
Tests for Arabic language support
"""

import pytest
from app.services.document_processor import DocumentProcessor
from app.services.embedding_service import EmbeddingService


def test_arabic_text_processing():
    """Test processing of Arabic text"""
    processor = DocumentProcessor()
    
    arabic_text = "مرحباً بكم في نظام معالجة المستندات"
    language = processor.detect_language(arabic_text)
    
    assert language == 'arabic'


def test_arabic_with_diacritics():
    """Test Arabic text with diacritics (harakat)"""
    processor = DocumentProcessor()
    
    # Text with various diacritics
    text_with_harakat = "مَرْحَباً بِكُمْ فِي نِظَامِ مُعَالَجَةِ الْمُسْتَنَدَاتِ"
    
    has_diacritics = processor.validate_arabic_diacritics(text_with_harakat)
    assert has_diacritics == True


def test_arabic_embedding_generation():
    """Test embedding generation for Arabic text"""
    embedding_service = EmbeddingService()
    
    arabic_text = "هذا نص عربي للاختبار"
    embedding = embedding_service.generate_embedding(arabic_text)
    
    assert len(embedding) == 384  # Default model dimension
    assert all(isinstance(x, float) for x in embedding)


def test_mixed_language():
    """Test mixed Arabic-English text"""
    processor = DocumentProcessor()
    
    mixed_text = "This is English text مع نص عربي"
    language = processor.detect_language(mixed_text)
    
    assert language == 'mixed'
