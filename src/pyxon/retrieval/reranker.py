# src.pyxon.retrieval.reranker

from typing import List
from langchain_core.documents import Document
from sentence_transformers import CrossEncoder

from src.config import Settings

class CrossEncoderReranker:    
    def __init__(self):
        self.model = CrossEncoder(Settings.CROSS_ENCODER_MODEL_NAME)
    
    def rerank(
        self, 
        query: str, 
        documents: List[Document], 
        top_k: int = 5
    ) -> List[Document]:
        if not documents:
            return []
        
        pairs = [[query, doc.page_content] for doc in documents]
        scores = self.model.predict(pairs)
        
        doc_score_pairs = list(zip(documents, scores))
        doc_score_pairs.sort(key=lambda x: x[1], reverse=True)
        
        return [doc for doc, _ in doc_score_pairs[:top_k]]
