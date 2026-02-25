from sentence_transformers import SentenceTransformer
from typing import List
import numpy as np

class Embedder:
    def __init__(self, model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
        """
        Initialize the embedder with a multilingual model.
        This model performs well with Arabic text.
        """
        self.model = SentenceTransformer(model_name)

    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single string."""
        embedding = self.model.encode(text)
        return embedding.tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of strings."""
        embeddings = self.model.encode(texts)
        return embeddings.tolist()
