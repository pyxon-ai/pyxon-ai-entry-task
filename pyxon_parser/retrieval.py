import numpy as np
from dataclasses import dataclass
from typing import Any
from rank_bm25 import BM25Okapi
from .textnorm import tokenize_ar_en, normalize_for_keyword, strip_diacritics, nfc, strip_tatweel
from .storage import SqlStore, VectorStore
from .embeddings import E5Embedder

@dataclass
class SearchHit:
    chunk_id: str
    score: float
    source: str
    payload: dict[str, Any] | None

def _rrf(ranks: dict[str, int], k: int = 60) -> dict[str, float]:
    out = {}
    for cid, r in ranks.items():
        out[cid] = 1.0 / (k + r)
    return out

def _unique_ordered(xs: list[str]) -> list[str]:
    seen = set()
    out = []
    for x in xs:
        if x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out

class HybridRetriever:
    def __init__(self, sql: SqlStore, vdb: VectorStore, embedder: E5Embedder):
        self.sql = sql
        self.vdb = vdb
        self.embedder = embedder
        self._bm25 = None
        self._bm25_ids = None

    def rebuild_bm25(self):
        ids, texts = self.sql.get_all_chunks_for_bm25()
        corpus_tokens = [tokenize_ar_en(t) for t in texts]
        self._bm25 = BM25Okapi(corpus_tokens)
        self._bm25_ids = ids

    def _query_variants(self, q: str) -> list[str]:
        q0 = nfc(q or "")
        q1 = strip_tatweel(q0)
        q2 = strip_diacritics(q1)
        q3 = normalize_for_keyword(q0)
        variants = [q0, q2, q3]
        variants = [v.strip() for v in variants if v and v.strip()]
        return _unique_ordered(variants)

    def search(
        self,
        query: str,
        k: int = 5,
        use_bm25: bool = True,
        use_vector: bool = True,
        w_bm25: float = 0.4,
        w_vec: float = 0.6,
        diacritics_aware: bool = True
    ) -> list[SearchHit]:
        qvars = self._query_variants(query) if diacritics_aware else [query]
        candidates: dict[str, dict[str, Any]] = {}

        vec_rrf_all: dict[str, float] = {}
        if use_vector:
            vec_rank: dict[str, int] = {}
            rank_cursor = 1
            for qv in qvars:
                qemb = self.embedder.embed_query(qv)
                res = self.vdb.search(qemb, limit=max(20, k * 6))
                for p in res:
                    cid = p.payload.get("chunk_id") if p.payload else None
                    if not cid:
                        continue
                    if cid not in vec_rank:
                        vec_rank[cid] = rank_cursor
                        rank_cursor += 1
                    candidates.setdefault(cid, {})["payload"] = p.payload
            vec_rrf_all = _rrf(vec_rank)

        bm_rrf_all: dict[str, float] = {}
        if use_bm25:
            if self._bm25 is None:
                self.rebuild_bm25()
            bm_rank: dict[str, int] = {}
            rank_cursor = 1
            for qv in qvars:
                qt = tokenize_ar_en(qv)
                scores = self._bm25.get_scores(qt)
                top_idx = np.argsort(scores)[::-1][:max(20, k * 6)]
                for idx in top_idx:
                    cid = self._bm25_ids[int(idx)]
                    if cid not in bm_rank:
                        bm_rank[cid] = rank_cursor
                        rank_cursor += 1
                    candidates.setdefault(cid, {})
            bm_rrf_all = _rrf(bm_rank)

        fused: dict[str, float] = {}
        for cid in set(list(vec_rrf_all.keys()) + list(bm_rrf_all.keys())):
            fused[cid] = (w_vec * vec_rrf_all.get(cid, 0.0)) + (w_bm25 * bm_rrf_all.get(cid, 0.0))

        ordered = sorted(fused.items(), key=lambda x: x[1], reverse=True)[:k]
        hits = []
        for cid, sc in ordered:
            payload = candidates.get(cid, {}).get("payload")
            hits.append(SearchHit(chunk_id=cid, score=float(sc), source="hybrid", payload=payload))
        return hits
