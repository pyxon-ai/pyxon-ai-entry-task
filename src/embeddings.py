"""
Embedding model loader. Arabic-safe (multilingual model, preserves diacritics).
embed(texts: list[str]) -> list[list[float]]
"""

from typing import List

# Lazy load to avoid slow import when not used
_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        # Multilingual model with Arabic support; preserves diacritics
        _model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    return _model


def embed(texts: List[str]) -> List[List[float]]:
    """
    Embed a list of texts. UTF-8 and Arabic diacritics preserved.
    Returns list of embedding vectors.
    """
    if not texts:
        return []
    model = _get_model()
    embeddings = model.encode(texts, show_progress_bar=False, normalize_embeddings=False)
    return [e.tolist() for e in embeddings]
