"""Hybrid retrieval: vector (semantic) + BM25 (keyword) + knowledge-graph expansion.

Rankings from each retriever are merged with weighted Reciprocal Rank Fusion
(RRF), which is robust to the different score scales of cosine similarity and
BM25. Each result reports which retrievers found it, so the demo/benchmark
can show why a chunk was returned.
"""
from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field

from .embeddings import Embedder
from .storage import SQLStore, VectorStore
from .text import content_tokens

RRF_K = 60


@dataclass
class SearchResult:
    chunk_id: str
    score: float
    text: str
    filename: str
    document_id: int
    section: str
    level: int
    page: int | None
    sources: dict[str, int] = field(default_factory=dict)  # retriever -> rank


class HybridRetriever:
    def __init__(self, sql: SQLStore, vectors: VectorStore, embedder: Embedder,
                 weights: dict[str, float] | None = None):
        self.sql, self.vectors, self.embedder = sql, vectors, embedder
        self.weights = weights or {"vector": 1.0, "keyword": 1.0, "graph": 0.5}

    def _vector(self, query: str, k: int, levels: list[int], doc_ids) -> list[tuple[str, float]]:
        clauses = [{"level": {"$in": levels}}]
        if doc_ids:
            clauses.append({"document_id": {"$in": list(doc_ids)}})
        where = clauses[0] if len(clauses) == 1 else {"$and": clauses}
        return self.vectors.query(self.embedder.embed_one(query, is_query=True), k=k, where=where)

    def _keyword(self, query: str, k: int, levels: list[int], doc_ids) -> list[tuple[str, float]]:
        tokens = content_tokens(query)
        hits: list[tuple[str, float]] = []
        for lvl in levels:
            hits.extend(self.sql.keyword_search(tokens, k=k, level=lvl, doc_ids=doc_ids))
        return sorted(hits, key=lambda x: -x[1])[:k]

    def _graph(self, query: str, k: int, doc_ids) -> list[tuple[str, float]]:
        tokens = list(dict.fromkeys(content_tokens(query)))
        scores: dict[str, float] = defaultdict(float)
        for row in self.sql.terms_for(tokens, doc_ids=doc_ids):
            for cid in json.loads(row["chunk_ids"]):
                scores[cid] += 1.0
            # one hop: related concepts contribute with a damped weight
            for nb in self.sql.neighbors(row["document_id"], row["term"], k=3):
                for r2 in self.sql.terms_for([nb["term"]], doc_ids=[row["document_id"]]):
                    for cid in json.loads(r2["chunk_ids"]):
                        scores[cid] += 0.25 * min(nb["weight"], 3) / 3
        return sorted(scores.items(), key=lambda x: -x[1])[:k]

    def search(
        self,
        query: str,
        k: int = 5,
        mode: str = "hybrid",
        include_summaries: bool = False,
        doc_ids: list[int] | None = None,
    ) -> list[SearchResult]:
        """mode: 'hybrid' | 'vector' | 'keyword' | 'graph'."""
        levels = [0, 1, 2, 3] if include_summaries else [0]
        pool = max(k * 4, 20)
        rankings: dict[str, list[tuple[str, float]]] = {}
        if mode in ("hybrid", "vector"):
            rankings["vector"] = self._vector(query, pool, levels, doc_ids)
        if mode in ("hybrid", "keyword"):
            rankings["keyword"] = self._keyword(query, pool, levels, doc_ids)
        if mode in ("hybrid", "graph"):
            rankings["graph"] = self._graph(query, pool, doc_ids)

        fused: dict[str, float] = defaultdict(float)
        sources: dict[str, dict[str, int]] = defaultdict(dict)
        for name, hits in rankings.items():
            w = self.weights.get(name, 1.0)
            for rank, (cid, _) in enumerate(hits, start=1):
                fused[cid] += w / (RRF_K + rank)
                sources[cid][name] = rank

        top = sorted(fused.items(), key=lambda x: -x[1])[: k * 2]
        rows = self.sql.get_chunks([cid for cid, _ in top])
        results = []
        for cid, score in top:
            r = rows.get(cid)
            if r is None or r["level"] not in levels:
                continue
            results.append(SearchResult(
                chunk_id=cid, score=round(score, 5), text=r["text"], filename=r["filename"],
                document_id=r["document_id"], section=r["section"] or "", level=r["level"],
                page=r["page"], sources=sources[cid],
            ))
        return results[:k]
