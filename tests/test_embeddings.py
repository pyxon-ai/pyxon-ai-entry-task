"""Tests for embedding generation."""

import pytest
from src.embeddings.generator import EmbeddingGenerator


class TestEmbeddingGenerator:
    """Tests for embedding generation."""
    
    def test_init_generator(self):
        """Test initializing the embedding generator."""
        generator = EmbeddingGenerator()
        assert generator.model is not None
    
    def test_embed_single_text(self):
        """Test embedding a single text."""
        generator = EmbeddingGenerator()
        text = "This is a test sentence for embedding."
        embedding = generator.embed_text(text)
        
        assert isinstance(embedding, list)
        assert len(embedding) > 0
        assert all(isinstance(x, float) for x in embedding)
    
    def test_embed_batch_texts(self):
        """Test embedding multiple texts."""
        generator = EmbeddingGenerator()
        texts = [
            "First test sentence.",
            "Second test sentence.",
            "Third test sentence.",
        ]
        embeddings = generator.embed_text(texts)
        
        assert isinstance(embeddings, list)
        assert len(embeddings) == 3
        assert all(isinstance(e, list) for e in embeddings)
        assert all(len(e) > 0 for e in embeddings)
    
    def test_embedding_dimension(self):
        """Test embedding dimension."""
        generator = EmbeddingGenerator()
        text = "Test text"
        embedding = generator.embed_text(text)
        dimension = generator.get_embedding_dimension()
        
        assert len(embedding) == dimension
        assert dimension > 0
    
    def test_embed_chunks(self):
        """Test embedding chunks."""
        from src.models.document import Chunk, ChunkMetadata
        
        generator = EmbeddingGenerator()
        chunks = [
            Chunk(
                id=f"chunk_{i}",
                document_id="test_doc",
                content=f"Chunk content {i}",
                metadata=ChunkMetadata(
                    chunk_index=i,
                    token_count=10,
                    char_count=15,
                ),
            )
            for i in range(3)
        ]
        
        result = generator.embed_chunks(chunks)
        
        assert len(result) == 3
        assert all(c.embedding is not None for c in result)
        assert all(len(c.embedding) > 0 for c in result)


class TestEmbeddingConsistency:
    """Tests for embedding consistency."""
    
    def test_same_text_same_embedding(self):
        """Test that same text produces same embedding."""
        generator = EmbeddingGenerator()
        text = "Consistency test text."
        
        embedding1 = generator.embed_text(text)
        embedding2 = generator.embed_text(text)
        
        # Embeddings should be identical
        assert embedding1 == embedding2
    
    def test_different_text_different_embedding(self):
        """Test that different text produces different embedding."""
        generator = EmbeddingGenerator()
        text1 = "First text."
        text2 = "Second text."
        
        embedding1 = generator.embed_text(text1)
        embedding2 = generator.embed_text(text2)
        
        # Embeddings should be different
        assert embedding1 != embedding2
