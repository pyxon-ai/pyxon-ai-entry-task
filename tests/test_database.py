"""Tests for database operations."""

import pytest
from sqlalchemy.orm import Session
from src.database.connection import db_manager
from src.database.repository import DocumentRepository, ChunkRepository
from src.database.models import DocumentModel, ChunkModel
from src.models.document import Document, DocumentMetadata, Chunk, ChunkMetadata


class TestDocumentRepository:
    """Tests for document repository operations."""
    
    def test_create_document(self):
        """Test creating a document."""
        session = db_manager.get_session()
        repo = DocumentRepository(session)
        
        doc = Document(
            id="test_doc_1",
            filename="test.txt",
            file_type="txt",
            content="Test content",
            metadata=DocumentMetadata(title="Test Document"),
        )
        
        result = repo.create_document(doc)
        assert result.id == "test_doc_1"
        assert result.filename == "test.txt"
        session.close()
    
    def test_get_document(self):
        """Test retrieving a document."""
        session = db_manager.get_session()
        repo = DocumentRepository(session)
        
        # Create a document first
        doc = Document(
            id="test_doc_2",
            filename="test.txt",
            file_type="txt",
            content="Test content",
            metadata=DocumentMetadata(),
        )
        repo.create_document(doc)
        
        # Retrieve it
        retrieved = repo.get_document("test_doc_2")
        assert retrieved is not None
        assert retrieved.id == "test_doc_2"
        session.close()
    
    def test_get_all_documents(self):
        """Test retrieving all documents."""
        session = db_manager.get_session()
        repo = DocumentRepository(session)
        
        # Create multiple documents
        for i in range(3):
            doc = Document(
                id=f"test_doc_{i}",
                filename=f"test{i}.txt",
                file_type="txt",
                content=f"Content {i}",
                metadata=DocumentMetadata(),
            )
            repo.create_document(doc)
        
        # Retrieve all
        docs = repo.get_all_documents()
        assert len(docs) >= 3
        session.close()
    
    def test_delete_document(self):
        """Test deleting a document."""
        session = db_manager.get_session()
        repo = DocumentRepository(session)
        
        # Create a document
        doc = Document(
            id="test_doc_delete",
            filename="test.txt",
            file_type="txt",
            content="Test content",
            metadata=DocumentMetadata(),
        )
        repo.create_document(doc)
        
        # Delete it
        result = repo.delete_document("test_doc_delete")
        assert result is True
        
        # Verify it's gone
        retrieved = repo.get_document("test_doc_delete")
        assert retrieved is None
        session.close()


class TestChunkRepository:
    """Tests for chunk repository operations."""
    
    def test_create_chunks(self):
        """Test creating chunks."""
        session = db_manager.get_session()
        doc_repo = DocumentRepository(session)
        chunk_repo = ChunkRepository(session)
        
        # Create a document first
        doc = Document(
            id="test_doc_chunks",
            filename="test.txt",
            file_type="txt",
            content="Test content for chunks",
            metadata=DocumentMetadata(),
        )
        doc_repo.create_document(doc)
        
        # Create chunks
        chunks = [
            Chunk(
                id=f"chunk_{i}",
                document_id="test_doc_chunks",
                content=f"Chunk content {i}",
                metadata=ChunkMetadata(
                    chunk_index=i,
                    token_count=10,
                    char_count=15,
                ),
            )
            for i in range(3)
        ]
        
        result = chunk_repo.create_chunks(chunks)
        assert len(result) == 3
        session.close()
    
    def test_get_chunks_by_document(self):
        """Test retrieving chunks by document."""
        session = db_manager.get_session()
        doc_repo = DocumentRepository(session)
        chunk_repo = ChunkRepository(session)
        
        # Create document and chunks
        doc = Document(
            id="test_doc_retrieve",
            filename="test.txt",
            file_type="txt",
            content="Test content",
            metadata=DocumentMetadata(),
        )
        doc_repo.create_document(doc)
        
        chunks = [
            Chunk(
                id=f"retrieve_chunk_{i}",
                document_id="test_doc_retrieve",
                content=f"Chunk {i}",
                metadata=ChunkMetadata(
                    chunk_index=i,
                    token_count=5,
                    char_count=8,
                ),
            )
            for i in range(2)
        ]
        chunk_repo.create_chunks(chunks)
        
        # Retrieve chunks
        retrieved = chunk_repo.get_chunks_by_document("test_doc_retrieve")
        assert len(retrieved) == 2
        session.close()
    
    def test_count_chunks(self):
        """Test counting chunks."""
        session = db_manager.get_session()
        chunk_repo = ChunkRepository(session)
        
        # Create some chunks
        chunks = [
            Chunk(
                id=f"count_chunk_{i}",
                document_id="test_doc_count",
                content=f"Chunk {i}",
                metadata=ChunkMetadata(
                    chunk_index=i,
                    token_count=5,
                    char_count=8,
                ),
            )
            for i in range(5)
        ]
        chunk_repo.create_chunks(chunks)
        
        # Count chunks
        count = chunk_repo.count_chunks(document_id="test_doc_count")
        assert count >= 5
        session.close()


class TestDatabaseConnection:
    """Tests for database connection management."""
    
    def test_init_db(self):
        """Test database initialization."""
        db_manager.init_db()
        assert db_manager.engine is not None
        assert db_manager.SessionLocal is not None
    
    def test_get_session(self):
        """Test getting a database session."""
        session = db_manager.get_session()
        assert session is not None
        session.close()
    
    def test_create_tables(self):
        """Test table creation."""
        db_manager.init_db()
        db_manager.create_tables()
        # If no exception, tables created successfully
        assert True
