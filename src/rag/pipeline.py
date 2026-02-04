"""RAG pipeline combining retrieval and generation."""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from src.rag.retriever import Retriever
from src.rag.generator import get_answer_generator
from src.database.repository import DocumentRepository, ChunkRepository


class RAGPipeline:
    """Complete RAG pipeline for question answering."""

    def __init__(self, session: Session):
        self.session = session
        self.retriever = Retriever(session, use_hybrid=True)
        self.answer_generator = get_answer_generator()
        self.document_repo = DocumentRepository(session)
        self.chunk_repo = ChunkRepository(session)

    def query(
        self,
        question: str,
        top_k: int = 5,
        document_id: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process a question through the RAG pipeline.
        
        Args:
            question: User question
            top_k: Number of chunks to retrieve
            document_id: Optional document ID to search within
            model: LLM model to use
        
        Returns:
            Dictionary with answer and retrieved context
        """
        # Retrieve relevant chunks
        chunks = self.retriever.retrieve(
            query=question,
            top_k=top_k,
            document_id=document_id,
        )
        
        if not chunks:
            return {
                "answer": "No relevant information found.",
                "context": [],
                "sources": [],
            }
        
        # Extract context
        context = [chunk.content for chunk in chunks]
        sources = [
            {
                "chunk_id": chunk.id,
                "document_id": chunk.document_id,
                "content": chunk.content[:200] + "...",
            }
            for chunk in chunks
        ]
        
        # Generate answer
        answer = self.answer_generator.generate_answer(
            query=question,
            context=context,
            model=model,
        )
        
        return {
            "answer": answer,
            "context": context,
            "sources": sources,
        }

    def query_arabic(
        self,
        question: str,
        top_k: int = 5,
        document_id: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process an Arabic question through the RAG pipeline.
        
        Args:
            question: Arabic question
            top_k: Number of chunks to retrieve
            document_id: Optional document ID to search within
            model: LLM model to use
        
        Returns:
            Dictionary with Arabic answer and retrieved context
        """
        # Retrieve relevant chunks
        chunks = self.retriever.retrieve(
            query=question,
            top_k=top_k,
            document_id=document_id,
            filters={"has_arabic": True},
        )
        
        if not chunks:
            return {
                "answer": "لم يتم العثور على معلومات ذات صلة.",
                "context": [],
                "sources": [],
            }
        
        # Extract context
        context = [chunk.content for chunk in chunks]
        sources = [
            {
                "chunk_id": chunk.id,
                "document_id": chunk.document_id,
                "content": chunk.content[:200] + "...",
            }
            for chunk in chunks
        ]
        
        # Generate answer in Arabic
        answer = self.answer_generator.generate_arabic_answer(
            query=question,
            context=context,
            model=model,
        )
        
        return {
            "answer": answer,
            "context": context,
            "sources": sources,
        }

    def get_document_stats(self) -> Dict[str, Any]:
        """Get statistics about indexed documents."""
        total_documents = self.document_repo.count_documents()
        total_chunks = self.chunk_repo.count_chunks()
        
        return {
            "total_documents": total_documents,
            "total_chunks": total_chunks,
        }
