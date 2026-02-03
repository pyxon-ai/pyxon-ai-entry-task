from fastapi import APIRouter, Depends, UploadFile, File, status
from fastapi.responses import JSONResponse
from helpers.config import get_settings, Settings
from controllers.DataController import DataController
from controllers.DynamicController import DynamicController
from models import ResponseSignal
from typing import List
import logging

logger = logging.getLogger('uvicorn.error')

chunk_router = APIRouter(
    prefix="/api/v1",
    tags=["api_v1", "chunk"],
)

DEFAULT_CHUNK_SIZE = 500
DEFAULT_OVERLAP_SIZE = 25


async def process_single_file(file: UploadFile, data_controller: DataController):
    is_valid, result_signal = data_controller.validate_uploaded_file(file=file)
    
    if not is_valid:
        return {"error": result_signal, "file_name": file.filename}
    
    try:
        dynamic_controller = DynamicController()
        
        result = await dynamic_controller.process_document(
            file=file,
            chunk_size=DEFAULT_CHUNK_SIZE,
            overlap_size=DEFAULT_OVERLAP_SIZE
        )
        
        chunks = result["chunks"]
        strategy = result["strategy"]
        
        if chunks is None or len(chunks) == 0:
            return {"error": ResponseSignal.PROCESSING_FAILED.value, "file_name": file.filename}
        
        from services.storage_service import storage_service
        storage_result = await storage_service.store_document(
            file_name=file.filename,
            strategy=strategy,
            chunks=chunks
        )
        
        formatted_chunks = [
            {
                "id": idx,
                "content": chunk.page_content,
                "metadata": chunk.metadata
            }
            for idx, chunk in enumerate(chunks)
        ]
        
        return {
            "file_name": file.filename,
            "strategy": strategy,
            "total_chunks": len(formatted_chunks),
            "document_id": storage_result["document_id"],
            "storage_status": storage_result["status"],
            "chunks": formatted_chunks
        }
        
    except Exception as e:
        logger.error(f"Error processing {file.filename}: {e}")
        return {"error": str(e), "file_name": file.filename}


@chunk_router.post("/chunk")
async def chunk_documents(
    files: List[UploadFile] = File(..., description="Upload one or more files"),
    app_settings: Settings = Depends(get_settings)
):
    data_controller = DataController()
    results = []
    errors = []
    
    logger.info(f"Received {len(files)} file(s) for processing")
    
    for file in files:
        logger.info(f"Processing file: {file.filename}")
        result = await process_single_file(file, data_controller)
        
        if "error" in result:
            errors.append({
                "file_name": result.get("file_name"),
                "error": result["error"]
            })
        else:
            results.append(result)
    
    if len(files) == 1:
        if errors:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=errors[0]
            )
        return results[0]
    
    if len(results) == 0 and len(errors) > 0:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": "All files failed processing",
                "errors": errors
            }
        )
    
    return {
        "total_files": len(files),
        "successful": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors if errors else None
    }
