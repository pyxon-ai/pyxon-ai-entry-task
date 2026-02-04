"""Embedding generator using BGE-M3 model."""

import numpy as np
from typing import List, Union
from sentence_transformers import SentenceTransformer

from src.config.settings import settings


class EmbeddingGenerator:
    """Generate embeddings using BGE-M3 model."""

    def __init__(self, model_name: str = None):
        """Initialize the embedding model."""
        self.model_name = model_name or settings.embedding_model
        self.model = None
        self._load_model()

    def _load_model(self):
        """Load the BGE-M3 model."""
        try:
            # Use SentenceTransformer directly
            self.model = SentenceTransformer(self.model_name)
            print(f"Successfully loaded embedding model: {self.model_name}")
        except Exception as e:
            print(f"Error loading embedding model: {e}")
            raise RuntimeError(
                f"Failed to load embedding model {self.model_name}"
            )

    def embed_text(
        self, text: Union[str, List[str]], batch_size: int = 32
    ) -> Union[List[float], List[List[float]]]:
        """
        Generate embeddings for text(s).
        
        Args:
            text: Single text or list of texts
            batch_size: Batch size for processing
        
        Returns:
            Embedding vector(s)
        """
        if isinstance(text, str):
            return self._embed_single(text)
        else:
            return self._embed_batch(text, batch_size)

    def _embed_single(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        embedding = self.model.encode(text)
        return embedding.tolist()

    def _embed_batch(
        self, texts: List[str], batch_size: int
    ) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        embeddings: List[List[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            result = self.model.encode(batch, show_progress_bar=False)
            # SentenceTransformer returns a numpy array
            embeddings.extend(result.tolist())
        return embeddings

    def embed_chunks(self, chunks: List) -> List:
        """
        Generate embeddings for chunks and update them in-place.
        
        Args:
            chunks: List of Chunk objects
        
        Returns:
            List of updated chunks with embeddings
        """
        texts = [chunk.content for chunk in chunks]
        embeddings = self.embed_text(texts, batch_size=settings.batch_size)
        
        for chunk, embedding in zip(chunks, embeddings):
            chunk.embedding = embedding
        
        return chunks

    def get_embedding_dimension(self) -> int:
        """Get the dimension of the embedding vectors."""
        # BGE-M3 produces 1024-dimensional vectors
        return 1024


# Global embedding generator instance
embedding_generator = None


def get_embedding_generator() -> EmbeddingGenerator:
    """Get or create the global embedding generator instance."""
    global embedding_generator
    if embedding_generator is None:
        embedding_generator = EmbeddingGenerator()
    return embedding_generator
