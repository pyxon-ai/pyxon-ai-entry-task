"""RAPTOR-style hierarchical summary tree.

Leaf chunks are clustered by embedding (k-means), each cluster is summarized,
the summaries are embedded, and the process repeats until a single root (or
``max_levels``) remains. Summary nodes are stored next to the leaves (level >= 1)
so the retriever can answer broad "what is this document about?" questions
from upper levels and detail questions from leaves ("collapsed tree" retrieval).

Summarization uses an LLM when one is configured (see :mod:`pyxon_parser.llm`),
otherwise an extractive summary that keeps the original wording and diacritics.
"""
from __future__ import annotations

import math

import numpy as np

from .analyzer import extractive_summary
from .chunking import Chunk
from .embeddings import Embedder


def _kmeans(vectors: np.ndarray, k: int, seed: int = 0) -> np.ndarray:
    from sklearn.cluster import KMeans

    return KMeans(n_clusters=k, n_init=5, random_state=seed).fit_predict(vectors)


def build_tree(
    leaves: list[Chunk],
    leaf_vectors: np.ndarray,
    embedder: Embedder,
    summarize=None,
    branching: int = 5,
    max_levels: int = 3,
) -> tuple[list[Chunk], np.ndarray]:
    """Return (summary_nodes, their_vectors). ``children`` hold indexes of the level below."""
    summarize = summarize or (lambda text: extractive_summary(text, max_sentences=3))
    nodes: list[Chunk] = []
    vectors: list[np.ndarray] = []
    level_nodes, level_vecs = leaves, leaf_vectors

    for level in range(1, max_levels + 1):
        if len(level_nodes) <= 1:
            break
        k = max(1, math.ceil(len(level_nodes) / branching))
        labels = np.zeros(len(level_nodes), dtype=int) if k == 1 else _kmeans(level_vecs, k)
        new_nodes = []
        for cluster in sorted(set(labels.tolist())):
            members = [i for i, lab in enumerate(labels) if lab == cluster]
            members.sort(key=lambda i: level_nodes[i].index)  # keep reading order
            joined = " ".join(level_nodes[i].text for i in members)
            sections = list(dict.fromkeys(level_nodes[i].section for i in members if level_nodes[i].section))
            new_nodes.append(
                Chunk(
                    text=summarize(joined),
                    index=len(new_nodes),
                    section=" / ".join(sections[:3]),
                    strategy="raptor",
                    level=level,
                    children=[level_nodes[i].index for i in members],
                )
            )
        new_vecs = embedder.embed([n.embedding_text() for n in new_nodes])
        nodes.extend(new_nodes)
        vectors.append(new_vecs)
        level_nodes, level_vecs = new_nodes, new_vecs
        if k == 1:
            break

    if not nodes:
        return [], np.zeros((0, leaf_vectors.shape[1]), dtype=np.float32)
    return nodes, np.vstack(vectors)
