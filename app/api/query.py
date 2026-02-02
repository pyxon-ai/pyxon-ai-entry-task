"""
Query API Endpoints
Handles search and retrieval operations
"""

from fastapi import APIRouter, HTTPException
from loguru import logger

from app.models.schemas import QueryRequest, QueryResponse
from app.services import RAGService

router = APIRouter(prefix="/api/query", tags=["query"])

# Initialize RAG service
rag_service = RAGService()


@router.post("/", response_model=QueryResponse)
async def search_documents(request: QueryRequest):
    """
    Search documents using semantic similarity
    
    Supports:
    - Semantic search across all documents
    - Filtering by document_id
    - Filtering by language
    """
    try:
        # Build filters
        filters = {}
        if request.document_id:
            filters['document_id'] = request.document_id
        if request.language:
            filters['language'] = request.language
        
        # Perform search
        if filters:
            results = rag_service.hybrid_search(
                query=request.query,
                top_k=request.top_k,
                filters=filters
            )
        else:
            results = rag_service.semantic_search(
                query=request.query,
                top_k=request.top_k
            )
        
        return QueryResponse(**results)
    
    except Exception as e:
        logger.error(f"Error in search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/context")
async def get_context(query: str, top_k: int = 3):
    """
    Get context for a query (useful for LLM integration)
    
    Returns concatenated relevant chunks
    """
    try:
        context = rag_service.get_context_for_query(query, top_k)
        return {
            "query": query,
            "context": context,
            "chunks_used": top_k
        }
    except Exception as e:
        logger.error(f"Error getting context: {e}")
        raise HTTPException(status_code=500, detail=str(e))
