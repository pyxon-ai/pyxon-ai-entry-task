"""Retrieval system for RAG."""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, text
import numpy as np
import re

from src.database.models import ChunkModel
from src.embeddings.generator import get_embedding_generator
from src.utils.text_utils import remove_diacritics


class VectorRetriever:
    """Vector-based retrieval using pgvector."""

    def __init__(self, session: Session):
        self.session = session
        self.embedding_generator = get_embedding_generator()
        self.embedding_dim = self.embedding_generator.get_embedding_dimension()

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        document_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[ChunkModel]:
        """
        Retrieve relevant chunks using vector similarity search.
        
        Args:
            query: Query text
            top_k: Number of results to return
            document_id: Optional document ID to filter by
            filters: Optional filters (e.g., chunk_type, has_arabic)
        
        Returns:
            List of relevant chunks
        """
        # Generate query embedding
        query_embedding = self.embedding_generator.embed_text(query)
        
        # Build SQL query with vector similarity
        sql = f"""
        SELECT 
            c.*,
            c.embedding <=> :embedding as distance
        FROM chunks c
        WHERE c.embedding IS NOT NULL
        """
        
        params = {"embedding": query_embedding}
        
        # Add document filter
        if document_id:
            sql += " AND c.document_id = :document_id"
            params["document_id"] = document_id
        
        # Add additional filters
        if filters:
            if "chunk_type" in filters:
                sql += " AND c.chunk_type = :chunk_type"
                params["chunk_type"] = filters["chunk_type"]
            if "has_arabic" in filters:
                sql += " AND c.has_arabic = :has_arabic"
                params["has_arabic"] = filters["has_arabic"]
        
        # Order by distance and limit
        sql += f" ORDER BY distance LIMIT {top_k}"
        
        # Execute query with safe fallback if pgvector isn't available
        try:
            result = self.session.execute(text(sql), params)
            rows = result.fetchall()
        except Exception as e:
            # Likely pgvector or operator not available (e.g., embedding column not vector type)
            # Return empty list so caller can fall back to keyword search/hybrid.
            return []
        
        # Convert to ChunkModel objects
        chunks = []
        for row in rows:
            chunk = ChunkModel(
                id=row.id,
                document_id=row.document_id,
                content=row.content,
                chunk_index=row.chunk_index,
                page_number=row.page_number,
                chunk_type=row.chunk_type,
                heading=row.heading,
                token_count=row.token_count,
                char_count=row.char_count,
                has_arabic=row.has_arabic,
                has_diacritics=row.has_diacritics,
                embedding=row.embedding,
                created_at=row.created_at,
            )
            chunks.append(chunk)
        
        return chunks

    def hybrid_retrieve(
        self,
        query: str,
        top_k: int = 5,
        document_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        keyword_weight: float = 0.3,
        vector_weight: float = 0.7,
    ) -> List[ChunkModel]:
        """
        Hybrid retrieval combining keyword and vector search.
        
        Args:
            query: Query text
            top_k: Number of results to return
            document_id: Optional document ID to filter by
            filters: Optional filters
            keyword_weight: Weight for keyword search (0-1)
            vector_weight: Weight for vector search (0-1)
        
        Returns:
            List of relevant chunks
        """
        # Vector search
        vector_results = self.retrieve(
            query=query,
            top_k=top_k * 2,
            document_id=document_id,
            filters=filters,
        )
        
        # Keyword search (simple text matching)
        keyword_results = self._keyword_search(
            query=query,
            top_k=top_k * 2,
            document_id=document_id,
            filters=filters,
        )
        
        # Combine and re-rank
        combined = self._combine_results(
            vector_results=vector_results,
            keyword_results=keyword_results,
            vector_weight=vector_weight,
            keyword_weight=keyword_weight,
        )
        
        return combined[:top_k]

    def _keyword_search(
        self,
        query: str,
        top_k: int,
        document_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[ChunkModel]:
        """Simple keyword-based search."""
        # Extract keywords from query
        keywords = [k for k in query.lower().split() if k]

        # Fetch candidates and score in Python (diacritic-insensitive, dialect-agnostic)
        q = self.session.query(ChunkModel)
        if document_id:
            q = q.filter(ChunkModel.document_id == document_id)
        if filters:
            if "chunk_type" in filters:
                q = q.filter(ChunkModel.chunk_type == filters["chunk_type"])
            if "has_arabic" in filters:
                q = q.filter(ChunkModel.has_arabic == filters["has_arabic"])
        candidates: List[ChunkModel] = q.all()

        def score_chunk(c: ChunkModel) -> int:
            raw = (c.content or "")
            norm = remove_diacritics(raw)
            norm = re.sub(r"[^\w\s]", " ", norm, flags=re.UNICODE)
            norm = norm.lower()
            nk = [re.sub(r"[^\w\s]", " ", remove_diacritics(k)).lower() for k in keywords]
            return sum(norm.count(k) for k in nk if k)

        ranked = sorted(candidates, key=score_chunk, reverse=True)
        return ranked[:top_k]

        # (Unreachable legacy SQL path removed for portability)

    def _combine_results(
        self,
        vector_results: List[ChunkModel],
        keyword_results: List[ChunkModel],
        vector_weight: float,
        keyword_weight: float,
    ) -> List[ChunkModel]:
        """Combine vector and keyword search results."""
        scores = {}
        
        # Score vector results
        for i, chunk in enumerate(vector_results):
            score = (len(vector_results) - i) / len(vector_results)  # Higher rank = higher score
            scores[chunk.id] = scores.get(chunk.id, 0) + score * vector_weight
        
        # Score keyword results
        for i, chunk in enumerate(keyword_results):
            score = (len(keyword_results) - i) / len(keyword_results)
            scores[chunk.id] = scores.get(chunk.id, 0) + score * keyword_weight
        
        # Combine and sort
        all_chunks = {c.id: c for c in vector_results + keyword_results}
        sorted_chunks = sorted(
            all_chunks.values(),
            key=lambda c: scores.get(c.id, 0),
            reverse=True,
        )
        
        return sorted_chunks


class Retriever:
    """Main retriever interface."""

    def __init__(self, session: Session, use_hybrid: bool = True):
        self.session = session
        self.vector_retriever = VectorRetriever(session)
        self.use_hybrid = use_hybrid

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        document_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[ChunkModel]:
        """Retrieve relevant chunks."""
        if self.use_hybrid:
            return self.vector_retriever.hybrid_retrieve(
                query=query,
                top_k=top_k,
                document_id=document_id,
                filters=filters,
            )
        else:
            return self.vector_retriever.retrieve(
                query=query,
                top_k=top_k,
                document_id=document_id,
                filters=filters,
            )
