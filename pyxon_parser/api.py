"""REST API over the parser, so a RAG product can call it without the demo UI.

    uvicorn pyxon_parser.api:app --port 8000        # API only (interactive docs at /docs)
    python app.py                                    # demo UI at / and the same API at /api

Endpoints (JSON):

    GET    /api/health                  embedder, LLM, OCR, counts
    GET    /api/documents               list documents
    GET    /api/documents/{id}          one document with its sections and key concepts
    POST   /api/documents               upload a file (multipart: file, strategy=auto|fixed|dynamic)
    DELETE /api/documents/{id}          delete a document from both stores
    POST   /api/search                  {"query", "k", "mode", "include_summaries", "doc_ids"}
    POST   /api/ask                     {"question", "k", "doc_ids"}  -> answer + cited passages
    POST   /api/sql                     {"sql", "limit"}              -> read-only SELECT

Set PYXON_API_KEY to require an ``X-API-Key`` header on the endpoints that change data
(upload, delete). Reads stay open, as in the demo.
"""
from __future__ import annotations

import os
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from pydantic import BaseModel, Field

from .loaders import SUPPORTED_EXTENSIONS, DocumentLoadError, EmptyDocumentError, UnsupportedFileType, ocr_available
from .pipeline import PyxonParser

MAX_UPLOAD_MB = float(os.getenv("PYXON_MAX_UPLOAD_MB", "20"))


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, examples=["ما هي علامات الجفاف؟"])
    k: int = Field(5, ge=1, le=50)
    mode: Literal["hybrid", "vector", "keyword", "graph"] = "hybrid"
    include_summaries: bool = False
    doc_ids: list[int] | None = None


class AskRequest(BaseModel):
    question: str = Field(min_length=1, examples=["Which forklift failed inspection?"])
    k: int = Field(5, ge=1, le=20)
    doc_ids: list[int] | None = None


class SQLRequest(BaseModel):
    sql: str = Field(min_length=1, examples=["SELECT filename, language, strategy FROM documents"])
    limit: int = Field(200, ge=1, le=1000)


def _result(r) -> dict:
    return {"chunk_id": r.chunk_id, "document_id": r.document_id, "filename": r.filename, "text": r.text,
            "section": r.section, "page": r.page, "level": r.level, "score": r.score,
            "retrievers": r.sources, "raw_scores": r.raw_scores, "also_in": r.also_in}


def build_router(parser: PyxonParser) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["pyxon"])

    def require_key(x_api_key: str | None = Header(default=None)):
        expected = os.getenv("PYXON_API_KEY")
        if expected and x_api_key != expected:
            raise HTTPException(401, "Missing or wrong X-API-Key header.")

    @router.get("/health")
    def health():
        llm = parser.rag.llm
        return {"status": "ok", "embedder": parser.embedder.name, "embedding_dim": int(parser.embedder.dim),
                "llm": llm.model if llm else None, "ocr": ocr_available(),
                "documents": len(parser.sql.list_documents()), "chunks": parser.sql.chunk_count(),
                "supported_extensions": sorted(SUPPORTED_EXTENSIONS)}

    @router.get("/documents")
    def list_documents():
        return parser.sql.list_documents()

    @router.get("/documents/{doc_id}")
    def get_document(doc_id: int):
        doc = parser.sql.get_document(doc_id)
        if doc is None:
            raise HTTPException(404, f"No document with id {doc_id}.")
        sections = parser.sql.run_readonly_query(
            "SELECT title, level, position FROM sections WHERE document_id = ? ORDER BY position", params=[doc_id])
        return {**doc, "sections": sections, "key_concepts": [t["term"] for t in parser.sql.top_terms(doc_id, 10)],
                "chunks": len(parser.sql.document_chunks(doc_id))}

    @router.post("/documents", status_code=201, dependencies=[Depends(require_key)])
    async def upload(file: UploadFile = File(...), strategy: Literal["auto", "fixed", "dynamic"] = Form("auto")):
        name = Path(file.filename or "upload").name
        if Path(name).suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise HTTPException(415, f"Unsupported file type {Path(name).suffix or '(none)'}; "
                                     f"supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}.")
        data = await file.read()
        if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
            raise HTTPException(413, f"File is larger than {MAX_UPLOAD_MB:g} MB.")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / name
            path.write_bytes(data)
            try:
                r = parser.ingest(path, strategy=strategy)
            except (UnsupportedFileType, EmptyDocumentError, DocumentLoadError) as exc:
                raise HTTPException(422, str(exc)) from exc
        a = r.analysis
        return {"document_id": r.document_id, "filename": r.filename, "duplicate": r.duplicate,
                "language": a.language, "direction": a.direction, "has_diacritics": a.has_diacritics,
                "doc_type": a.doc_type, "strategy": a.strategy, "strategy_score": a.strategy_score,
                "reasons": a.reasons, "summary": a.summary, "keywords": a.keywords,
                "chunks": len(r.chunks), "raptor_nodes": len(r.summaries), "timings": r.timings}

    @router.delete("/documents/{doc_id}", dependencies=[Depends(require_key)])
    def delete(doc_id: int):
        doc = parser.sql.get_document(doc_id)
        if doc is None:
            raise HTTPException(404, f"No document with id {doc_id}.")
        parser.delete(doc_id)
        return {"deleted": doc_id, "filename": doc["filename"]}

    @router.post("/search")
    def search(req: SearchRequest):
        res = parser.search(req.query, k=req.k, mode=req.mode,
                            include_summaries=req.include_summaries, doc_ids=req.doc_ids)
        return {"query": req.query, "results": [_result(r) for r in res]}

    @router.post("/ask")
    def ask(req: AskRequest):
        ans = parser.ask(req.question, k=req.k, doc_ids=req.doc_ids)
        out = asdict(ans)
        out["contexts"] = [_result(c) for c in ans.contexts]
        return out

    @router.post("/sql")
    def sql(req: SQLRequest):
        try:
            return {"rows": parser.sql.run_readonly_query(req.sql, limit=req.limit)}
        except Exception as exc:
            raise HTTPException(400, str(exc)) from exc

    return router


def create_app(parser: PyxonParser | None = None) -> FastAPI:
    parser = parser or PyxonParser(data_dir=os.getenv("PYXON_DATA_DIR", "data"))
    app = FastAPI(title="Pyxon Document Parser API", version="1.0",
                  description="Parse PDF/DOCX/DOC/TXT (Arabic with harakat), chunk, index and query for RAG.")
    app.include_router(build_router(parser))
    app.state.parser = parser
    return app


def __getattr__(name: str):  # ``uvicorn pyxon_parser.api:app`` builds the app on first access
    if name == "app":
        globals()["app"] = create_app()
        return globals()["app"]
    raise AttributeError(name)
