import time
import random
from typing import Any

def _now_ms() -> int:
    return int(time.time() * 1000)

def _percentile(xs: list[float], p: float) -> float:
    if not xs:
        return 0.0
    ys = sorted(xs)
    k = int((len(ys) - 1) * p)
    return float(ys[k])

def _safe_lower(s: str) -> str:
    return (s or "").strip().lower()

def _strip_diacritics_ar(s: str) -> str:
    if not s:
        return ""
    diacs = set([
        "\u064b","\u064c","\u064d","\u064e","\u064f","\u0650","\u0651","\u0652","\u0653","\u0654","\u0655",
        "\u0670"
    ])
    return "".join(ch for ch in s if ch not in diacs)

def _tokenize_kw(s: str) -> list[str]:
    s = _safe_lower(s)
    out = []
    cur = []
    for ch in s:
        if ch.isalnum() or ch in ("_",):
            cur.append(ch)
        else:
            if cur:
                out.append("".join(cur))
                cur = []
    if cur:
        out.append("".join(cur))
    return out

def _pick_query_from_chunk(text: str, prefer_ar: bool = True) -> str:
    t = (text or "").strip()
    if not t:
        return ""
    lines = [x.strip() for x in t.splitlines() if x and x.strip()]
    if lines:
        cand = max(lines, key=len)
    else:
        cand = t
    cand = " ".join(cand.split())
    if len(cand) <= 80:
        return cand
    start = max(0, (len(cand) // 2) - 60)
    seg = cand[start:start+120]
    toks = seg.split()
    if len(toks) >= 8:
        toks = toks[:12]
    return " ".join(toks).strip()

def _contains_any_kw(hay: str, q: str, diacritics_aware: bool) -> bool:
    if not hay or not q:
        return False
    h = hay
    qq = q
    if diacritics_aware:
        h = _strip_diacritics_ar(h)
        qq = _strip_diacritics_ar(qq)
    ht = set(_tokenize_kw(h))
    qt = [x for x in _tokenize_kw(qq) if len(x) >= 3]
    if not qt:
        return False
    hit = 0
    for w in qt:
        if w in ht:
            hit += 1
    return hit >= max(1, min(2, len(qt)//3))

def auto_generate_cases(sql, max_docs: int = 5, per_doc: int = 2, seed: int = 7) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    docs = sql.list_documents(limit=max_docs) if hasattr(sql, "list_documents") else []
    cases = []
    for d in docs:
        doc_id = d.get("doc_id")
        if not doc_id:
            continue
        chunks = sql.list_chunks_by_doc(doc_id, limit=200) if hasattr(sql, "list_chunks_by_doc") else []
        chunks = [c for c in chunks if (c.get("text_raw") or "").strip()]
        if not chunks:
            continue
        rng.shuffle(chunks)
        picked = chunks[:per_doc]
        for c in picked:
            q = _pick_query_from_chunk(c.get("text_raw") or "")
            if not q:
                continue
            cases.append({
                "case_id": f"{doc_id}:{c.get('chunk_index', 0)}",
                "doc_id": doc_id,
                "chunk_id": c.get("chunk_id"),
                "query": q,
                "notes": "auto_generated",
                "k_suggest": 5,
                "created_at_ms": _now_ms(),
            })
    return cases

def run_benchmark(sql, retriever, cases: list[dict[str, Any]], k: int = 5, diacritics_aware: bool = True) -> dict[str, Any]:
    if not cases:
        return {"error": "no_benchmark_cases"}

    lat = []
    hits = 0
    rr_sum = 0.0
    per_case = []

    for c in cases:
        q = (c.get("query") or "").strip()
        gold_chunk = c.get("chunk_id")
        gold_doc = c.get("doc_id")

        t0 = time.perf_counter()
        res = retriever.search(q, k=k, use_bm25=True, use_vector=True, diacritics_aware=diacritics_aware)
        t1 = time.perf_counter()
        dt_ms = (t1 - t0) * 1000.0
        lat.append(dt_ms)

        top = res[:k] if res else []
        found = False
        rank = None

        for i, r in enumerate(top, start=1):
            pid = r.get("chunk_id") or r.get("payload", {}).get("chunk_id")
            did = r.get("doc_id") or r.get("payload", {}).get("doc_id")
            txt = r.get("text") or r.get("text_raw") or ""
            if gold_chunk and pid == gold_chunk:
                found = True
                rank = i
                break
            if (not gold_chunk) and gold_doc and did == gold_doc:
                found = True
                rank = i
                break
            if (not found) and gold_doc and did == gold_doc and _contains_any_kw(txt, q, diacritics_aware):
                found = True
                rank = i
                break

        if found:
            hits += 1
            rr_sum += (1.0 / float(rank if rank else 1))

        per_case.append({
            "case_id": c.get("case_id"),
            "query": q,
            "gold_doc": gold_doc,
            "gold_chunk": gold_chunk,
            "hit": bool(found),
            "rank": rank,
            "latency_ms": float(dt_ms),
        })

    n = len(cases)
    recall = hits / max(1, n)
    mrr = rr_sum / max(1, n)

    out = {
        "n_cases": n,
        "k": int(k),
        "diacritics_aware": bool(diacritics_aware),
        "recall_at_k": float(recall),
        "mrr_at_k": float(mrr),
        "latency_ms": {
            "avg": float(sum(lat)/max(1, len(lat))),
            "p95": float(_percentile(lat, 0.95)),
            "max": float(max(lat) if lat else 0.0),
        },
        "cases": per_case,
        "ts_ms": _now_ms(),
    }
    return out
