"""
Graph RAG: build knowledge graph from chunks (entities/relations), entity-aware retrieval.
Arabic-safe (preserve diacritics). Uses NetworkX for in-memory graph.
"""

import re
from typing import Any

import networkx as nx

from src.embeddings import embed


def _simple_entities(text: str) -> list[str]:
    """Heuristic entity extraction: capitalized phrases and Arabic-like words. Preserves diacritics."""
    # Simple: words that look like proper nouns (capitalized) or Arabic words (Unicode range)
    words = re.findall(r"[A-Z][a-z\u0600-\u06FF\u064B-\u0652]+(?:\s+[A-Z][a-z\u0600-\u06FF\u064B-\u0652]+)*|[a-zA-Z]{3,}|\u0600-\u06FF+", text)
    return list(dict.fromkeys(w.strip() for w in words if len(w.strip()) > 1))[:20]


def build_graph(chunks: list[dict[str, Any]]) -> nx.DiGraph:
    """
    Build a simple knowledge graph from chunks: entities from each chunk, edges between co-occurring.
    Arabic-safe (no stripping of diacritics).
    """
    G = nx.DiGraph()
    chunk_id_to_entities: dict[int, list[str]] = {}

    for c in chunks:
        idx = c.get("index", len(chunk_id_to_entities))
        text = c.get("text", "")
        entities = _simple_entities(text)
        chunk_id_to_entities[idx] = entities
        for e in entities:
            G.add_node(e, chunk_index=idx)
        for i, e1 in enumerate(entities):
            for e2 in entities[i + 1 : i + 3]:
                if e1 != e2:
                    G.add_edge(e1, e2, weight=1)

    # Link chunks that share entities
    for idx, entities in chunk_id_to_entities.items():
        for e in entities:
            if G.has_node(e):
                G.nodes[e]["chunk_index"] = idx
    return G


def retrieve_subgraph(
    query: str,
    chunks: list[dict[str, Any]],
    graph: nx.DiGraph | None,
    top_k: int = 5,
    embed_fn: Any = None,
) -> list[dict[str, Any]]:
    """
    Entity-aware retrieval: embed query, find nearby chunks; optionally expand via graph.
    If graph is None, falls back to embedding similarity over chunks only.
    """
    embed_fn = embed_fn or embed
    if not chunks:
        return []

    texts = [c.get("text", "") for c in chunks]
    query_emb = embed_fn([query])[0]
    chunk_embs = embed_fn(texts)

    # Cosine similarity
    def cos_sim(a, b):
        dot = sum(x * y for x, y in zip(a, b))
        na = sum(x * x for x in a) ** 0.5
        nb = sum(x * x for x in b) ** 0.5
        if na * nb == 0:
            return 0.0
        return dot / (na * nb)

    scored = [(cos_sim(query_emb, ce), i) for i, ce in enumerate(chunk_embs)]
    scored.sort(key=lambda x: -x[0])
    top_indices = [i for _, i in scored[: top_k * 2]]

    if graph is not None and top_indices:
        # Expand: add chunks that share entities with top chunks
        expanded = set(top_indices)
        for idx in top_indices:
            chunk_text = chunks[idx].get("text", "")
            for entity in _simple_entities(chunk_text):
                if graph.has_node(entity):
                    ci = graph.nodes[entity].get("chunk_index")
                    if ci is not None:
                        expanded.add(ci)
        top_indices = list(expanded)[: top_k * 2]

    result = []
    seen = set()
    for _, i in sorted(
        [(cos_sim(query_emb, chunk_embs[i]), i) for i in top_indices],
        key=lambda x: -x[0],
    ):
        if i in seen:
            continue
        seen.add(i)
        result.append({**chunks[i], "score": cos_sim(query_emb, chunk_embs[i])})
        if len(result) >= top_k:
            break
    return result
