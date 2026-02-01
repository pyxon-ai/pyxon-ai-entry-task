import os 
import sqlite3
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any
from enum import Enum 
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.retrievers.ensemble import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document

class ChunkingStrategy(Enum):
    FIXED = "fixed"
    DYNAMIC = "dynamic"

class DocumentProcessor:
    def __init__(self, persist_directory: str = "./db_storage"):
        self.persist_directory = persist_directory
        self.sql_db_path = os.path.join(persist_directory, "metadata.db")
        
        os.makedirs(persist_directory, exist_ok=True)
        self._init_sql_db()
        
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
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                file_type TEXT,
                chunking_strategy TEXT,
                total_chunks INTEGER
            )
        ''')
        conn.commit()
        conn.close()

    def process_file(self, file_path: str, filename: str) -> bool:
        try:
            # 1. Load Document
            raw_documents = self._load_document(file_path)
            if not raw_documents:
                return False

            # 2. Analyze & Decide Strategy
            strategy = self._decide_chunking_strategy(raw_documents)
            
            # 3. Chunking
            chunks = self._chunk_document(raw_documents, strategy)
            
            # 4. Store in Vector DB
            self.vector_db.add_documents(chunks)
            
            # 5. Store Metadata in SQL
            self._save_metadata(filename, file_path.split('.')[-1], strategy.value, len(chunks))
            
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

    def _decide_chunking_strategy(self, docs: List[Document]) -> ChunkingStrategy:
        full_text = " ".join([d.page_content for d in docs])
        
        # Simple heuristic: Structure variance detection
        # High ratio of newlines to text length suggests structured content (lists, headers) -> Dynamic
        # Dense blocks of text suggest reports/articles -> Fixed
        
        structure_markers = full_text.count('\n\n') + full_text.count('##')
        text_length = len(full_text)
        
        if text_length == 0: 
            return ChunkingStrategy.FIXED
            
        structure_ratio = structure_markers / (text_length / 1000)
        
        if structure_ratio > 5.0:
            return ChunkingStrategy.DYNAMIC
        return ChunkingStrategy.FIXED

    def _chunk_document(self, docs: List[Document], strategy: ChunkingStrategy) -> List[Document]:
        if strategy == ChunkingStrategy.DYNAMIC:
            # Respects semantic boundaries (paragraphs, headers)
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                separators=["\n\n", "\n", "。", ".", " ", ""]
            )
        else:
            # Fixed size, strict splitting
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=500,
                chunk_overlap=50,
                separators=["\n\n", "\n", " ", ""] 
            )
            
        return splitter.split_documents(docs)

    def _save_metadata(self, filename: str, file_type: str, strategy: str, chunk_count: int):
        conn = sqlite3.connect(self.sql_db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO documents (filename, file_type, chunking_strategy, total_chunks) VALUES (?, ?, ?, ?)",
            (filename, file_type, strategy, chunk_count)
        )
        conn.commit()
        conn.close()

    def get_retriever(self):
        chroma_retriever = self.vector_db.as_retriever(
            search_type="mmr", 
            search_kwargs={"k": 5}
        )
        
        # We need raw docs for BM25, pulling from vector store for simplicity in this architecture
        # In production, we might cache this separately.
        all_docs = self.vector_db.get()['documents']
        if not all_docs:
            return chroma_retriever
            
        bm25_retriever = BM25Retriever.from_texts(all_docs)
        bm25_retriever.k = 5
        
        ensemble_retriever = EnsembleRetriever(
            retrievers=[bm25_retriever, chroma_retriever],
            weights=[0.3, 0.7] # Weigh semantic search higher
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
                "chunks": r[5]
            } 
            for r in rows
        ]