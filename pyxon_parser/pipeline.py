import io
import time
import hashlib
import uuid
import zipfile
import re
import html
import os
import tracemalloc
import faulthandler
from dataclasses import dataclass
from typing import Any, Callable

import fitz

from .textnorm import nfc
from .storage import SqlStore, VectorStore
from .embeddings import E5Embedder
from .chunking import analyze_structure, chunk_fixed, chunk_dynamic

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

try:
    import torch
    torch.set_num_threads(1)
except Exception:
    pass

@dataclass
class IngestResult:
    doc_id: str
    filename: str
    file_type: str
    strategy: str
    metrics: dict[str, Any]
    n_pages: int
    n_chunks: int
    elapsed_ms: int

def _sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def _ext_from_name(name: str) -> str:
    parts = name.rsplit(".", 1)
    return parts[-1].lower() if len(parts) == 2 else "unknown"

def _clean_text(t: str) -> str:
    if not t:
        return ""
    t = t.replace("\u00ad", "")
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    t = "\n".join([ln.rstrip() for ln in t.splitlines()])
    return t.strip()

def _chunk_as_pages(text: str, page_char_limit: int) -> list[str]:
    text = _clean_text(text)
    if not text:
        return []
    out = []
    i = 0
    n = len(text)
    while i < n:
        seg = text[i:i+page_char_limit].strip()
        if seg:
            out.append(nfc(seg))
        i += page_char_limit
    return out

def _load_pdf_pages(b: bytes) -> list[str]:
    doc = fitz.open(stream=b, filetype="pdf")
    pages = []
    for p in doc:
        t = p.get_text("text") or ""
        t = _clean_text(t)
        if not t:
            blocks = p.get_text("blocks") or []
            parts = []
            for blk in blocks:
                if len(blk) >= 5 and isinstance(blk[4], str):
                    s = _clean_text(blk[4])
                    if s:
                        parts.append(s)
            t = "\n".join(parts).strip()
        pages.append(nfc(t))
    doc.close()
    return [p for p in pages if p and p.strip()]

_TOKEN_RE = re.compile(r"(<w:t[^>]*>.*?</w:t>|</w:p>|<w:br[^>]*/>|<w:cr[^>]*/>|<w:tab[^>]*/>)", re.DOTALL)

def _docx_xml_to_text(xml: str) -> str:
    xml = xml.replace("</w:p>", "</w:p>\n")
    out = []
    for m in _TOKEN_RE.finditer(xml):
        tok = m.group(1)
        if tok.startswith("<w:t"):
            inner = re.sub(r"^<w:t[^>]*>|</w:t>$", "", tok, flags=re.DOTALL)
            inner = html.unescape(inner)
            if inner:
                out.append(inner)
        elif tok.startswith("<w:tab"):
            out.append("\t")
        else:
            out.append("\n")
    text = "".join(out)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return _clean_text(text)

def _load_docx_pages(b: bytes, page_char_limit: int = 6000) -> list[str]:
    z = zipfile.ZipFile(io.BytesIO(b))
    names = set(z.namelist())
    ordered = []
    if "word/document.xml" in names:
        ordered.append("word/document.xml")
    parts = []
    for name in ordered:
        try:
            xml = z.read(name).decode("utf-8", errors="ignore")
        except Exception:
            continue
        t = _docx_xml_to_text(xml)
        if t:
            parts.append(t)
    z.close()
    full = "\n\n".join(parts).strip()
    if not full:
        return []
    return _chunk_as_pages(full, page_char_limit)

def _load_txt_pages(b: bytes, page_char_limit: int = 8000) -> list[str]:
    try:
        txt = b.decode("utf-8-sig")
    except:
        txt = b.decode("utf-8", errors="ignore")
    return _chunk_as_pages(txt, page_char_limit)

def load_bytes(filename: str, b: bytes) -> tuple[list[str], str]:
    ext = _ext_from_name(filename)
    if ext == "pdf":
        return _load_pdf_pages(b), "pdf"
    if ext == "docx":
        return _load_docx_pages(b), "docx"
    if ext == "txt":
        return _load_txt_pages(b), "txt"
    return [], ext

def _tolist(vecs: Any) -> list[list[float]]:
    if hasattr(vecs, "tolist"):
        return vecs.tolist()
    return vecs

class IngestPipeline:
    def __init__(self, sql_path: str, qdrant_path: str | None, embedder: E5Embedder):
        self.sql = SqlStore(sql_path)
        self.vdb = VectorStore(qdrant_path)
        self.embedder = embedder

    def ingest(self, filename: str, b: bytes, progress: Callable[[str], None] | None = None) -> IngestResult:
        t0 = time.time()
        t = time.perf_counter()

        if progress:
            try:
                faulthandler.dump_traceback_later(45, repeat=True)
            except Exception:
                pass
            try:
                tracemalloc.start()
            except Exception:
                pass

        stage_ms: dict[str, int] = {}
        stage_mem: dict[str, dict[str, int]] = {}

        def mark(name: str):
            nonlocal t
            now = time.perf_counter()
            stage_ms[name] = int((now - t) * 1000)
            t = now
            if progress:
                try:
                    cur, peak = tracemalloc.get_traced_memory()
                    stage_mem[name] = {"cur_kb": int(cur / 1024), "peak_kb": int(peak / 1024)}
                    progress(f"{name} | {stage_ms[name]}ms | mem_cur={stage_mem[name]['cur_kb']}KB peak={stage_mem[name]['peak_kb']}KB")
                except Exception:
                    progress(f"{name} | {stage_ms[name]}ms")

        pages, ftype = load_bytes(filename, b)
        pages = [p for p in pages if p and p.strip()]
        mark("load_bytes")

        if not pages:
            raise ValueError("empty_document")

        full_text = "\n\n".join(pages).strip()
        if not full_text:
            raise ValueError("empty_document")
        mark("build_full_text")

        doc_id = _sha256(b)

        try:
            self.vdb.delete_by_doc(doc_id)
        except Exception:
            pass
        try:
            self.sql.delete_document(doc_id)
        except Exception:
            pass
        mark("cleanup_previous")

        metrics = analyze_structure(full_text, pages)
        strategy = metrics["strategy"]
        mark("analyze_structure")

        chunks = chunk_dynamic(doc_id, pages, metrics) if strategy == "dynamic" else chunk_fixed(doc_id, pages, metrics)
        if not chunks:
            raise ValueError("no_chunks_generated")
        mark("chunking")

        metrics["text_chars"] = len(full_text)
        metrics["n_chunks"] = len(chunks)
        metrics["stage_ms"] = dict(stage_ms)
        if stage_mem:
            metrics["stage_mem_kb"] = dict(stage_mem)

        self.sql.upsert_document({
            "doc_id": doc_id,
            "filename": filename,
            "file_type": ftype,
            "strategy": strategy,
            "metrics": metrics,
            "n_pages": len(pages),
            "n_chunks": len(chunks),
        })
        self.sql.upsert_chunks(chunks)
        mark("sql_upsert")

        dim = int(self.embedder.dim())
        self.vdb.ensure(dim)
        mark("vdb_ensure")

        if ftype == "docx":
            bs = 8
            max_chars_per_passage = 1800
        else:
            bs = 32
            max_chars_per_passage = 2400

        for i in range(0, len(chunks), bs):
            batch = chunks[i:i+bs]
            passages = [(c["text_raw"] or "")[:max_chars_per_passage] for c in batch]
            vecs = _tolist(self.embedder.embed_passages(passages))
            chunk_ids = [c["chunk_id"] for c in batch]
            point_ids = [str(uuid.uuid5(uuid.NAMESPACE_DNS, cid)) for cid in chunk_ids]
            payloads = [{
                "chunk_id": c["chunk_id"],
                "doc_id": c["doc_id"],
                "chunk_index": c["chunk_index"],
                "page_start": c["page_start"],
                "page_end": c["page_end"],
                "section_path": c["section_path"],
                "ar": c["lang"]["ar_ratio"],
                "dia": c["lang"]["dia_ratio"]
            } for c in batch]
            self.vdb.upsert(point_ids, vecs, payloads)

            if progress and (i == 0 or (i // bs) % 10 == 0):
                progress(f"embed+upsert progress: {min(i+bs, len(chunks))}/{len(chunks)}")

        mark("embed_upsert_all")

        elapsed_ms = int((time.time() - t0) * 1000)

        if progress:
            try:
                faulthandler.cancel_dump_traceback_later()
            except Exception:
                pass
            try:
                tracemalloc.stop()
            except Exception:
                pass

        return IngestResult(
            doc_id=doc_id,
            filename=filename,
            file_type=ftype,
            strategy=strategy,
            metrics=metrics,
            n_pages=len(pages),
            n_chunks=len(chunks),
            elapsed_ms=elapsed_ms
        )
