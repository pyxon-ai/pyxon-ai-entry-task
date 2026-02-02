"""
LangGraph ingest graph: extract -> analyze -> chunk -> embed -> store_vector -> store_sql.
"""

import hashlib
from pathlib import Path
from typing import Any

from langgraph.graph import StateGraph, END, START

from src.graphs.state import IngestState
from src.parser.extractors import extract as extract_doc
from src.parser.analyzer import analyze_content
from src.parser.chunkers import chunk_fixed, chunk_dynamic
from src.embeddings import embed as embed_texts
from src.storage.vector_store import VectorStore
from src.storage.sql_store import SQLStore


def _node_extract(state: IngestState) -> dict[str, Any]:
    path = state["file_path"]
    result = extract_doc(path)
    return {
        "raw_text": result["raw_text"],
        "pages_or_sections": result.get("pages_or_sections", []),
    }


def _node_analyze(state: IngestState) -> dict[str, Any]:
    raw_text = state["raw_text"]
    pages_or_sections = state.get("pages_or_sections", [])
    result = analyze_content(raw_text, pages_or_sections)
    return {
        "strategy": result["strategy"],
        "params": result["params"],
    }


def _node_chunk(state: IngestState) -> dict[str, Any]:
    raw_text = state["raw_text"]
    strategy = state["strategy"]
    params = state["params"]
    pages_or_sections = state.get("pages_or_sections", [])

    if strategy == "dynamic":
        chunks = chunk_dynamic(raw_text, pages_or_sections, params)
    else:
        chunks = chunk_fixed(raw_text, params)

    return {"chunks": chunks}


def _node_embed(state: IngestState) -> dict[str, Any]:
    chunks = state["chunks"]
    texts = [c.get("text", "") for c in chunks]
    embeddings = embed_texts(texts)
    return {"embeddings": embeddings}


def _node_store_vector(state: IngestState) -> dict[str, Any]:
    document_id = state["document_id"]
    chunks = state["chunks"]
    embeddings = state["embeddings"]
    store = VectorStore()
    store.add_chunks(
        chunks,
        embeddings,
        document_id=document_id,
        metadata={"strategy": state.get("strategy", "")},
    )
    return {}


def _node_store_sql(state: IngestState) -> dict[str, Any]:
    document_id = state["document_id"]
    path = state.get("file_path", "")
    strategy = state.get("strategy", "")
    format_type = Path(path).suffix.lower() if path else ""
    store = SQLStore()
    store.insert_document(document_id, path=path, format_type=format_type, strategy=strategy)
    chunks_for_sql = [
        {
            "index": c.get("index", i),
            "start": c.get("start", 0),
            "end": c.get("end", 0),
            "metadata": {},
        }
        for i, c in enumerate(state["chunks"])
    ]
    store.insert_chunks(document_id, chunks_for_sql)
    return {}


def _node_document_id(state: IngestState) -> dict[str, Any]:
    """Set document_id from file path (hash) before store nodes."""
    path = state.get("file_path", "")
    h = hashlib.sha256(path.encode("utf-8")).hexdigest()[:16]
    return {"document_id": h}


def build_ingest_graph():
    """Build and compile the ingest StateGraph."""
    graph = StateGraph(IngestState)

    graph.add_node("extract", _node_extract)
    graph.add_node("analyze", _node_analyze)
    graph.add_node("chunk", _node_chunk)
    graph.add_node("embed", _node_embed)
    graph.add_node("document_id", _node_document_id)
    graph.add_node("store_vector", _node_store_vector)
    graph.add_node("store_sql", _node_store_sql)

    graph.add_edge(START, "extract")
    graph.add_edge("extract", "analyze")
    graph.add_edge("analyze", "chunk")
    graph.add_edge("chunk", "document_id")
    graph.add_edge("document_id", "embed")
    graph.add_edge("embed", "store_vector")
    graph.add_edge("store_vector", "store_sql")
    graph.add_edge("store_sql", END)

    return graph.compile()


# Compiled graph for pipeline use
ingest_graph = build_ingest_graph()
