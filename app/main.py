import os
import tempfile

from app.parsers.pdf_parser import PDFParser
from app.parsers.docx_parser import DOCXParser
from app.parsers.txt_parser import TXTParser

from app.analysis.content_analyzer import ContentAnalyzer
from app.chunking.chunk_selector import ChunkSelector

from app.embeddings.embedder import Embedder
from app.storage.vector_store import VectorStore
from app.storage.sql_store import SQLStore


class DocuRAGPipeline:
    def __init__(self):
        self.analyzer = ContentAnalyzer()
        self.chunk_selector = ChunkSelector()
        self.embedder = Embedder()
        self.vector_store = VectorStore()
        self.sql_store = SQLStore()

    def _get_parser(self, file_path: str):
        if file_path.endswith(".pdf"):
            return PDFParser()
        elif file_path.endswith(".docx"):
            return DOCXParser()
        elif file_path.endswith(".txt"):
            return TXTParser()
        else:
            raise ValueError("Unsupported file type")

    def process_document(self, file_path: str) -> dict:
        # Parse document
        parser = self._get_parser(file_path)
        parsed = parser.parse(file_path)
        text = parsed["text"]

        # Analyze content
        analysis = self.analyzer.analyze(text)

        # Intelligent chunking
        chunking_result = self.chunk_selector.select_and_chunk(text, analysis)
        chunks = chunking_result["chunks"]

        # Embeddings
        embeddings = self.embedder.embed(chunks)

        # Store document metadata in SQL
        doc_id = self.sql_store.insert_document(
            source=parsed["source"],
            language=analysis["language"],
            num_chunks=len(chunks),
            chunking_strategy=chunking_result["strategy"]
        )

        # Store chunks in Vector DB + SQL
        for idx, (chunk, vector) in enumerate(zip(chunks, embeddings)):
            self.vector_store.add_vector(
                vector=vector,
                text=chunk,
                metadata={
                    "doc_id": doc_id,
                    "chunk_id": idx
                }
            )

            self.sql_store.insert_chunk(
                doc_id=doc_id,
                chunk_id=idx,
                text=chunk
            )

        return {
            "doc_id": doc_id,
            "chunking_strategy": chunking_result["strategy"],
            "num_chunks": len(chunks),
            "language": analysis["language"]
        }


def run_pipeline_from_upload(uploaded_file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=uploaded_file.name) as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name

    pipeline = DocuRAGPipeline()
    result = pipeline.process_document(tmp_path)

    os.remove(tmp_path)
    return result


if __name__ == "__main__":
    pipeline = DocuRAGPipeline()
    pipeline.process_document("data/arabic_sample.txt")
    print("✅ Document ingested successfully")