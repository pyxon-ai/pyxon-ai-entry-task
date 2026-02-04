"""SQLAlchemy database models."""

from datetime import datetime
from typing import List, Optional
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    DateTime,
    Boolean,
    Text,
    ForeignKey,
    JSON,
    Index,
    LargeBinary,
)
from sqlalchemy.orm import relationship, declarative_base
from src.database.connection import Base


class DocumentModel(Base):
    """Document model for SQL storage."""
    __tablename__ = "documents"

    id = Column(String, primary_key=True)
    filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    
    # Metadata
    title = Column(String, nullable=True)
    author = Column(String, nullable=True)
    subject = Column(String, nullable=True)
    keywords = Column(JSON, nullable=True)
    created_date = Column(DateTime, nullable=True)
    modified_date = Column(DateTime, nullable=True)
    page_count = Column(Integer, nullable=True)
    word_count = Column(Integer, nullable=True)
    language = Column(String, nullable=True)
    has_arabic = Column(Boolean, default=False)
    has_diacritics = Column(Boolean, default=False)
    
    # Processing
    chunking_strategy = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    
    # Relationships
    chunks = relationship("ChunkModel", back_populates="document", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_documents_filename', 'filename'),
        Index('idx_documents_file_type', 'file_type'),
        Index('idx_documents_created_at', 'created_at'),
    )


class ChunkModel(Base):
    """Chunk model for SQL storage."""
    __tablename__ = "chunks"

    id = Column(String, primary_key=True)
    document_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    
    # Metadata
    chunk_index = Column(Integer, nullable=False)
    page_number = Column(Integer, nullable=True)
    chunk_type = Column(String, nullable=True)
    heading = Column(String, nullable=True)
    token_count = Column(Integer, nullable=False)
    char_count = Column(Integer, nullable=False)
    has_arabic = Column(Boolean, default=False)
    has_diacritics = Column(Boolean, default=False)
    
    # Vector embedding (stored as JSON for compatibility, can be upgraded to pgvector)
    embedding = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    document = relationship("DocumentModel", back_populates="chunks")

    __table_args__ = (
        Index('idx_chunks_document_id', 'document_id'),
        Index('idx_chunks_chunk_index', 'chunk_index'),
        Index('idx_chunks_chunk_type', 'chunk_type'),
    )
