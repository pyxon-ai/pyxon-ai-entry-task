"""
Embedding Manager for multilingual/Arabic embeddings
Integrates with sentence-transformers
"""
import logging
from typing import List, Optional
import numpy as np

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class EmbeddingManager:
    """
    Manages text embeddings using multilingual models
    Optimized for Arabic text
    """
    
    def __init__(
        self,
        model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
        device: str = "cpu",
        cache_folder: Optional[str] = None
    ):
        """
        Initialize embedding manager
        
        Args:
            model_name: Name of sentence-transformers model
            device: Device to run model on ('cpu' or 'cuda')
            cache_folder: Optional folder to cache models
        """
        self.model_name = model_name
        self.device = device
        
        logger.info(f"Loading embedding model: {model_name} on {device}")
        
        self.model = SentenceTransformer(
            model_name,
            device=device,
            cache_folder=cache_folder
        )
        
        # Get embedding dimension
        self.dimension = self.model.get_sentence_embedding_dimension()
        
        logger.info(f"Model loaded. Embedding dimension: {self.dimension}")
    
    def _prepare_text(self, text: str, is_query: bool = False) -> str:
        """Add prefix for e5 models if needed"""
        if "e5" in self.model_name.lower():
            prefix = "query: " if is_query else "passage: "
            # Check if prefix already exists to avoid double prefixing
            if not text.startswith(prefix):
                return f"{prefix}{text}"
        return text

    def encode_single(self, text: str, is_query: bool = False, normalize: bool = True) -> np.ndarray:
        """
        Encode a single text into embedding
        
        Args:
            text: Text to encode
            is_query: Whether this is a search query (for E5 models)
            normalize: Whether to normalize embedding to unit length
            
        Returns:
            Embedding vector as numpy array
        """
        text = self._prepare_text(text, is_query)
        
        embedding = self.model.encode(
            text,
            normalize_embeddings=normalize,
            show_progress_bar=False
        )
        
        return embedding
    
    def encode_batch(
        self,
        texts: List[str],
        is_query: bool = False,
        batch_size: int = 32,
        normalize: bool = True,
        show_progress: bool = True
    ) -> np.ndarray:
        """
        Encode multiple texts into embeddings
        
        Args:
            texts: List of texts to encode
            is_query: Whether these are search queries (for E5 models)
            batch_size: Batch size for encoding
            normalize: Whether to normalize embeddings
            show_progress: Whether to show progress bar
            
        Returns:
            Array of embeddings
        """
        logger.info(f"Encoding {len(texts)} texts with batch size {batch_size}")
        
        processed_texts = [self._prepare_text(t, is_query) for t in texts]
        
        embeddings = self.model.encode(
            processed_texts,
            batch_size=batch_size,
            normalize_embeddings=normalize,
            show_progress_bar=show_progress
        )
        
        return embeddings
    
    def compute_similarity(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray
    ) -> float:
        """
        Compute cosine similarity between two embeddings
        
        Args:
            embedding1: First embedding
            embedding2: Second embedding
            
        Returns:
            Cosine similarity score (0-1)
        """
        # Compute cosine similarity
        similarity = np.dot(embedding1, embedding2) / (
            np.linalg.norm(embedding1) * np.linalg.norm(embedding2)
        )
        
        return float(similarity)
    
    def get_model_info(self) -> dict:
        """
        Get information about the embedding model
        
        Returns:
            Dictionary with model information
        """
        return {
            'model_name': self.model_name,
            'dimension': self.dimension,
            'device': self.device,
            'max_seq_length': self.model.max_seq_length,
        }
