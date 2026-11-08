"""Lightweight knowledge graph (Graph-RAG style).

Nodes are key concepts (normalized content terms that matter in their chunk
by TF-IDF); edges connect concepts that co-occur in the same chunk, weighted
by how often. Term centrality (PageRank) surfaces the document's main
concepts, and at query time the graph expands query terms to related
concepts so the retriever can reach chunks that never use the query's exact
words.
"""
from __future__ import annotations

import math
from collections import Counter, defaultdict
from itertools import combinations

import networkx as nx

from .text import content_tokens


def build_graph(chunk_ids: list[str], texts: list[str], terms_per_chunk: int = 8):
    tokenized = [content_tokens(t, expand=False) for t in texts]
    df = Counter(t for toks in tokenized for t in set(toks))
    n = len(texts)

    chunk_terms: dict[str, list[str]] = {}
    for cid, toks in zip(chunk_ids, tokenized):
        tf = Counter(toks)
        scored = {t: c * math.log((1 + n) / (1 + df[t]) + 1) for t, c in tf.items() if df[t] < max(2, 0.8 * n) or n < 3}
        chunk_terms[cid] = [t for t, _ in sorted(scored.items(), key=lambda x: (-x[1], x[0]))[:terms_per_chunk]]

    g = nx.Graph()
    term_chunks: dict[str, list[str]] = defaultdict(list)
    freq = Counter()
    for cid, terms in chunk_terms.items():
        for t in terms:
            term_chunks[t].append(cid)
            freq[t] += 1
            g.add_node(t)
        for a, b in combinations(sorted(terms), 2):
            w = g[a][b]["weight"] + 1 if g.has_edge(a, b) else 1
            g.add_edge(a, b, weight=w)

    centrality = nx.pagerank(g, weight="weight") if g.number_of_edges() else {t: 1 / max(len(g), 1) for t in g}
    terms = [
        {"term": t, "frequency": freq[t], "centrality": round(centrality.get(t, 0.0), 6), "chunk_ids": term_chunks[t]}
        for t in g.nodes
    ]
    edges = [(a, b, float(d["weight"])) for a, b, d in g.edges(data=True)]
    return terms, edges
