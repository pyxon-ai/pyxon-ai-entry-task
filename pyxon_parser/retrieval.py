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

from .arabic import DIACRITICS_RE
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
    raw_scores: dict[str, float] = field(default_factory=dict)  # retriever -> its own score (cosine, BM25, graph)
    also_in: list[str] = field(default_factory=list)  # other files holding the same passage


class HybridRetriever:
    def __init__(self, sql: SQLStore, vectors: VectorStore, embedder: Embedder,
                 weights: dict[str, float] | None = None):
        self.sql, self.vectors, self.embedder = sql, vectors, embedder
        self.weights = weights or {"vector": 1.0, "keyword": 1.0, "graph": 0.5}
        # With a neural embedder a vector-only hit is often a genuine paraphrase match, so its top-2
        # survive the filler filter; with the lexical hashing embedder they are mostly noise.
        from .embeddings import HashingEmbedder

        self.keep_top_rank = 0 if isinstance(embedder, HashingEmbedder) else 2
        # ...but only when the semantic match itself is strong (cosine similarity). Override with
        # PYXON_VECTOR_MIN_SIM; the score of every hit is shown in the demo to help calibrate it.
        import os

        self.vector_min_sim = float(os.getenv("PYXON_VECTOR_MIN_SIM", "0.5"))
        self.vector_keep_rank = int(os.getenv("PYXON_VECTOR_KEEP_RANK", "0"))  # 0 = no rank limit

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
        min_relative_score: float = 0.5,
        collapse_duplicates: bool = True,
    ) -> list[SearchResult]:
        """mode: 'hybrid' | 'vector' | 'keyword' | 'graph'.

        In hybrid mode, a result found by only one retriever is kept if its fused score is at least
        ``min_relative_score`` x the top score, or (with a neural embedder) if it is in that
        retriever's top 2, so a semantic-only paraphrase match survives. Set
        ``min_relative_score=0`` to disable the filter.
        """
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
        raw: dict[str, dict[str, float]] = defaultdict(dict)
        for name, hits in rankings.items():
            w = self.weights.get(name, 1.0)
            for rank, (cid, score) in enumerate(hits, start=1):
                fused[cid] += w / (RRF_K + rank)
                sources[cid][name] = rank
                raw[cid][name] = float(score)

        ranked = sorted(fused.items(), key=lambda x: -x[1])
        if len(rankings) > 1 and ranked and min_relative_score > 0:
            # Drop weak filler that only one retriever found.
            best = ranked[0][1]
            neural = self.keep_top_rank > 0

            def keep(cid: str, sc: float) -> bool:
                if len(sources[cid]) > 1:            # confirmed by several retrievers
                    return True
                if neural and "vector" in sources[cid]:
                    # vector-only hit from a neural model: trust its cosine, not its rank. Calibrated
                    # on the demo (multilingual MiniLM): right answers found only semantically score
                    # >= 0.5-0.7, unrelated chunks stay below ~0.4, so rank alone lets noise through.
                    rank_ok = not self.vector_keep_rank or sources[cid]["vector"] <= self.vector_keep_rank
                    return rank_ok and raw[cid]["vector"] >= self.vector_min_sim
                return sc >= min_relative_score * best

            filtered = [(cid, sc) for cid, sc in ranked if keep(cid, sc)]
            ranked = filtered or ranked[:1]  # never return nothing when something matched
        top = ranked[: k * 4]
        rows = self.sql.get_chunks([cid for cid, _ in top])
        results: list[SearchResult] = []
        keys: list[str] = []
        for cid, score in top:
            r = rows.get(cid)
            if r is None or r["level"] not in levels:
                continue
            if collapse_duplicates:
                # The same passage indexed from two files (e.g. book.txt and book.pdf) is shown
                # once, under its best-ranked copy, with the other files listed in ``also_in``.
                key = r["normalized_text"].replace(" ", "")
                dup = next((i for i, other in enumerate(keys) if _same_passage(key, other)), None)
                if dup is not None:
                    kept = results[dup]
                    if len(DIACRITICS_RE.findall(r["text"])) > len(DIACRITICS_RE.findall(kept.text)):
                        # show the copy with the most harakat (e.g. the TXT, not a PDF that lost
                        # some marks); keep the rank and retriever evidence of the better hit
                        kept.also_in.append(kept.filename)
                        kept.text, kept.filename, kept.chunk_id = r["text"], r["filename"], cid
                        kept.document_id, kept.section, kept.page = r["document_id"], r["section"] or "", r["page"]
                    elif r["filename"] != kept.filename:
                        kept.also_in.append(r["filename"])
                    kept.also_in = [f for f in dict.fromkeys(kept.also_in) if f != kept.filename]
                    continue
                keys.append(key)
            results.append(SearchResult(
                chunk_id=cid, score=round(score, 5), text=r["text"], filename=r["filename"],
                document_id=r["document_id"], section=r["section"] or "", level=r["level"],
                page=r["page"], sources=sources[cid], raw_scores={k: round(v, 3) for k, v in raw[cid].items()},
            ))
        # keep scanning past k so duplicates of the top hits are still recorded in also_in
        return results[:k]


def _same_passage(a: str, b: str, threshold: float = 0.95) -> bool:
    """Near-identical normalized texts (diacritics already removed, so a PDF copy that lost a few
    marks or spaces still matches its TXT original)."""
    if a == b:
        return True
    if not a or not b or min(len(a), len(b)) / max(len(a), len(b)) < threshold:
        return False
    from difflib import SequenceMatcher

    return SequenceMatcher(None, a, b, autojunk=False).ratio() >= threshold
