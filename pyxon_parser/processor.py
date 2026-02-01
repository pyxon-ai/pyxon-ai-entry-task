import os
import sqlite3
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any
from enum import Enum

from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from pydantic import Field
from collections import defaultdict



class ChunkingStrategy(Enum):
    FIXED = "fixed"
    DYNAMIC = "dynamic"


class DocumentProcessor:
    def __init__(self, persist_directory: str = "./db_storage"):
        self.persist_directory = persist_directory
        self.sql_db_path = os.path.join(persist_directory, "metadata.db")
        
        os.makedirs(persist_directory, exist_ok=True)
        self._init_sql_db()
        
        # Using the Multilingual E5 model (Best for Arabic/English mix)
        self.embedding_model = HuggingFaceEmbeddings(
            model_name="intfloat/multilingual-e5-small",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True}
        )
        
        self.vector_db = Chroma(
            persist_directory=os.path.join(persist_directory, "chroma"),
            embedding_function=self.embedding_model
        )

    def _init_sql_db(self):
        conn = sqlite3.connect(self.sql_db_path)
        cursor = conn.cursor()
        # Added 'metrics' column to store why we chose the strategy
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                file_type TEXT,
                chunking_strategy TEXT,
                strategy_metrics TEXT,  
                total_chunks INTEGER
            )
        ''')
        conn.commit()
        conn.close()

    def process_file(self, file_path: str, filename: str) -> bool:
        try:
            # 1. Load
            raw_documents = self._load_document(file_path)
            if not raw_documents:
                return False

            # Merge for analysis
            full_text = "\n".join([d.page_content for d in raw_documents])

            # 2. Analyze (The Upgrade)
            analysis = StructureAnalyzer.analyze(full_text)
            strategy = analysis["strategy"]
            metrics_str = str(analysis["metrics"])
            
            print(f"File Analysis for {filename}: {analysis}") # Debugging/Demo log

            # 3. Chunk
            chunks = self._chunk_document(full_text, strategy, raw_documents) # Pass full text + raw docs
            
            # 4. Store Vector
            self.vector_db.add_documents(chunks)
            
            # 5. Store Metadata
            self._save_metadata(filename, file_path.split('.')[-1], strategy.value, metrics_str, len(chunks))
            
            return True
        except Exception as e:
            print(f"Error processing file: {e}")
            return False

    def _load_document(self, file_path: str) -> List[Document]:
        ext = file_path.split('.')[-1].lower()
        if ext == 'pdf':
            loader = PyPDFLoader(file_path)
        elif ext in ['docx', 'doc']:
            loader = Docx2txtLoader(file_path)
        elif ext == 'txt':
            loader = TextLoader(file_path, encoding='utf-8')
        else:
            return []
        return loader.load()

    def _chunk_document(self, full_text: str, strategy: ChunkingStrategy, raw_docs: List[Document]) -> List[Document]:
        if strategy == ChunkingStrategy.SEMANTIC:
            # HYBRID SPLITTING: 
            # 1. Try to split by Headers (Markdown style) first to keep structure
            # Even if it's not markdown, we treat newlines as potential breaks
            
            headers_to_split_on = [
                ("#", "Header 1"),
                ("##", "Header 2"),
                ("###", "Header 3"),
            ]
            
            # Note: Since raw text might not be markdown, we rely on the secondary splitter mostly,
            # but this sets up the architecture for advanced processing.
            # For this task, we focus on a smarter Recursive splitter for Arabic.
            
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=800,
                chunk_overlap=150,
                # ARABIC OPTIMIZED SEPARATORS
                # Split by double newline (paragraph), then dot+space (sentence), then newline
                separators=["\n\n", ".\n", ".\s", "\n", " ", ""]
            )
            
            # If we had real Markdown, we'd use MarkdownHeaderTextSplitter here.
            # For general docs, we apply the smarter recursive splitter on the original docs
            return splitter.split_documents(raw_docs)
            
        else:
            # FIXED Strategy: Faster, larger chunks, less sensitive to structure
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=100,
                separators=["\n\n", "\n", " ", ""]
            )
            return splitter.split_documents(raw_docs)

    def _save_metadata(self, filename: str, file_type: str, strategy: str, metrics: str, chunk_count: int):
        conn = sqlite3.connect(self.sql_db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO documents (filename, file_type, chunking_strategy, strategy_metrics, total_chunks) VALUES (?, ?, ?, ?, ?)",
            (filename, file_type, strategy, metrics, chunk_count)
        )
        conn.commit()
        conn.close()

    def get_retriever(self):
        chroma_retriever = self.vector_db.as_retriever(
            search_type="mmr", 
            search_kwargs={"k": 5}
        )
        
        try:
            # Safety check: Chroma might be empty
            all_docs = self.vector_db.get()['documents']
            if not all_docs:
                return chroma_retriever
        except:
            return chroma_retriever
            
        bm25_retriever = BM25Retriever.from_texts(all_docs)
        bm25_retriever.k = 5
        
        ensemble_retriever = EnsembleRetriever(
            retrievers=[bm25_retriever, chroma_retriever],
            weights=[0.4, 0.6] # Adjusted weights
        )
        return ensemble_retriever

    def get_all_documents(self) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.sql_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM documents ORDER BY upload_date DESC")
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "id": r[0], 
                "filename": r[1], 
                "date": r[2], 
                "type": r[3], 
                "strategy": r[4], 
                "metrics": r[5], # New field
                "chunks": r[6]
            } 
            for r in rows
        ]