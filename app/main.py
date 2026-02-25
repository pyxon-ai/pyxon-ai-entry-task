import os
import uuid
import logging
from typing import List, Dict, Any
from app.parser.loader import load_document
from app.parser.chunker import chunk_text
from app.embeddings.embedder import Embedder
from app.storage.vector_db import VectorDB
from app.storage.sql_db import SQLDB

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DocumentProcessor:
    def __init__(self):
        """
        Initialize the full RAG pipeline components.
        """
        self.embedder = Embedder()
        self.vector_db = VectorDB()
        self.sql_db = SQLDB()
        logging.info("🚀 DocumentProcessor initialized successfully.")

    def process_file(self, file_path: str) -> tuple:
        """
        Execute the full pipeline for a single file.
        Returns: (doc_id, preview_chunks)
        """
        logging.info(f"[*] Processing file: {file_path}")
        
        try:
            # 1. Load
            text = load_document(file_path)
            if not text or not text.strip():
                raise ValueError("No text could be extracted. File might be empty or scanned image.")
            
            filename = os.path.basename(file_path)
            file_type = filename.split('.')[-1]
            doc_id = str(uuid.uuid4())
            
            # 2. Store document metadata in SQL
            self.sql_db.add_document(doc_id, filename, file_type)
            
            # 3. Chunk
            chunks_data = chunk_text(text)
            logging.info(f"[+] Created {len(chunks_data)} chunks for {filename}.")
            
            if not chunks_data:
                logging.warning("File produced 0 chunks. Skipping embedding.")
                return doc_id, []

            # Unpack chunks and headings
            chunk_texts = [c[0] for c in chunks_data]
            chunk_headings = [c[1] for c in chunks_data]

            # 4. Embed (Batch processing is faster)
            embeddings = self.embedder.embed_batch(chunk_texts)
            
            # 5. Prepare data for storage
            chunk_ids = []
            metadatas = []
            
            for i, (chunk, embedding, heading) in enumerate(zip(chunk_texts, embeddings, chunk_headings)):
                chunk_id = f"{doc_id}_{i}"
                chunk_ids.append(chunk_id)
                
                # Metadata for Vector DB
                metadata = {
                    "doc_id": doc_id,
                    "filename": filename,
                    "chunk_index": i
                }
                if heading:
                    metadata["heading"] = heading
                    
                metadatas.append(metadata)
                
                # Store in SQL (Detailed storage)
                try:
                    self.sql_db.add_chunk(chunk_id, doc_id, i, chunk, heading=heading)
                except TypeError:
                    # Fallback if add_chunk signature in SQLDB hasn't been updated to accept heading
                     self.sql_db.add_chunk(chunk_id, doc_id, i, chunk)
                
            # Store in Vector DB
            self.vector_db.add_chunks(chunk_texts, embeddings, metadatas, chunk_ids)
            
            logging.info(f"✅ Processing complete for {filename}. Doc ID: {doc_id}")
            # Return doc_id and first 3 chunks type for preview
            return doc_id, chunk_texts[:3]

        except Exception as e:
            logging.error(f"❌ Error processing file {file_path}: {str(e)}")
            raise e

    def ask(self, query: str, n_results: int = 3) -> Dict[str, Any]:
        """
        Semantic search for a query with formatted output.
        """
        logging.info(f"🔍 Searching for: {query}")
        
        # 1. Embed query
        query_embedding = self.embedder.embed_text(query)
        
        # 2. Search Vector DB
        results = self.vector_db.search(query_embedding, n_results=n_results)
        
        return results

if __name__ == "__main__":
    processor = DocumentProcessor()
    # processor.process_file("data/sample.docx")
