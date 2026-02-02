"""
RAG Service
Implements retrieval-augmented generation capabilities
"""

from typing import List, Dict, Any, Optional
import time
from loguru import logger

from app.services.storage_service import StorageService
from app.services.embedding_service import EmbeddingService


class RAGService:
    """RAG system for document querying and retrieval"""
    
    def __init__(self):
        self.storage = StorageService()
        self.embedding_service = EmbeddingService()
        logger.info("RAG service initialized")
    
    def semantic_search(
        self,
        query: str,
        top_k: int = 5,
        document_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Perform semantic search on documents
        
        Args:
            query: Search query
            top_k: Number of results to return
            document_id: Optional filter by document ID
            
        Returns:
            Search results with metadata
        """
        start_time = time.time()
        
        try:
            # Generate query embedding
            query_embedding = self.embedding_service.generate_embedding(query)
            
            # Search in vector database
            vector_results = self.storage.search_similar_chunks(
                query_embedding=query_embedding,
                top_k=top_k,
                document_id=document_id
            )
            
            # Get chunk details from SQL database
            chunk_ids = vector_results['ids'][0] if vector_results['ids'] else []
            
            if not chunk_ids:
                return {
                    'query': query,
                    'results': [],
                    'total_results': 0,
                    'processing_time': time.time() - start_time
                }
            
            chunks = self.storage.get_chunk_details(chunk_ids)
            
            # Build results
            results = []
            distances = vector_results['distances'][0] if vector_results['distances'] else []
            
            for i, chunk in enumerate(chunks):
                # Convert distance to similarity score (1 - normalized distance)
                similarity_score = 1.0 - (distances[i] if i < len(distances) else 1.0)
                
                # Get document info
                document = self.storage.get_document(chunk.document_id)
                
                result = {
                    'chunk_id': chunk.id,
                    'document_id': chunk.document_id,
                    'document_name': document.filename if document else 'Unknown',
                    'chunk_text': chunk.chunk_text,
                    'similarity_score': round(similarity_score, 4),
                    'chunk_index': chunk.chunk_index
                }
                results.append(result)
            
            processing_time = time.time() - start_time
            
            logger.info(f"Search completed in {processing_time:.2f}s, found {len(results)} results")
            
            return {
                'query': query,
                'results': results,
                'total_results': len(results),
                'processing_time': round(processing_time, 3)
            }
        
        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            raise
    
    def hybrid_search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Hybrid search combining vector similarity and metadata filtering
        
        Args:
            query: Search query
            top_k: Number of results
            filters: Metadata filters (language, document_id, etc.)
            
        Returns:
            Search results
        """
        # Extract document_id from filters if present
        document_id = filters.get('document_id') if filters else None
        
        # Perform semantic search
        results = self.semantic_search(query, top_k, document_id)
        
        # Apply additional filters if needed
        if filters and 'language' in filters:
            language_filter = filters['language']
            filtered_results = []
            
            for result in results['results']:
                doc = self.storage.get_document(result['document_id'])
                if doc and doc.language == language_filter:
                    filtered_results.append(result)
            
            results['results'] = filtered_results
            results['total_results'] = len(filtered_results)
        
        return results
    
    def get_context_for_query(
        self,
        query: str,
        top_k: int = 3
    ) -> str:
        """
        Get relevant context chunks for a query
        Useful for feeding to LLM
        
        Args:
            query: User query
            top_k: Number of context chunks
            
        Returns:
            Concatenated context string
        """
        results = self.semantic_search(query, top_k)
        
        context_parts = []
        for i, result in enumerate(results['results'], 1):
            context_parts.append(f"[Context {i}]")
            context_parts.append(result['chunk_text'])
            context_parts.append("")
        
        return "\n".join(context_parts)
