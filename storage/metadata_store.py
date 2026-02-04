"""
SQLite Metadata Store for tracking document processing
"""
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON, Float, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

logger = logging.getLogger(__name__)

Base = declarative_base()


class DocumentMetadata(Base):
    """Document metadata table"""
    __tablename__ = 'documents'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    file_path = Column(String, unique=True, nullable=False, index=True)
    file_name = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    file_size = Column(Integer)
    
    # Processing metadata
    processed_at = Column(DateTime, default=datetime.utcnow)
    chunking_strategy = Column(String)
    num_chunks = Column(Integer)
    
    # Content metadata
    is_arabic = Column(Boolean, default=False)
    encoding = Column(String)
    
    # Additional metadata as JSON
    extra_metadata = Column(JSON)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'file_path': self.file_path,
            'file_name': self.file_name,
            'file_type': self.file_type,
            'file_size': self.file_size,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'chunking_strategy': self.chunking_strategy,
            'num_chunks': self.num_chunks,
            'is_arabic': self.is_arabic,
            'encoding': self.encoding,
            'extra_metadata': self.extra_metadata,
        }


class ChunkMetadata(Base):
    """Chunk metadata table"""
    __tablename__ = 'chunks'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    chunk_id_vector = Column(String, unique=True, nullable=False, index=True)  # UUID from vector store
    document_id = Column(Integer, nullable=False, index=True)  # FK to documents
    
    chunk_index = Column(Integer, nullable=False)
    start_idx = Column(Integer)
    end_idx = Column(Integer)
    
    # Chunk content info
    text_preview = Column(Text)  # First 200 chars
    chunk_size = Column(Integer)
    
    # Processing metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Additional metadata as JSON
    chunk_metadata = Column(JSON)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'chunk_id_vector': self.chunk_id_vector,
            'document_id': self.document_id,
            'chunk_index': self.chunk_index,
            'start_idx': self.start_idx,
            'end_idx': self.end_idx,
            'text_preview': self.text_preview,
            'chunk_size': self.chunk_size,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'chunk_metadata': self.chunk_metadata,
        }


class BenchmarkRun(Base):
    """Benchmark results table"""
    __tablename__ = 'benchmarks'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_name = Column(String, nullable=False)
    run_timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Performance metrics
    processing_time = Column(Float)  # seconds
    memory_usage = Column(Float)  # MB
    
    # Quality metrics
    retrieval_accuracy = Column(Float)  # 0-1
    hit_rate = Column(Float)  # 0-1
    
    # Configuration
    chunking_strategy = Column(String)
    num_documents = Column(Integer)
    num_chunks = Column(Integer)
    
    # Detailed results as JSON
    detailed_results = Column(JSON)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'run_name': self.run_name,
            'run_timestamp': self.run_timestamp.isoformat() if self.run_timestamp else None,
            'processing_time': self.processing_time,
            'memory_usage': self.memory_usage,
            'retrieval_accuracy': self.retrieval_accuracy,
            'hit_rate': self.hit_rate,
            'chunking_strategy': self.chunking_strategy,
            'num_documents': self.num_documents,
            'num_chunks': self.num_chunks,
            'detailed_results': self.detailed_results,
        }


class MetadataStore:
    """
    SQLite metadata store for tracking documents, chunks, and benchmarks
    """
    
    def __init__(self, db_path: str):
        """
        Initialize metadata store
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create engine
        self.engine = create_engine(f'sqlite:///{self.db_path}', echo=False)
        
        # Create tables
        Base.metadata.create_all(self.engine)
        
        # Create session factory
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        logger.info(f"Initialized metadata store at {db_path}")
    
    def get_session(self) -> Session:
        """Get a new database session"""
        return self.SessionLocal()
    
    # ========== Document Operations ==========
    
    def add_document(
        self,
        file_path: str,
        file_name: str,
        file_type: str,
        file_size: int,
        chunking_strategy: str,
        num_chunks: int,
        is_arabic: bool = False,
        encoding: Optional[str] = None,
        extra_metadata: Optional[Dict] = None
    ) -> int:
        """
        Add document metadata
        
        Returns:
            Document ID
        """
        session = self.get_session()
        
        try:
            doc = DocumentMetadata(
                file_path=file_path,
                file_name=file_name,
                file_type=file_type,
                file_size=file_size,
                chunking_strategy=chunking_strategy,
                num_chunks=num_chunks,
                is_arabic=is_arabic,
                encoding=encoding,
                extra_metadata=extra_metadata or {}
            )
            
            session.add(doc)
            session.commit()
            
            doc_id = doc.id
            logger.info(f"Added document: {file_name} (ID: {doc_id})")
            
            return doc_id
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to add document: {e}")
            raise
        finally:
            session.close()
    
    def get_document(self, doc_id: int) -> Optional[Dict]:
        """Get document by ID"""
        session = self.get_session()
        
        try:
            doc = session.query(DocumentMetadata).filter_by(id=doc_id).first()
            return doc.to_dict() if doc else None
        finally:
            session.close()
    
    def get_document_by_path(self, file_path: str) -> Optional[Dict]:
        """Get document by file path"""
        session = self.get_session()
        
        try:
            doc = session.query(DocumentMetadata).filter_by(file_path=file_path).first()
            return doc.to_dict() if doc else None
        finally:
            session.close()
    
    def delete_document_by_path(self, file_path: str) -> bool:
        """Delete document and its chunks by file path"""
        session = self.get_session()
        try:
            doc = session.query(DocumentMetadata).filter_by(file_path=file_path).first()
            if doc:
                # Delete associated chunks first
                session.query(ChunkMetadata).filter_by(document_id=doc.id).delete()
                # Delete document
                session.delete(doc)
                session.commit()
                logger.info(f"Deleted existing document: {file_path}")
                return True
            return False
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to delete document: {e}")
            return False
        finally:
            session.close()

    def get_all_documents(self) -> List[Dict]:
        """Get all documents"""
        session = self.get_session()
        
        try:
            docs = session.query(DocumentMetadata).all()
            return [doc.to_dict() for doc in docs]
        finally:
            session.close()
    
    # ========== Chunk Operations ==========
    
    def add_chunk(
        self,
        chunk_id_vector: str,
        document_id: int,
        chunk_index: int,
        start_idx: int,
        end_idx: int,
        text: str,
        chunk_metadata: Optional[Dict] = None
    ) -> int:
        """
        Add chunk metadata
        
        Returns:
            Chunk metadata ID
        """
        session = self.get_session()
        
        try:
            chunk = ChunkMetadata(
                chunk_id_vector=chunk_id_vector,
                document_id=document_id,
                chunk_index=chunk_index,
                start_idx=start_idx,
                end_idx=end_idx,
                text_preview=text[:200] if text else "",
                chunk_size=len(text) if text else 0,
                chunk_metadata=chunk_metadata or {}
            )
            
            session.add(chunk)
            session.commit()
            
            return chunk.id
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to add chunk: {e}")
            raise
        finally:
            session.close()
    
    def get_all_chunks(self) -> List[Dict]:
        """Get all chunks in the database"""
        session = self.get_session()
        
        try:
            chunks = session.query(ChunkMetadata).all()
            return [chunk.to_dict() for chunk in chunks]
        finally:
            session.close()

    def get_chunks_by_document(self, doc_id: int) -> List[Dict]:
        """Get all chunks for a document"""
        session = self.get_session()
        
        try:
            chunks = session.query(ChunkMetadata).filter_by(document_id=doc_id).all()
            return [chunk.to_dict() for chunk in chunks]
        finally:
            session.close()
    
    # ========== Benchmark Operations ==========
    
    def add_benchmark(
        self,
        run_name: str,
        processing_time: float,
        memory_usage: float,
        retrieval_accuracy: float,
        hit_rate: float,
        chunking_strategy: str,
        num_documents: int,
        num_chunks: int,
        detailed_results: Optional[Dict] = None
    ) -> int:
        """
        Add benchmark run
        
        Returns:
            Benchmark ID
        """
        session = self.get_session()
        
        try:
            benchmark = BenchmarkRun(
                run_name=run_name,
                processing_time=processing_time,
                memory_usage=memory_usage,
                retrieval_accuracy=retrieval_accuracy,
                hit_rate=hit_rate,
                chunking_strategy=chunking_strategy,
                num_documents=num_documents,
                num_chunks=num_chunks,
                detailed_results=detailed_results or {}
            )
            
            session.add(benchmark)
            session.commit()
            
            logger.info(f"Added benchmark run: {run_name}")
            return benchmark.id
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to add benchmark: {e}")
            raise
        finally:
            session.close()
    
    def get_all_benchmarks(self) -> List[Dict]:
        """Get all benchmark runs"""
        session = self.get_session()
        
        try:
            benchmarks = session.query(BenchmarkRun).order_by(BenchmarkRun.run_timestamp.desc()).all()
            return [b.to_dict() for b in benchmarks]
        finally:
            session.close()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get overall statistics"""
        session = self.get_session()
        
        try:
            total_docs = session.query(DocumentMetadata).count()
            total_chunks = session.query(ChunkMetadata).count()
            arabic_docs = session.query(DocumentMetadata).filter_by(is_arabic=True).count()
            
            return {
                'total_documents': total_docs,
                'total_chunks': total_chunks,
                'arabic_documents': arabic_docs,
                'total_benchmarks': session.query(BenchmarkRun).count(),
            }
        finally:
            session.close()

    def reset(self):
        """Reset the metadata store (delete all data)"""
        logger.warning("Resetting metadata store...")
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
        logger.info("Metadata store reset complete")
