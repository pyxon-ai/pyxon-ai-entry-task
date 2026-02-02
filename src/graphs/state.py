"""
LangGraph state types: ingest and RAG.
"""

from typing import Any, TypedDict


class IngestState(TypedDict, total=False):
    file_path: str
    raw_text: str
    pages_or_sections: list[dict[str, Any]]
    strategy: str
    params: dict[str, Any]
    chunks: list[dict[str, Any]]
    embeddings: list[list[float]]
    document_id: str


class RAGState(TypedDict, total=False):
    query: str
    query_embedding: list[float]
    top_k: int
    filter_metadata: dict[str, Any]
    chunks: list[dict[str, Any]]
    answer: str
