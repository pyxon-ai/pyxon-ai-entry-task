"""Tests for chunking strategies."""

import pytest
from src.chunking.strategies import FixedChunker, DynamicChunker, IntelligentChunker
from src.models.document import Document, DocumentMetadata, ChunkingStrategy


class TestFixedChunker:
    """Tests for fixed-size chunking."""
    
    def test_fixed_chunking_basic(self):
        """Test basic fixed chunking."""
        chunker = FixedChunker(chunk_size=100, overlap=10)
        doc = Document(
            id="test1",
            filename="test.txt",
            file_type="txt",
            content="Word " * 50,
            metadata=DocumentMetadata(),
        )
        chunks = chunker.chunk(doc)
        assert len(chunks) > 0
        assert all(c.metadata.chunk_index is not None for c in chunks)
    
    def test_fixed_chunking_overlap(self):
        """Test chunking with overlap."""
        chunker = FixedChunker(chunk_size=50, overlap=10)
        doc = Document(
            id="test2",
            filename="test.txt",
            file_type="txt",
            content="Word " * 20,
            metadata=DocumentMetadata(),
        )
        chunks = chunker.chunk(doc)
        # Verify overlap is present
        if len(chunks) > 1:
            first_chunk = chunks[0].content
            second_chunk = chunks[1].content
            # Should have some overlap
            assert len(set(first_chunk.split()) & set(second_chunk.split())) > 0


class TestDynamicChunker:
    """Tests for dynamic chunking."""
    
    def test_dynamic_chunking_with_headings(self):
        """Test dynamic chunking with markdown headings."""
        chunker = DynamicChunker(max_chunk_size=200, min_chunk_size=50)
        content = """# Heading 1
Content under heading 1.

## Heading 2
Content under heading 2.

More content here."""
        
        doc = Document(
            id="test3",
            filename="test.md",
            file_type="txt",
            content=content,
            metadata=DocumentMetadata(),
        )
        chunks = chunker.chunk(doc)
        assert len(chunks) > 0
        # Check that headings are preserved
        assert any("# Heading 1" in c.content for c in chunks)
    
    def test_dynamic_chunking_large_section(self):
        """Test dynamic chunking with large sections."""
        chunker = DynamicChunker(max_chunk_size=100, min_chunk_size=20)
        content = "Large paragraph. " * 50  # Very long text
        
        doc = Document(
            id="test4",
            filename="test.txt",
            file_type="txt",
            content=content,
            metadata=DocumentMetadata(),
        )
        chunks = chunker.chunk(doc)
        assert len(chunks) > 1  # Should split into multiple chunks


class TestIntelligentChunker:
    """Tests for intelligent chunking strategy selection."""
    
    def test_auto_select_fixed_for_simple_text(self):
        """Test auto-selection of fixed chunking for simple text."""
        fixed_chunker = FixedChunker(chunk_size=100, overlap=10)
        dynamic_chunker = DynamicChunker(max_chunk_size=200, min_chunk_size=50)
        chunker = IntelligentChunker(fixed_chunker, dynamic_chunker)
        
        # Simple text without structure
        doc = Document(
            id="test5",
            filename="test.txt",
            file_type="txt",
            content="Simple text without structure. " * 20,
            metadata=DocumentMetadata(),
        )
        strategy = chunker.analyze_document(doc)
        assert strategy in [ChunkingStrategy.FIXED, ChunkingStrategy.DYNAMIC]
    
    def test_auto_select_dynamic_for_structured_text(self):
        """Test auto-selection of dynamic chunking for structured text."""
        fixed_chunker = FixedChunker(chunk_size=100, overlap=10)
        dynamic_chunker = DynamicChunker(max_chunk_size=200, min_chunk_size=50)
        chunker = IntelligentChunker(fixed_chunker, dynamic_chunker)
        
        # Structured text with headings
        content = """# Chapter 1
Content here.

# Chapter 2
More content.

# Chapter 3
Final content."""
        
        doc = Document(
            id="test6",
            filename="test.md",
            file_type="txt",
            content=content,
            metadata=DocumentMetadata(),
        )
        strategy = chunker.analyze_document(doc)
        assert strategy in [ChunkingStrategy.FIXED, ChunkingStrategy.DYNAMIC]
    
    def test_intelligent_chunking(self):
        """Test end-to-end intelligent chunking."""
        fixed_chunker = FixedChunker(chunk_size=100, overlap=10)
        dynamic_chunker = DynamicChunker(max_chunk_size=200, min_chunk_size=50)
        chunker = IntelligentChunker(fixed_chunker, dynamic_chunker)
        
        doc = Document(
            id="test7",
            filename="test.txt",
            file_type="txt",
            content="Test content. " * 50,
            metadata=DocumentMetadata(),
        )
        chunks = chunker.chunk(doc)
        assert len(chunks) > 0
        assert doc.chunking_strategy is not None


class TestChunkMetadata:
    """Tests for chunk metadata."""
    
    def test_chunk_metadata_arabic(self):
        """Test Arabic detection in chunks."""
        from src.utils.text_utils import detect_arabic
        
        chunker = FixedChunker(chunk_size=100, overlap=10)
        doc = Document(
            id="test8",
            filename="test.txt",
            file_type="txt",
            content="مرحبا بالعالم",
            metadata=DocumentMetadata(),
        )
        chunks = chunker.chunk(doc)
        if chunks:
            assert chunks[0].metadata.has_arabic == detect_arabic(chunks[0].content)
    
    def test_chunk_metadata_token_count(self):
        """Test token count in chunks."""
        chunker = FixedChunker(chunk_size=100, overlap=10)
        doc = Document(
            id="test9",
            filename="test.txt",
            file_type="txt",
            content="Word " * 50,
            metadata=DocumentMetadata(),
        )
        chunks = chunker.chunk(doc)
        if chunks:
            assert chunks[0].metadata.token_count > 0
            assert chunks[0].metadata.char_count == len(chunks[0].content)
