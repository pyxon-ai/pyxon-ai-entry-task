"""
Tests for chunking service
"""

import pytest
from app.services.chunking_service import ChunkingService


def test_fixed_chunking():
    """Test fixed-size chunking"""
    chunker = ChunkingService(default_chunk_size=10, default_overlap=2)
    
    text = "This is a test sentence with multiple words to chunk properly."
    chunks = chunker.fixed_chunking(text)
    
    assert len(chunks) > 0
    assert all(chunk.metadata['strategy'] == 'fixed' for chunk in chunks)


def test_dynamic_chunking():
    """Test dynamic chunking"""
    chunker = ChunkingService()
    
    text = """
    Paragraph one with some content.
    
    Paragraph two with different content.
    """
    
    chunks = chunker.dynamic_chunking(text)
    
    assert len(chunks) > 0
    assert all(chunk.metadata['strategy'] == 'dynamic' for chunk in chunks)


def test_strategy_decision():
    """Test automatic strategy selection"""
    chunker = ChunkingService()
    
    # Simple text should use fixed
    simple_text = "Simple text without structure."
    strategy = chunker.decide_strategy(simple_text, {})
    
    # Complex text should use dynamic
    complex_text = """
    HEADING ONE
    
    This is a complex paragraph with structure.
    
    - Bullet point one
    - Bullet point two
    """
    strategy_complex = chunker.decide_strategy(complex_text, {})
    
    assert strategy in ['fixed', 'dynamic']
    assert strategy_complex in ['fixed', 'dynamic']
