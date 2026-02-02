"""
Tests for document processor
"""

import pytest
from app.services.document_processor import DocumentProcessor


def test_language_detection():
    """Test language detection"""
    processor = DocumentProcessor()
    
    # Test English
    english_text = "This is an English sentence."
    assert processor.detect_language(english_text) == 'english'
    
    # Test Arabic
    arabic_text = "هذا نص عربي"
    assert processor.detect_language(arabic_text) == 'arabic'
    
    # Test mixed
    mixed_text = "This is English and هذا عربي"
    assert processor.detect_language(mixed_text) == 'mixed'


def test_arabic_diacritics():
    """Test Arabic diacritics detection"""
    processor = DocumentProcessor()
    
    # Text with diacritics
    with_diacritics = "مَرْحَباً"
    assert processor.validate_arabic_diacritics(with_diacritics) == True
    
    # Text without diacritics
    without_diacritics = "مرحبا"
    assert processor.validate_arabic_diacritics(without_diacritics) == False


def test_supported_formats():
    """Test supported file formats"""
    processor = DocumentProcessor()
    
    assert '.pdf' in processor.supported_formats
    assert '.docx' in processor.supported_formats
    assert '.txt' in processor.supported_formats
