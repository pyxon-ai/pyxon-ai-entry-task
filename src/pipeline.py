"""
Pipeline entrypoint: run_ingest(file_path), run_rag(query, top_k, use_graph_rag, use_raptor).
Uses LangGraph compiled ingest and RAG graphs.
"""

from pathlib import Path
from typing import Any

from src.graphs.ingest_graph import ingest_graph
from src.graphs.rag_graph import rag_graph
from src.storage.sql_store import SQLStore
from src.storage.vector_store import VectorStore
from src.rag.graph_rag import build_graph, retrieve_subgraph
from src.rag.raptor import build_raptor_tree, retrieve_multilevel


def run_ingest(file_path: str | Path) -> dict[str, Any]:
    """
    Run the ingest LangGraph for a single document.
    Returns final state (document_id, chunks, strategy, etc.).
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    initial: dict[str, Any] = {"file_path": str(file_path)}
    result = ingest_graph.invoke(initial)
    return result


def delete_document(document_id: str) -> None:
    """Remove all data for a document from vector store and SQL store."""
    VectorStore().delete_by_document_id(document_id)
    SQLStore().delete_document(document_id)


def run_rag(
    query: str,
    top_k: int = 5,
    use_graph_rag: bool = False,
    use_raptor: bool = False,
    filter_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Run the RAG LangGraph: retrieve from vector store, optionally expand with Graph RAG/RAPTOR.
    Returns state with chunks and optional answer.
    """
    # Fetch more candidates when expanding with graph/raptor for better recall, then re-rank
    fetch_k = max(top_k * 2, 10) if (use_graph_rag or use_raptor) else top_k
    initial: dict[str, Any] = {
        "query": query,
        "top_k": fetch_k,
        "filter_metadata": filter_metadata or {},
    }
    result = rag_graph.invoke(initial)
    chunks = result.get("chunks", [])

    # Chroma returns distance (lower = better). Use -distance as score for sorting.
    def score_of(c: dict) -> float:
        d = c.get("distance")
        if d is not None:
            return -float(d)
        return float(c.get("score", 0))

    scored = [{"text": c.get("text", ""), "metadata": c.get("metadata", {}), "score": score_of(c)} for c in chunks]

    if (use_graph_rag or use_raptor) and scored:
        sql = SQLStore()
        doc_ids = {c.get("metadata", {}).get("document_id") for c in scored if c.get("metadata")}
        all_chunks_flat: list[dict] = []
        for doc_id in doc_ids:
            if doc_id:
                for r in sql.get_chunks_by_document_id(doc_id):
                    all_chunks_flat.append({
                        "text": "",
                        "index": r.get("chunk_index", 0),
                        "start": r.get("start", 0),
                        "end": r.get("end", 0),
                        "document_id": doc_id,
                    })
        for c in scored:
            meta = c.get("metadata", {})
            doc_id, idx = meta.get("document_id"), meta.get("chunk_index", -1)
            for ac in all_chunks_flat:
                if ac.get("document_id") == doc_id and ac.get("index") == idx:
                    ac["text"] = c.get("text", "")
                    break

        merged: dict[tuple, dict] = {}
        for c in scored:
            k = (c.get("metadata", {}).get("document_id"), c.get("metadata", {}).get("chunk_index", -1))
            if k not in merged or c.get("score", 0) > merged[k].get("score", 0):
                merged[k] = {"text": c.get("text", ""), "metadata": c.get("metadata", {}), "score": c.get("score", 0)}

        if use_graph_rag and all_chunks_flat:
            G = build_graph(all_chunks_flat)
            for e in retrieve_subgraph(query, all_chunks_flat, G, top_k=top_k * 2):
                idx = e.get("index", -1)
                doc_id = all_chunks_flat[idx].get("document_id", "") if 0 <= idx < len(all_chunks_flat) else ""
                k = (doc_id, idx)
                s = e.get("score", 0.0)
                if k not in merged or s > merged[k].get("score", 0):
                    merged[k] = {"text": e.get("text", ""), "metadata": {}, "score": s}

        if use_raptor and all_chunks_flat:
            for e in retrieve_multilevel(query, build_raptor_tree(all_chunks_flat), top_k=top_k * 2):
                idx = e.get("index", e.get("chunk_index", -1))
                doc_id = all_chunks_flat[idx].get("document_id", "") if 0 <= idx < len(all_chunks_flat) else ""
                k = (doc_id, idx)
                s = e.get("score", 0.0)
                if k not in merged or s > merged[k].get("score", 0):
                    merged[k] = {"text": e.get("text", ""), "metadata": {}, "score": s}

        result["chunks"] = sorted(merged.values(), key=lambda x: -x.get("score", 0))[:top_k]
    else:
        result["chunks"] = sorted(scored, key=lambda x: -x.get("score", 0))[:top_k]

    return result
