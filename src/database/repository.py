"""Database repository for document and chunk operations."""

from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select, func, text
from src.database.models import DocumentModel, ChunkModel
from src.models.document import Document, Chunk, DocumentMetadata, ChunkMetadata


class DocumentRepository:
    """Repository for document database operations."""

    def __init__(self, session: Session):
        self.session = session

    def create_document(self, document: Document) -> DocumentModel:
        """Create a new document in the database."""
        # Support both Enum and raw string for chunking_strategy
        cs_value = (
            document.chunking_strategy.value
            if hasattr(document.chunking_strategy, "value")
            else str(document.chunking_strategy)
        )

        # Upsert by ID to avoid duplicate key errors in tests
        existing = self.get_document(document.id)
        if existing:
            existing.filename = document.filename
            existing.file_type = getattr(document.file_type, "value", document.file_type)
            existing.content = document.content
            existing.title = document.metadata.title
            existing.author = document.metadata.author
            existing.subject = document.metadata.subject
            existing.keywords = document.metadata.keywords
            existing.created_date = document.metadata.created_date
            existing.modified_date = document.metadata.modified_date
            existing.page_count = document.metadata.page_count
            existing.word_count = document.metadata.word_count
            existing.language = document.metadata.language
            existing.has_arabic = document.metadata.has_arabic
            existing.has_diacritics = document.metadata.has_diacritics
            existing.chunking_strategy = cs_value
            existing.processed_at = document.processed_at
            self.session.commit()
            self.session.refresh(existing)
            return existing

        doc_model = DocumentModel(
            id=document.id,
            filename=document.filename,
            file_type=getattr(document.file_type, "value", document.file_type),
            content=document.content,
            title=document.metadata.title,
            author=document.metadata.author,
            subject=document.metadata.subject,
            keywords=document.metadata.keywords,
            created_date=document.metadata.created_date,
            modified_date=document.metadata.modified_date,
            page_count=document.metadata.page_count,
            word_count=document.metadata.word_count,
            language=document.metadata.language,
            has_arabic=document.metadata.has_arabic,
            has_diacritics=document.metadata.has_diacritics,
            chunking_strategy=cs_value,
            created_at=document.created_at,
            processed_at=document.processed_at,
        )
        self.session.add(doc_model)
        try:
            self.session.commit()
        except Exception:
            # Handle potential unique constraint errors due to prior inserts
            self.session.rollback()
            existing = self.get_document(document.id)
            if existing:
                existing.filename = document.filename
                existing.file_type = getattr(document.file_type, "value", document.file_type)
                existing.content = document.content
                existing.title = document.metadata.title
                existing.author = document.metadata.author
                existing.subject = document.metadata.subject
                existing.keywords = document.metadata.keywords
                existing.created_date = document.metadata.created_date
                existing.modified_date = document.metadata.modified_date
                existing.page_count = document.metadata.page_count
                existing.word_count = document.metadata.word_count
                existing.language = document.metadata.language
                existing.has_arabic = document.metadata.has_arabic
                existing.has_diacritics = document.metadata.has_diacritics
                existing.chunking_strategy = cs_value
                existing.processed_at = document.processed_at
                self.session.commit()
                self.session.refresh(existing)
                return existing
            else:
                # Re-raise if truly unexpected
                raise
        self.session.refresh(doc_model)
        return doc_model

    def get_document(self, document_id: str) -> Optional[DocumentModel]:
        """Get a document by ID."""
        return self.session.query(DocumentModel).filter(
            DocumentModel.id == document_id
        ).first()

    def get_all_documents(self, skip: int = 0, limit: int = 100) -> List[DocumentModel]:
        """Get all documents with pagination."""
        return self.session.query(DocumentModel).offset(skip).limit(limit).all()

    def update_document(self, document_id: str, **kwargs) -> Optional[DocumentModel]:
        """Update document fields."""
        doc = self.get_document(document_id)
        if doc:
            for key, value in kwargs.items():
                setattr(doc, key, value)
            doc.processed_at = datetime.utcnow()
            self.session.commit()
            self.session.refresh(doc)
        return doc

    def delete_document(self, document_id: str) -> bool:
        """Delete a document by ID."""
        doc = self.get_document(document_id)
        if doc:
            self.session.delete(doc)
            self.session.commit()
            return True
        return False

    def count_documents(self) -> int:
        """Count total documents."""
        return self.session.query(func.count(DocumentModel.id)).scalar()


class ChunkRepository:
    """Repository for chunk database operations."""

    def __init__(self, session: Session):
        self.session = session

    def create_chunks(self, chunks: List[Chunk]) -> List[ChunkModel]:
        """Create multiple chunks in the database."""
        chunk_models = []
        for chunk in chunks:
            chunk_model = ChunkModel(
                id=chunk.id,
                document_id=chunk.document_id,
                content=chunk.content,
                chunk_index=chunk.metadata.chunk_index,
                page_number=chunk.metadata.page_number,
                chunk_type=chunk.metadata.chunk_type,
                heading=chunk.metadata.heading,
                token_count=chunk.metadata.token_count,
                char_count=chunk.metadata.char_count,
                has_arabic=chunk.metadata.has_arabic,
                has_diacritics=chunk.metadata.has_diacritics,
                embedding=chunk.embedding,
            )
            chunk_models.append(chunk_model)
        
        self.session.add_all(chunk_models)
        self.session.commit()
        for cm in chunk_models:
            self.session.refresh(cm)
        return chunk_models

    def get_chunks_by_document(self, document_id: Optional[str]) -> List[ChunkModel]:
        """Get all chunks for a document. If document_id is None, return all chunks."""
        query = self.session.query(ChunkModel)
        if document_id is not None:
            query = query.filter(ChunkModel.document_id == document_id)
        return query.order_by(ChunkModel.chunk_index).all()

    def get_chunk(self, chunk_id: str) -> Optional[ChunkModel]:
        """Get a chunk by ID."""
        return self.session.query(ChunkModel).filter(
            ChunkModel.id == chunk_id
        ).first()

    def search_chunks(self, query_embedding: List[float], limit: int = 10) -> List[ChunkModel]:
        """
        Search chunks by vector similarity using pgvector.
        
        Args:
            query_embedding: Query embedding vector
            limit: Maximum number of results to return
        
        Returns:
            List of similar chunks
        """
        try:
            # Use pgvector cosine similarity search
            sql = """
            SELECT 
                c.*,
                1 - (c.embedding <=> :embedding) as similarity
            FROM chunks c
            WHERE c.embedding IS NOT NULL
            ORDER BY c.embedding <=> :embedding
            LIMIT :limit
            """
            
            result = self.session.execute(
                text(sql),
                {"embedding": query_embedding, "limit": limit}
            )
            rows = result.fetchall()
            
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
        except Exception as e:
            # Fallback to empty list if pgvector search fails
            import logging
            logging.warning(f"Vector search failed, returning empty results: {e}")
            return []

    def count_chunks(self, document_id: Optional[str] = None) -> int:
        """Count total chunks, optionally filtered by document."""
        query = self.session.query(func.count(ChunkModel.id))
        if document_id:
            query = query.filter(ChunkModel.document_id == document_id)
        return query.scalar()
