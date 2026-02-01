import re
from typing import Any
from .textnorm import normalize_for_keyword, arabic_ratio, latin_ratio, diacritics_ratio

_MD_HEADING = re.compile(r"^\s*#{1,6}\s+\S+")
_NUM_HEADING = re.compile(r"^\s*\d{1,3}(\.\d{1,3})*\s*[\)\.\-]?\s+\S+")
_BULLET = re.compile(r"^\s*(?:[-*•–]|(\d{1,3}[\)\.\-]))\s+\S+")
_TABLEISH = re.compile(r"(\|.*\|)|(\s{3,}\S)")

_AR_SENT_SPLIT = re.compile(r"([؟\!\.\؛\n]+)")
_AR_SOFT_SPLIT = re.compile(r"([،\:]+)")

def _clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)

def _var(xs: list[float]) -> float:
    if not xs:
        return 0.0
    m = sum(xs) / len(xs)
    return sum((x - m) ** 2 for x in xs) / len(xs)

def analyze_structure(full_text: str, pages: list[str]) -> dict[str, Any]:
    lines = [l.rstrip() for l in full_text.splitlines()]
    nonempty = [l.strip() for l in lines if l and l.strip()]
    n_lines = len(lines)
    n_nonempty = len(nonempty)
    lens = [len(l) for l in nonempty]
    avg_len = (sum(lens) / max(1, n_nonempty))
    len_var = _var([float(x) for x in lens])

    blank_ratio = (n_lines - n_nonempty) / max(1, n_lines)

    md_head = sum(1 for l in nonempty if _MD_HEADING.match(l)) / max(1, n_nonempty)
    num_head = sum(1 for l in nonempty if _NUM_HEADING.match(l)) / max(1, n_nonempty)
    heading_ratio = md_head + num_head

    bullet_ratio = sum(1 for l in nonempty if _BULLET.match(l) and not _NUM_HEADING.match(l)) / max(1, n_nonempty)
    table_ratio = sum(1 for l in nonempty if _TABLEISH.search(l)) / max(1, n_nonempty)

    short_ratio = sum(1 for l in nonempty if len(l) <= 40) / max(1, n_nonempty)
    long_ratio = sum(1 for l in nonempty if len(l) >= 220) / max(1, n_nonempty)

    ar = arabic_ratio(full_text)
    la = latin_ratio(full_text)
    dia = diacritics_ratio(full_text)

    structure_score = (
        0.55 * _clamp01(heading_ratio / 0.06) +
        0.25 * _clamp01(blank_ratio / 0.22) +
        0.20 * _clamp01(short_ratio / 0.45)
    )

    template_score = (
        0.55 * _clamp01((bullet_ratio + table_ratio) / 0.35) +
        0.25 * _clamp01((0.05 - heading_ratio) / 0.05) +
        0.20 * _clamp01((120.0 - avg_len) / 120.0)
    )

    narrative_score = (
        0.55 * _clamp01(long_ratio / 0.12) +
        0.25 * _clamp01((0.06 - heading_ratio) / 0.06) +
        0.20 * _clamp01((0.10 - blank_ratio) / 0.10)
    )

    doc_type = "structured"
    if template_score >= max(structure_score, narrative_score) + 0.10:
        doc_type = "template"
    elif narrative_score >= max(structure_score, template_score) + 0.10:
        doc_type = "narrative"

    strategy = "dynamic"
    if doc_type == "template":
        strategy = "fixed"
    else:
        strategy = "dynamic"

    why = []
    if doc_type == "structured":
        if heading_ratio >= 0.06:
            why.append(f"Detected multiple section headers (heading_ratio={heading_ratio:.3f})")
        if blank_ratio >= 0.22:
            why.append(f"Paragraph separation is high (blank_line_ratio={blank_ratio:.3f})")
        if len_var >= 8000:
            why.append(f"Line length variance suggests mixed structure (len_var={len_var:.0f})")
        why.append("Using dynamic chunking to preserve section/topic boundaries")
    elif doc_type == "template":
        if bullet_ratio + table_ratio >= 0.25:
            why.append(f"List/table-like patterns are high (bullet_ratio={bullet_ratio:.3f}, table_like_ratio={table_ratio:.3f})")
        if heading_ratio < 0.02:
            why.append(f"Few or no real headings detected (heading_ratio={heading_ratio:.3f})")
        why.append("Using fixed chunking for uniform template-like content")
    else:
        if long_ratio >= 0.10:
            why.append(f"Large narrative blocks detected (long_line_ratio={long_ratio:.3f})")
        if blank_ratio < 0.10:
            why.append(f"Low paragraph breaks (blank_line_ratio={blank_ratio:.3f})")
        if heading_ratio < 0.02:
            why.append(f"Single/no headings detected (heading_ratio={heading_ratio:.3f})")
        why.append("Using narrative-aware dynamic splitting (sentence-first)")

    signals = [
        f"md_heading_ratio={md_head:.3f}",
        f"numbered_heading_ratio={num_head:.3f}",
        f"heading_ratio={heading_ratio:.3f} vs 0.060",
        f"bullet_ratio={bullet_ratio:.3f}",
        f"table_like_ratio={table_ratio:.3f}",
        f"blank_line_ratio={blank_ratio:.3f} vs 0.220",
        f"short_line_ratio={short_ratio:.3f}",
        f"long_line_ratio={long_ratio:.3f}",
        f"avg_line_len={avg_len:.2f}",
        f"line_len_variance={len_var:.0f}",
        f"scores: structured={structure_score:.3f} template={template_score:.3f} narrative={narrative_score:.3f}"
    ]

    decision = f"{strategy} because doc_type={doc_type}"

    return {
        "strategy": strategy,
        "doc_type": doc_type,
        "scores": {"structured": float(structure_score), "template": float(template_score), "narrative": float(narrative_score)},
        "signals": signals,
        "why": why,
        "decision": decision,
        "n_pages": len(pages),
        "n_lines": n_lines,
        "n_nonempty": n_nonempty,
        "avg_line_len": avg_len,
        "line_len_variance": len_var,
        "short_line_ratio": short_ratio,
        "long_line_ratio": long_ratio,
        "blank_line_ratio": blank_ratio,
        "heading_ratio": heading_ratio,
        "bullet_ratio": bullet_ratio,
        "table_like_ratio": table_ratio,
        "ar_ratio": ar,
        "latin_ratio": la,
        "diacritics_ratio": dia,
    }

def _split_by_headings(text: str) -> list[tuple[str, str]]:
    lines = text.splitlines()
    blocks = []
    cur_title = "ROOT"
    cur = []
    for ln in lines:
        s = ln.strip()
        if s and ( _MD_HEADING.match(s) or _NUM_HEADING.match(s) ) and len(s) <= 140:
            if cur:
                blocks.append((cur_title, "\n".join(cur).strip()))
            cur_title = s[:140]
            cur = []
        else:
            cur.append(ln)
    if cur:
        blocks.append((cur_title, "\n".join(cur).strip()))
    return [(t, b) for (t, b) in blocks if b and b.strip()]

def _sentence_split_ar(text: str) -> list[str]:
    t = text.strip()
    if not t:
        return []
    parts = _AR_SENT_SPLIT.split(t)
    out = []
    buf = ""
    for p in parts:
        if not p:
            continue
        if _AR_SENT_SPLIT.fullmatch(p):
            buf = (buf + p).strip()
            if buf:
                out.append(buf)
            buf = ""
        else:
            buf = (buf + " " + p).strip() if buf else p.strip()
    if buf:
        out.append(buf.strip())
    return [x for x in out if x and x.strip()]

def _pack_sentences(sentences: list[str], chunk_size: int, overlap_sents: int) -> list[tuple[int, int, str]]:
    if not sentences:
        return []
    spans = []
    idx_map = []
    cursor = 0
    for s in sentences:
        s = (s or "").strip()
        if not s:
            cursor += 1
            continue
        start = cursor
        end = start + len(s)
        idx_map.append((start, end, s))
        cursor = end + 1

    i = 0
    cur = []
    cur_len = 0

    while i < len(idx_map):
        s_start, s_end, s_txt = idx_map[i]
        slen = len(s_txt)

        if not cur:
            if slen > chunk_size:
                subs = _recursive_split(s_txt, chunk_size, 0)
                for cs, ce, txt in subs:
                    txt = (txt or "").strip()
                    if txt:
                        spans.append((s_start + cs, s_start + ce, txt))
                i += 1
                continue
            cur = [(s_start, s_end, s_txt)]
            cur_len = slen
            i += 1
            continue

        if cur_len + 1 + slen <= chunk_size:
            cur.append((s_start, s_end, s_txt))
            cur_len += 1 + slen
            i += 1
            continue

        cs = cur[0][0]
        ce = cur[-1][1]
        txt = " ".join(x[2] for x in cur).strip()
        if txt:
            spans.append((cs, ce, txt))

        if overlap_sents > 0:
            cur = cur[-overlap_sents:]
            cur_len = sum(len(x[2]) for x in cur) + max(0, len(cur) - 1)
            if cur_len >= chunk_size:
                cur = []
                cur_len = 0
        else:
            cur = []
            cur_len = 0

    if cur:
        cs = cur[0][0]
        ce = cur[-1][1]
        txt = " ".join(x[2] for x in cur).strip()
        if txt:
            spans.append((cs, ce, txt))

    return spans

def _recursive_split(text: str, chunk_size: int, overlap: int) -> list[tuple[int, int, str]]:
    t = text.strip()
    if not t:
        return []
    if len(t) <= chunk_size:
        return [(0, len(t), t)]
    seps = ["\n\n", "\n", "؟", "؛", "!", ". ", "،", ": ", " "]
    parts = [t]
    for sep in seps:
        new_parts = []
        for p in parts:
            if len(p) <= chunk_size:
                new_parts.append(p)
            else:
                spl = p.split(sep)
                if len(spl) == 1:
                    new_parts.append(p)
                else:
                    acc = ""
                    for piece in spl:
                        piece = piece.strip()
                        if not piece:
                            continue
                        cand = (acc + (sep if acc else "") + piece).strip()
                        if len(cand) <= chunk_size:
                            acc = cand
                        else:
                            if acc:
                                new_parts.append(acc)
                            acc = piece
                    if acc:
                        new_parts.append(acc)
        parts = new_parts
    chunks = []
    cursor = 0
    for p in parts:
        p = p.strip()
        if not p:
            continue
        start = t.find(p, cursor)
        if start < 0:
            start = cursor
        end = start + len(p)
        chunks.append((start, end, p))
        cursor = end
    if overlap > 0 and len(chunks) > 1:
        out = []
        for i, (s, e, c) in enumerate(chunks):
            if i == 0:
                out.append((s, e, c))
                continue
            ps, pe, pc = out[-1]
            ov_start = max(ps, e - overlap)
            merged = t[ov_start:e].strip()
            out.append((ov_start, e, merged))
        chunks = out
    return chunks

def chunk_fixed(doc_id: str, pages: list[str], metrics: dict[str, Any]) -> list[dict[str, Any]]:
    full = "\n\n".join([p for p in pages if p and p.strip()])
    chunk_size = 1100
    overlap = 150
    spans = _recursive_split(full, chunk_size, overlap)
    out = []
    for i, (cs, ce, txt) in enumerate(spans):
        raw = txt.strip()
        kw = normalize_for_keyword(raw)
        lang = {"ar_ratio": arabic_ratio(raw), "latin_ratio": latin_ratio(raw), "dia_ratio": diacritics_ratio(raw)}
        out.append({
            "chunk_id": f"{doc_id}:{i}",
            "doc_id": doc_id,
            "chunk_index": i,
            "page_start": 1,
            "page_end": max(1, len(pages)),
            "section_path": "FIXED",
            "char_start": cs,
            "char_end": ce,
            "text_raw": raw,
            "text_kw": kw,
            "lang": lang
        })
    return out

def chunk_dynamic(doc_id: str, pages: list[str], metrics: dict[str, Any]) -> list[dict[str, Any]]:
    chunk_size = 850
    overlap = 140
    out = []
    idx = 0
    global_cursor = 0
    doc_type = (metrics or {}).get("doc_type", "structured")

    for p_i, page in enumerate(pages, start=1):
        text = (page or "").strip()
        if not text:
            continue

        if doc_type == "narrative":
            spans = _recursive_split(text, 900, 120)
            for (cs, ce, txt) in spans:
                raw = txt.strip()
                if not raw:
                    continue
                kw = normalize_for_keyword(raw)
                lang = {"ar_ratio": arabic_ratio(raw), "latin_ratio": latin_ratio(raw), "dia_ratio": diacritics_ratio(raw)}
                out.append({
                    "chunk_id": f"{doc_id}:{idx}",
                    "doc_id": doc_id,
                    "chunk_index": idx,
                    "page_start": p_i,
                    "page_end": p_i,
                    "section_path": "NARRATIVE",
                    "char_start": global_cursor + cs,
                    "char_end": global_cursor + ce,
                    "text_raw": raw,
                    "text_kw": kw,
                    "lang": lang
                })
                idx += 1
            global_cursor += len(text) + 2
            continue

        blocks = _split_by_headings(text)
        if not blocks:
            blocks = [("PAGE", text)]
        for title, blk in blocks:
            spans = _recursive_split(blk, chunk_size, overlap)
            for (cs, ce, txt) in spans:
                raw = txt.strip()
                if not raw:
                    continue
                kw = normalize_for_keyword(raw)
                lang = {"ar_ratio": arabic_ratio(raw), "latin_ratio": latin_ratio(raw), "dia_ratio": diacritics_ratio(raw)}
                out.append({
                    "chunk_id": f"{doc_id}:{idx}",
                    "doc_id": doc_id,
                    "chunk_index": idx,
                    "page_start": p_i,
                    "page_end": p_i,
                    "section_path": title,
                    "char_start": global_cursor + cs,
                    "char_end": global_cursor + ce,
                    "text_raw": raw,
                    "text_kw": kw,
                    "lang": lang
                })
                idx += 1
        global_cursor += len(text) + 2
    return out
