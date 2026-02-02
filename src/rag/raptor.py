"""
RAPTOR: hierarchical tree from chunks (summarize, cluster, recurse). Multi-level retrieval.
Arabic-safe (preserve diacritics in summaries). Uses extractive summarization fallback.
"""

from typing import Any

from src.embeddings import embed


def _extractive_summary(text: str, max_sentences: int = 3) -> str:
    """Simple extractive summary: first N sentences. Preserves diacritics."""
    sentences = [s.strip() for s in text.replace("!", ".").replace("?", ".").split(".") if s.strip()]
    return ". ".join(sentences[:max_sentences]) if sentences else text[:500]


def build_raptor_tree(chunks: list[dict[str, Any]], max_levels: int = 2) -> list[dict[str, Any]]:
    """
    Build a shallow RAPTOR tree: level 0 = chunks, level 1 = summarized "parent" nodes.
    Returns flat list of nodes with level and parent ref: {text, level, chunk_indices, index}.
    """
    if not chunks:
        return []

    nodes: list[dict[str, Any]] = []
    for i, c in enumerate(chunks):
        nodes.append({
            "text": c.get("text", ""),
            "level": 0,
            "chunk_indices": [i],
            "index": i,
        })

    if max_levels < 2 or len(chunks) < 2:
        return nodes

    # Level 1: group chunks into 2–4 groups, summarize each
    group_size = max(1, len(chunks) // 3)
    level1: list[dict[str, Any]] = []
    for start in range(0, len(chunks), group_size):
        group = chunks[start : start + group_size]
        combined = " ".join(c.get("text", "") for c in group)
        summary = _extractive_summary(combined, max_sentences=5)
        level1.append({
            "text": summary,
            "level": 1,
            "chunk_indices": list(range(start, min(start + group_size, len(chunks)))),
            "index": len(nodes) + len(level1),
        })
    nodes.extend(level1)
    return nodes


def retrieve_multilevel(
    query: str,
    chunk_nodes: list[dict[str, Any]],
    top_k: int = 5,
    embed_fn: Any = None,
) -> list[dict[str, Any]]:
    """
    Multi-level retrieval: embed query and level-0/level-1 nodes, rank by similarity, return top chunks.
    """
    embed_fn = embed_fn or embed
    if not chunk_nodes:
        return []

    texts = [n.get("text", "") for n in chunk_nodes]
    query_emb = embed_fn([query])[0]
    node_embs = embed_fn(texts)

    def cos_sim(a, b):
        dot = sum(x * y for x, y in zip(a, b))
        na = sum(x * x for x in a) ** 0.5
        nb = sum(x * x for x in b) ** 0.5
        return dot / (na * nb) if na * nb else 0.0

    scored = [(cos_sim(query_emb, ne), i) for i, ne in enumerate(node_embs)]
    scored.sort(key=lambda x: -x[0])

    # Level-0 nodes are chunks (index 0..len(chunks)-1); level-1 are summaries. Always return actual chunk text.
    result = []
    seen_chunks: set[int] = set()
    for _, i in scored:
        node = chunk_nodes[i]
        for ci in node.get("chunk_indices", [i]):
            if ci not in seen_chunks and node.get("level", 0) == 0:
                seen_chunks.add(ci)
                result.append({
                    **node,
                    "score": cos_sim(query_emb, node_embs[i]),
                })
            elif node.get("level", 0) == 1 and ci not in seen_chunks:
                seen_chunks.add(ci)
                if len(result) < top_k:
                    # Resolve to actual chunk text (level-0 nodes are first in list, index = position)
                    chunk_text = chunk_nodes[ci].get("text", "") if 0 <= ci < len(chunk_nodes) else node.get("text", "")
                    result.append({
                        "text": chunk_text,
                        "level": 1,
                        "chunk_index": ci,
                        "score": cos_sim(query_emb, node_embs[i]),
                    })
        if len(result) >= top_k:
            break
    return result[:top_k]
