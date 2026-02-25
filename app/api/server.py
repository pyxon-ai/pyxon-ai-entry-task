from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
import shutil
import os
import uuid
from app.main import DocumentProcessor

app = FastAPI(
    title="Arabic AI Document Parser API",
    description="A high-performance API for parsing, chunking, and searching Arabic documents with diacritics support.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)
processor = DocumentProcessor()

# Ensure uploads directory exists
UPLOAD_DIR = "data/uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

class QueryRequest(BaseModel):
    query: str
    top_k: int = 3

@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Upload and process a document (PDF, DOCX, TXT).
    """
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in [".pdf", ".docx", ".txt"]:
        raise HTTPException(status_code=400, detail="Unsupported file format. Use PDF, DOCX, or TXT.")

    # Validate MIME type (Basic check)
    allowed_mimes = ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "text/plain"]
    if file.content_type not in allowed_mimes:
        # Fallback for some browsers sending different types
        if not (file_ext == ".txt" and file.content_type.startswith("text/")):
             print(f"Warning: Mime type {file.content_type} does not strictly match expected but extension is valid. Proceeding with caution.")

    file_id = str(uuid.uuid4())
    save_path = os.path.join(UPLOAD_DIR, f"{file_id}{file_ext}")

    try:
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Run heavy processing in a separate thread
        doc_id, preview = await run_in_threadpool(processor.process_file, save_path)
        
        return {"message": "File processed successfully", "doc_id": doc_id, "filename": file.filename, "preview": preview}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    """
    Serve the main dashboard UI.
    """
    with open("app/api/templates/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/query")
async def semantic_search(request: QueryRequest):
    """
    Perform semantic search on processed documents.
    """
    try:
        results = processor.ask(request.query, n_results=request.top_k)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
