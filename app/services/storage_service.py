"""
Storage Service
Manages dual storage: PostgreSQL (metadata) + ChromaDB (vectors)
"""

from typing import List, Dict, Any, Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import chromadb
from chromadb.config import Settings
from loguru import logger
import uuid

from app.models.document import Base, Document, Chunk
from app.config import settings


class StorageService:
    """Dual storage management for SQL and Vector databases"""
    
    def __init__(self):
        # PostgreSQL setup
        self.engine = create_engine(settings.database_url)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # ChromaDB setup
        self.chroma_client = chromadb.PersistentClient(
            path=settings.chroma_persist_directory
        )
        
        # Create or get collection
        self.collection = self.chroma_client.get_or_create_collection(
            name="document_chunks",
            metadata={"description": "Document chunks with embeddings"}
        )
        
        logger.info("Storage service initialized successfully")
    
    def get_db_session(self) -> Session:
        """Get database session"""
        return self.SessionLocal()
    
    def store_document(
        self,
        filename: str,
        file_type: str,
        file_size: int,
        language: str,
        chunking_strategy: str,
        total_chunks: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Store document metadata in PostgreSQL
        
        Returns:
            Document ID
        """
        db = self.get_db_session()
        
        try:
            document = Document(
                id=str(uuid.uuid4()),
                filename=filename,
                file_type=file_type,
                file_size=file_size,
                language=language,
                chunking_strategy=chunking_strategy,
                total_chunks=total_chunks,
                doc_metadata=metadata or {}
            )
            
            db.add(document)
            db.commit()
            db.refresh(document)
            
            logger.info(f"Stored document: {document.id}")
            return document.id
        
        except Exception as e:
            db.rollback()
            logger.error(f"Error storing document: {e}")
            raise
        finally:
            db.close()
    
    def store_chunks(
        self,
        document_id: str,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]]
    ):
        """
        Store chunks in both PostgreSQL and ChromaDB
        
        Args:
            document_id: Parent document ID
            chunks: List of chunk dictionaries
            embeddings: List of embedding vectors
        """
        db = self.get_db_session()
        
        try:
            # Store in PostgreSQL
            chunk_ids = []
            for chunk_data in chunks:
                chunk = Chunk(
                    id=str(uuid.uuid4()),
                    document_id=document_id,
                    chunk_index=chunk_data['index'],
                    chunk_text=chunk_data['text'],
                    chunk_size=len(chunk_data['text']),
                    chunk_metadata=chunk_data.get('metadata', {})
                )
                db.add(chunk)
                chunk_ids.append(chunk.id)
            
            db.commit()
            
            # Store in ChromaDB
            self.collection.add(
                ids=chunk_ids,
                embeddings=embeddings,
                documents=[chunk['text'] for chunk in chunks],
                metadatas=[
                    {
                        'document_id': document_id,
                        'chunk_index': chunk['index'],
                        **chunk.get('metadata', {})
                    }
                    for chunk in chunks
                ]
            )
            
            logger.info(f"Stored {len(chunks)} chunks for document {document_id}")
        
        except Exception as e:
            db.rollback()
            logger.error(f"Error storing chunks: {e}")
            raise
        finally:
            db.close()
    
    def get_document(self, document_id: str) -> Optional[Document]:
        """Get document by ID"""
        db = self.get_db_session()
        try:
            return db.query(Document).filter(Document.id == document_id).first()
        finally:
            db.close()
    
    def get_all_documents(self) -> List[Document]:
        """Get all documents"""
        db = self.get_db_session()
        try:
            return db.query(Document).all()
        finally:
            db.close()
    
    def delete_document(self, document_id: str):
        """Delete document and all its chunks from both databases"""
        db = self.get_db_session()
        
        try:
            # Get all chunk IDs for this document
            chunks = db.query(Chunk).filter(Chunk.document_id == document_id).all()
            chunk_ids = [chunk.id for chunk in chunks]
            
            # Delete from PostgreSQL (cascades to chunks)
            document = db.query(Document).filter(Document.id == document_id).first()
            if document:
                db.delete(document)
                db.commit()
            
            # Delete from ChromaDB
            if chunk_ids:
                self.collection.delete(ids=chunk_ids)
            
            logger.info(f"Deleted document {document_id} and {len(chunk_ids)} chunks")
        
        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting document: {e}")
            raise
        finally:
            db.close()
    
    def search_similar_chunks(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        document_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search for similar chunks using vector similarity
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            document_id: Optional filter by document ID
            
        Returns:
            Dictionary with results
        """
        try:
            # Build where clause for filtering
            where = None
            if document_id:
                where = {"document_id": document_id}
            
            # Query ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where
            )
            
            return results
        
        except Exception as e:
            logger.error(f"Error searching chunks: {e}")
            raise
    
    def get_chunk_details(self, chunk_ids: List[str]) -> List[Chunk]:
        """Get full chunk details from PostgreSQL"""
        db = self.get_db_session()
        try:
            return db.query(Chunk).filter(Chunk.id.in_(chunk_ids)).all()
        finally:
            db.close()
