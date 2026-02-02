"""
LangGraph RAG graph: query -> retrieve (vector + optional SQL filter) -> optional expand (Graph RAG/RAPTOR) -> optional generate (LLM).
"""

from typing import Any

from langgraph.graph import StateGraph, END, START

from src.graphs.state import RAGState
from src.embeddings import embed
from src.storage.vector_store import VectorStore
from src.storage.sql_store import SQLStore


def _node_retrieve(state: RAGState) -> dict[str, Any]:
    query = state["query"]
    top_k = state.get("top_k", 5)
    filter_metadata = state.get("filter_metadata") or {}

    query_embedding = embed([query])[0]
    store = VectorStore()
    results = store.query(query_embedding, top_k=top_k, filter_metadata=filter_metadata or None)

    chunks = [
        {
            "text": r["document"],
            "metadata": r["metadata"],
            "distance": r["distance"],
        }
        for r in results
    ]
    return {"chunks": chunks, "query_embedding": query_embedding}


def _node_expand_graph_raptor(state: RAGState) -> dict[str, Any]:
    """Optional: expand retrieval with Graph RAG / RAPTOR. Here we leave chunks as-is; pipeline can call graph_rag/raptor separately."""
    return {}


def _node_generate(state: RAGState) -> dict[str, Any]:
    """Optional: LLM answer from retrieved context. Placeholder when no API key."""
    chunks = state.get("chunks", [])
    context = "\n\n".join(c.get("text", "") for c in chunks)[:4000]
    # Placeholder: no LLM call unless OPENAI_API_KEY etc. is set
    answer = f"[Retrieved {len(chunks)} chunk(s). Context length: {len(context)} chars. Set OPENAI_API_KEY for LLM answer.]"
    return {"answer": answer}


def build_rag_graph(include_llm: bool = False):
    """Build and compile the RAG StateGraph."""
    graph = StateGraph(RAGState)

    graph.add_node("retrieve", _node_retrieve)
    graph.add_node("expand_graph_raptor", _node_expand_graph_raptor)
    graph.add_node("generate", _node_generate)

    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "expand_graph_raptor")
    if include_llm:
        graph.add_edge("expand_graph_raptor", "generate")
        graph.add_edge("generate", END)
    else:
        graph.add_edge("expand_graph_raptor", END)

    return graph.compile()


# Default: no LLM node in main path; pipeline can add answer separately
rag_graph = build_rag_graph(include_llm=True)
