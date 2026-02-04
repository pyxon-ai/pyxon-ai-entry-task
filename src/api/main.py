"""FastAPI application for Pyxon AI Document Parser."""

from typing import Optional, List
import os
import tempfile
import logging
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, status
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from src.config.settings import settings
from src.database.connection import db_manager
from src.database.repository import DocumentRepository, ChunkRepository
from src.processor.document_processor import DocumentProcessor
from src.rag.pipeline import RAGPipeline
from sqlalchemy import text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


app = FastAPI(
    title="Pyxon AI Document Parser",
    description="AI-powered document parser with full Arabic support",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Security: Rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Security: CORS - Allow all by default for demo/testing; override via env
allowed_origins = ["*"]

# Allow environment override
if os.getenv("ALLOWED_ORIGINS"):
    allowed_origins = os.getenv("ALLOWED_ORIGINS").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Content-Range", "X-Total-Count"],
    max_age=600,
)

# Security: GZip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Serve demo UI
DEMO_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "demo")
if os.path.isdir(DEMO_DIR):
    app.mount("/demo", StaticFiles(directory=DEMO_DIR, html=True), name="demo")


@app.middleware("http")
async def ensure_cors_header(request: Request, call_next):
    response = await call_next(request)
    if "access-control-allow-origin" not in response.headers:
        response.headers["access-control-allow-origin"] = "*"
    return response


@app.on_event("startup")
def on_startup():
    logger.info("Starting Pyxon AI Document Parser...")
    db_manager.init_db()
    logger.info("Database initialized successfully")


# Security: Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "Internal server error",
            "detail": str(exc) if settings.demo_host == "0.0.0.0" else "An error occurred"
        }
    )


# Security: Health check endpoint
@app.get("/api/health")
@limiter.limit("100/minute")
def health_check(request: Request):
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "database": "connected" if db_manager.engine else "disconnected"
    }


def get_session():
    return db_manager.get_session()


# API Endpoints
@app.post("/api/documents/upload")
@limiter.limit("10/minute")
def upload_document(
    request: Request,
    file: UploadFile = File(...),
    chunking_strategy: Optional[str] = Form(None),
):
    """Upload and process a document."""
    session = get_session()
    try:
        # Security: Validate filename first
        original_filename = file.filename or ""
        if not original_filename or len(original_filename) > 255:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid filename"
            )

        # Security: Validate file type
        allowed_extensions = {'.pdf', '.docx', '.doc', '.txt'}
        file_ext = Path(original_filename).suffix.lower()

        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Unsupported file type. Allowed types: {', '.join(allowed_extensions)}"
            )

        # Security: Validate file size
        file.file.seek(0, os.SEEK_END)
        file_size = file.file.tell()
        file.file.seek(0)
        
        if file_size > settings.max_file_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size is {settings.max_file_size / 1024 / 1024}MB"
            )
        
        logger.info(f"Processing file upload: {filename} ({file_size} bytes)")
        
        processor = DocumentProcessor(session)

        suffix = os.path.splitext(file.filename or "")[1].lower() or ".txt"
        # Save to a temporary file so Docling can read it
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            contents = file.file.read()
            tmp.write(contents)
            tmp_path = tmp.name

        result = processor.process_file(tmp_path, chunking_strategy=chunking_strategy)

        # Clean up
        try:
            os.remove(tmp_path)
        except Exception:
            pass

        if result.success and result.document:
            logger.info(f"Successfully processed document: {result.document.id}")
            return {
                "success": True,
                "document_id": result.document.id,
                "chunks_created": result.chunks_created,
                "processing_time": result.processing_time,
            }
        else:
            logger.error(f"Failed to process document: {result.error}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.error or "Processing failed"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing document: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process document"
        )
    finally:
        session.close()


@app.get("/api/documents")
@limiter.limit("30/minute")
def list_documents(request: Request):
    """List all documents."""
    session = get_session()
    try:
        doc_repo = DocumentRepository(session)
        chunk_repo = ChunkRepository(session)
        docs = doc_repo.get_all_documents()
        out = []
        for d in docs:
            out.append({
                "id": d.id,
                "filename": d.filename,
                "file_type": d.file_type,
                "chunking_strategy": d.chunking_strategy,
                "has_arabic": bool(d.has_arabic),
                "has_diacritics": bool(d.has_diacritics),
                "chunk_count": chunk_repo.count_chunks(document_id=d.id),
            })
        return out
    except Exception as e:
        logger.error(f"Error listing documents: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list documents"
        )
    finally:
        session.close()


@app.delete("/api/documents/{document_id}")
@limiter.limit("20/minute")
def delete_document(request: Request, document_id: str):
    """Delete a document."""
    session = get_session()
    try:
        # Security: Validate document ID format
        if not document_id or len(document_id) < 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid document ID"
            )
        
        doc_repo = DocumentRepository(session)
        ok = doc_repo.delete_document(document_id)
        
        if not ok:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        logger.info(f"Deleted document: {document_id}")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document"
        )
    finally:
        session.close()


class QueryRequest(BaseModel):
    question: str
    top_k: int = 5
    document_id: Optional[str] = None
    model: Optional[str] = None


@app.post("/api/query")
@limiter.limit("20/minute")
def query(request: Request, body: QueryRequest):
    """Query documents."""
    session = get_session()
    try:
        # Security: Validate inputs
        if not body.question or len(body.question.strip()) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Question cannot be empty"
            )
        
        if len(body.question) > 1000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Question too long (max 1000 characters)"
            )
        
        if not isinstance(body.top_k, int) or body.top_k < 1 or body.top_k > 20:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="top_k must be between 1 and 20"
            )
        
        logger.info(f"Processing query: {body.question[:50]}...")
        
        rag = RAGPipeline(session)
        result = rag.query(
            question=body.question,
            top_k=body.top_k,
            document_id=body.document_id,
            model=body.model,
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing query: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process query"
        )
    finally:
        session.close()


@app.get("/api/benchmarks")
@limiter.limit("5/minute")
def run_benchmarks(request: Request):
    """Run benchmark tests."""
    session = get_session()
    try:
        logger.info("Running benchmark suite...")
        from src.benchmarks.suite import BenchmarkSuite
        suite = BenchmarkSuite(session)
        results = suite.run_all_benchmarks()
        report_md = suite.generate_report()

        passed = sum(1 for r in results if r.passed)
        total = len(results)
        average = sum(r.score for r in results) / total if total else 0.0

        logger.info(f"Benchmarks completed: {passed}/{total} passed")
        
        return {
            "total_tests": total,
            "passed": passed,
            "average_score": average,
            "results": [
                {
                    "test_name": r.test_name,
                    "passed": r.passed,
                    "score": r.score,
                    "execution_time": r.execution_time,
                }
                for r in results
            ],
            "report": report_md,
        }
    except Exception as e:
        logger.error(f"Error running benchmarks: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to run benchmarks"
        )
    finally:
        session.close()


@app.get("/api/stats")
@limiter.limit("30/minute")
def stats(request: Request):
    """Get system statistics."""
    session = get_session()
    try:
        # Totals
        total_documents = session.execute(text("SELECT COUNT(*) FROM documents")).scalar() or 0
        total_chunks = session.execute(text("SELECT COUNT(*) FROM chunks")).scalar() or 0
        arabic_documents = session.execute(text("SELECT COUNT(*) FROM documents WHERE has_arabic = TRUE")).scalar() or 0
        return {
            "total_documents": total_documents,
            "total_chunks": total_chunks,
            "arabic_documents": arabic_documents,
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get statistics"
        )
    finally:
        session.close()
