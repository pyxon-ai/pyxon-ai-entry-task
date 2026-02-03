from fastapi import APIRouter, Depends, status, Query
from fastapi.responses import JSONResponse
from helpers.config import get_settings, Settings
from services.weaviate_client import weaviate_client
from services.supabase_client import supabase_client
import cohere
import logging
from typing import Optional

logger = logging.getLogger('uvicorn.error')

search_router = APIRouter(
    prefix="/api/v1/search",
    tags=["api_v1", "search"],
)


@search_router.get("/semantic")
async def semantic_search(
    query: str = Query(..., description="Search query text"),
    limit: int = Query(10, ge=1, le=50, description="Number of results"),
    app_settings: Settings = Depends(get_settings)
):
    try:
        cohere_client = cohere.Client(app_settings.COHERE_API_KEY)
        
        embedding_response = cohere_client.embed(
            texts=[query],
            model='embed-multilingual-v3.0',
            input_type='search_query',
            embedding_types=['float']
        )
        query_vector = embedding_response.embeddings.float[0]
        
        initial_results = weaviate_client.semantic_search(
            query_vector=query_vector,
            limit=limit * 2
        )
        
        if not initial_results:
            return {
                "query": query,
                "total_results": 0,
                "results": []
            }
        
        documents = [r["content"] for r in initial_results]
        
        rerank_response = cohere_client.rerank(
            query=query,
            documents=documents,
            model='rerank-multilingual-v3.0',
            top_n=limit
        )
        
        reranked_results = []
        for result in rerank_response.results:
            original = initial_results[result.index]
            reranked_results.append({
                **original,
                "relevance_score": result.relevance_score
            })
        
        return {
            "query": query,
            "total_results": len(reranked_results),
            "results": reranked_results
        }
        
    except Exception as e:
        logger.error(f"Semantic search error: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": str(e)}
        )


@search_router.get("/sql")
async def sql_search(
    content: Optional[str] = Query(None, description="Search in chunk content"),
    file_name: Optional[str] = Query(None, description="Filter by document file name"),
    strategy: Optional[str] = Query(None, description="Filter by chunking strategy (FIXED/SEMANTIC)"),
    document_id: Optional[int] = Query(None, description="Filter by document ID"),
    from_date: Optional[str] = Query(None, description="Filter from date (ISO format: 2024-01-01)"),
    to_date: Optional[str] = Query(None, description="Filter to date (ISO format: 2024-12-31)"),
    limit: int = Query(50, ge=1, le=200, description="Number of results"),
    app_settings: Settings = Depends(get_settings)
):
    try:
        if not any([content, file_name, strategy, document_id, from_date, to_date]):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": "At least one filter parameter must be provided"}
            )
        
        results = supabase_client.advanced_search(
            content=content,
            file_name=file_name,
            strategy=strategy,
            document_id=document_id,
            from_date=from_date,
            to_date=to_date,
            limit=limit
        )
        
        return {
            "filters": {
                "content": content,
                "file_name": file_name,
                "strategy": strategy,
                "document_id": document_id,
                "from_date": from_date,
                "to_date": to_date
            },
            "total_results": len(results),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"SQL search error: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": str(e)}
        )


@search_router.get("/documents")
async def list_documents(
    limit: int = Query(50, ge=1, le=100, description="Number of documents"),
    app_settings: Settings = Depends(get_settings)
):
    try:
        results = supabase_client.get_all_documents(limit)
        
        return {
            "total_results": len(results),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": str(e)}
        )
