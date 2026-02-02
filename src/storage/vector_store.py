"""
Chroma vector store wrapper. LangChain-compatible add/query with metadata.
"""

import os
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings


def _default_persist_dir() -> str:
    return os.environ.get("CHROMA_PATH", "./data/chroma")


class VectorStore:
    """Chroma-backed vector store: add chunks with embeddings, query by embedding."""

    def __init__(self, persist_directory: str | None = None, collection_name: str = "documents"):
        self.persist_directory = persist_directory or _default_persist_dir()
        Path(self.persist_directory).mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name
        self._client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_chunks(
        self,
        chunks: list[dict[str, Any]],
        embeddings: list[list[float]],
        document_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add chunk texts with embeddings and metadata (document_id, chunk_index, etc.)."""
        meta = metadata or {}
        ids = []
        metadatas = []
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            chunk_id = f"{document_id}_{i}"
            ids.append(chunk_id)
            chunk_meta = {
                "document_id": document_id,
                "chunk_index": i,
                "start": chunk.get("start", 0),
                "end": chunk.get("end", 0),
                **meta,
            }
            # Chroma requires metadata values to be str, int, float, or bool
            chunk_meta = {k: (v if isinstance(v, (str, int, float, bool)) else str(v)) for k, v in chunk_meta.items()}
            metadatas.append(chunk_meta)
        texts = [c.get("text", "") for c in chunks]
        self._collection.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)

    def query(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        filter_metadata: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Query by embedding; return list of {document, metadata, distance}."""
        where = None
        if filter_metadata:
            where = {k: v for k, v in filter_metadata.items() if v is not None}
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        out: list[dict[str, Any]] = []
        docs = results["documents"][0] or []
        metas = results["metadatas"][0] or []
        dists = results["distances"][0] or []
        for doc, meta, dist in zip(docs, metas, dists):
            out.append({"document": doc, "metadata": meta or {}, "distance": dist})
        return out

    def delete_by_document_id(self, document_id: str) -> None:
        """Remove all chunks for a document."""
        # Chroma where filter
        existing = self._collection.get(where={"document_id": document_id}, include=[])
        if existing["ids"]:
            self._collection.delete(ids=existing["ids"])
