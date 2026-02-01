from sentence_transformers import SentenceTransformer

class E5Embedder:
    def __init__(self, model_name: str = "intfloat/multilingual-e5-small", device: str = "cpu"):
        self.model = SentenceTransformer(model_name, device=device)
        self._dim = None

    def dim(self) -> int:
        if self._dim is None:
            v = self.embed_query("ping")
            self._dim = len(v)
        return self._dim

    def embed_passages(self, passages: list[str]) -> list[list[float]]:
        inputs = [("passage: " + (p or "")) for p in passages]
        v = self.model.encode(inputs, normalize_embeddings=True, show_progress_bar=False)
        return v.tolist()

    def embed_query(self, query: str) -> list[float]:
        q = "query: " + (query or "")
        v = self.model.encode([q], normalize_embeddings=True, show_progress_bar=False)[0]
        return v.tolist()
