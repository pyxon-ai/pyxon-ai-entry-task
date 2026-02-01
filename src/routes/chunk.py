from fastapi import APIRouter, Depends, UploadFile, File, status
from fastapi.responses import JSONResponse
from helpers.config import get_settings, Settings
from controllers.DataController import DataController
from controllers.DynamicController import DynamicController
from models import ResponseSignal
import logging

logger = logging.getLogger('uvicorn.error')

chunk_router = APIRouter(
    prefix="/api/v1",
    tags=["api_v1", "chunk"],
)

DEFAULT_CHUNK_SIZE = 500
DEFAULT_OVERLAP_SIZE = 25


@chunk_router.post("/chunk")
async def chunk_document(
    file: UploadFile = File(...),
    app_settings: Settings = Depends(get_settings)
):
    """
    Process a document and return chunks using dynamic chunking strategy.
    
    The system automatically determines the best chunking strategy (FIXED or SEMANTIC)
    based on the document content using AI analysis.
    
    Args:
        file: The document file to process (PDF, DOCX, or TXT)
    
    Returns:
        JSON response with chunking strategy, total chunks, and chunk data
    """
    data_controller = DataController()
    is_valid, result_signal = data_controller.validate_uploaded_file(file=file)

    if not is_valid:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"signal": result_signal}
        )

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
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"signal": ResponseSignal.PROCESSING_FAILED.value}
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
            "strategy": strategy,
            "total_chunks": len(formatted_chunks),
            "chunks": formatted_chunks
        }
        
    except Exception as e:
        logger.error(f"Error processing document: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "signal": ResponseSignal.PROCESSING_FAILED.value,
                "error": str(e)
            }
        )
