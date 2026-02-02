from sentence_transformers import SentenceTransformer
from typing import List


class Embedder:
    def __init__(self, model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
        self.model = SentenceTransformer(model_name)

    def embed(self, texts: List[str]):
        """
        Generate embeddings for a list of text chunks.
        """
        return self.model.encode(texts, convert_to_numpy=True)