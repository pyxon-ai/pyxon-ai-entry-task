# src.pyxon.storage.vs

from typing import List

from langchain_core.documents import Document
from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pinecone import Pinecone
from langchain_core.vectorstores import  VectorStoreRetriever

from src.config import Settings


class VectorStore:
    def __init__(self):
        self.index_name = Settings.INDEX

        self.embedding_func = OpenAIEmbeddings(
            model=Settings.EMBEDDING_MODEL_NAME,
            api_key=Settings.OPENAI_API_KEY,
            dimensions=Settings.DIMENSIONS,
        )

        self.pc = Pinecone(api_key=Settings.PINECONE_API_KEY)

        self._vs = PineconeVectorStore(
            index=self.pc.Index(self.index_name),
            embedding=self.embedding_func,
        )

    def chunk_document(self, doc: Document) -> List[Document]:
        chunker = self._get_chunker(doc)
        return chunker.split_documents([doc])

    def _get_chunker(self, doc: Document):
        if doc.metadata.get("chunking_strategy") == "FIXED":
            return RecursiveCharacterTextSplitter(
                chunk_size=doc.metadata.get("chunk_size"),
                chunk_overlap=doc.metadata.get("chunk_overlap"),
            )

        return SemanticChunker(
            self.embedding_func, breakpoint_threshold_amount=Settings.PERCENTILE_THRESH
        )

    def add_documents(self, chunks: List[Document], document_id: str):
        for i, chunk in enumerate(chunks):
            chunk.metadata.update(
                {
                    "document_id": document_id,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                }
            )

        self._vs.add_documents(chunks)

    def get_retriever(self) -> VectorStoreRetriever:
        return self._vs.as_retriever()
    
    def get_all_chunks(self) -> List[Document]:
        return self._vs.similarity_search("", k=10000)

