from app.embeddings.embedder import Embedder
from app.storage.vector_store import VectorStore


class Retriever:
    def __init__(self, top_k: int = 5):
        self.embedder = Embedder()
        self.vector_store = VectorStore()
        self.top_k = top_k

    def retrieve(self, query: str):
        """
        Retrieve top-k relevant chunks for a given query.
        """
        # Embed query
        query_vector = self.embedder.embed([query])[0]

        # Query vector store
        results = self.vector_store.query(
            query_vector=query_vector,
            top_k=self.top_k
        )

        # Chroma returns lists inside dict
        texts = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]

        retrieved_chunks = []

        for text, meta in zip(texts, metadatas):
            retrieved_chunks.append({
                "doc_id": meta.get("doc_id"),
                "chunk_id": meta.get("chunk_id"),
                "text": text
            })

        return retrieved_chunks