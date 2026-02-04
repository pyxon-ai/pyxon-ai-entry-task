"""
ChromaDB Vector Store for embeddings
"""
import logging
from typing import List, Dict, Optional, Any
from pathlib import Path
import uuid

import chromadb
from chromadb.config import Settings
import numpy as np

logger = logging.getLogger(__name__)


class VectorStore:
    """
    Vector storage using ChromaDB
    Stores embeddings with metadata for RAG retrieval
    """
    
    def __init__(
        self,
        persist_directory: str,
        collection_name: str = "arabic_documents",
        embedding_dimension: int = 384
    ):
        """
        Initialize ChromaDB vector store
        
        Args:
            persist_directory: Directory to persist the database
            collection_name: Name of the collection
            embedding_dimension: Dimension of embeddings
        """
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        self.collection_name = collection_name
        self.embedding_dimension = embedding_dimension
        
        logger.info(f"Initializing ChromaDB at {persist_directory}")
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Get or create collection
        try:
            self.collection = self.client.get_collection(name=collection_name)
            logger.info(f"Loaded existing collection: {collection_name}")
        except Exception:
            self.collection = self.client.create_collection(
                name=collection_name,
                metadata={"dimension": embedding_dimension}
            )
            logger.info(f"Created new collection: {collection_name}")
    
    def add_chunks(
        self,
        chunks: List[str],
        embeddings: np.ndarray,
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ) -> List[str]:
        """
        Add chunks with embeddings to the vector store
        
        Args:
            chunks: List of text chunks
            embeddings: Array of embeddings (shape: [n_chunks, dimension])
            metadatas: Optional list of metadata dictionaries
            ids: Optional list of IDs (will generate UUIDs if not provided)
            
        Returns:
            List of chunk IDs
        """
        n_chunks = len(chunks)
        
        # Generate IDs if not provided
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in range(n_chunks)]
        
        # Prepare metadatas
        if metadatas is None:
            metadatas = [{} for _ in range(n_chunks)]
        
        # Convert embeddings to list
        embeddings_list = embeddings.tolist() if isinstance(embeddings, np.ndarray) else embeddings
        
        # Add to collection
        self.collection.add(
            documents=chunks,
            embeddings=embeddings_list,
            metadatas=metadatas,
            ids=ids
        )
        
        logger.info(f"Added {n_chunks} chunks to vector store")
        
        return ids
    
    def query(
        self,
        query_embedding: np.ndarray,
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Query the vector store for similar chunks
        
        Args:
            query_embedding: Query embedding vector
            n_results: Number of results to return
            where: Optional metadata filter
            where_document: Optional document content filter
            
        Returns:
            Dictionary with query results
        """
        # Convert embedding to list
        query_embedding_list = query_embedding.tolist() if isinstance(query_embedding, np.ndarray) else query_embedding
        
        results = self.collection.query(
            query_embeddings=[query_embedding_list],
            n_results=n_results,
            where=where,
            where_document=where_document
        )
        
        return results
    
    def query_by_text(
        self,
        query_texts: List[str],
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Query using text (ChromaDB will use its internal embedding)
        Note: This requires ChromaDB to have an embedding function set
        
        Args:
            query_texts: List of query texts
            n_results: Number of results per query
            where: Optional metadata filter
            
        Returns:
            Dictionary with query results
        """
        results = self.collection.query(
            query_texts=query_texts,
            n_results=n_results,
            where=where
        )
        
        return results
    
    def get_by_ids(self, ids: List[str]) -> Dict[str, Any]:
        """
        Retrieve chunks by their IDs
        
        Args:
            ids: List of chunk IDs
            
        Returns:
            Dictionary with retrieved chunks
        """
        results = self.collection.get(ids=ids)
        return results
    
    def delete_by_ids(self, ids: List[str]) -> None:
        """
        Delete chunks by their IDs
        
        Args:
            ids: List of chunk IDs to delete
        """
        self.collection.delete(ids=ids)
        logger.info(f"Deleted {len(ids)} chunks from vector store")
    
    def delete_collection(self) -> None:
        """Delete the entire collection"""
        self.client.delete_collection(name=self.collection_name)
        logger.warning(f"Deleted collection: {self.collection_name}")
    
    def get_count(self) -> int:
        """
        Get total number of chunks in the collection
        
        Returns:
            Number of chunks
        """
        return self.collection.count()
    
    def peek(self, limit: int = 10) -> Dict[str, Any]:
        """
        Peek at the first few items in the collection
        
        Args:
            limit: Number of items to peek
            
        Returns:
            Dictionary with sample items
        """
        return self.collection.peek(limit=limit)
    
    def reset(self) -> None:
        """Reset the vector store (delete and recreate collection)"""
        try:
            self.client.delete_collection(name=self.collection_name)
        except Exception:
            pass
        
        self.collection = self.client.create_collection(
            name=self.collection_name,
            metadata={"dimension": self.embedding_dimension}
        )
        
        logger.info(f"Reset vector store: {self.collection_name}")
    
    def get_info(self) -> Dict[str, Any]:
        """
        Get information about the vector store
        
        Returns:
            Dictionary with store information
        """
        return {
            'collection_name': self.collection_name,
            'persist_directory': str(self.persist_directory),
            'embedding_dimension': self.embedding_dimension,
            'total_chunks': self.get_count(),
        }
