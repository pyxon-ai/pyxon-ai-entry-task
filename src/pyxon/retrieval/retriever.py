# src.pyxon.retrieval.retriever

from typing import List
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_pinecone import PineconeVectorStore
from rank_bm25 import BM25Okapi
import numpy as np


class HybridRetriever(BaseRetriever):
    vector_store: PineconeVectorStore  
    bm25_index: BM25Okapi = None
    all_chunks: List[Document] = []
    alpha: float = 0.6
    
    def _get_relevant_documents(self, query: str) -> List[Document]:
        vector_results = self.vector_store.similarity_search_with_score(
            query, k=20
        )
        
        tokenized_query = query.lower().split()
        bm25_scores = self.bm25_index.get_scores(tokenized_query)
        
        top_bm25_indices = np.argsort(bm25_scores)[::-1][:20]
        bm25_results = [(self.all_chunks[i], bm25_scores[i]) for i in top_bm25_indices]
        
        combined_docs = {}
        
        max_vec_score = max(score for _, score in vector_results) if vector_results else 1
        for doc, score in vector_results:
            doc_id = doc.metadata.get('chunk_index', id(doc))
            normalized = 1 - (score / max_vec_score)
            combined_docs[doc_id] = {
                'doc': doc,
                'score': self.alpha * normalized
            }
        
        max_bm25 = max(bm25_scores) if len(bm25_scores) > 0 else 1
        for doc, score in bm25_results:
            doc_id = doc.metadata.get('chunk_index', id(doc))
            normalized = score / max_bm25
            if doc_id in combined_docs:
                combined_docs[doc_id]['score'] += (1 - self.alpha) * normalized
            else:
                combined_docs[doc_id] = {
                    'doc': doc,
                    'score': (1 - self.alpha) * normalized
                }
        
        sorted_docs = sorted(
            combined_docs.values(),
            key=lambda x: x['score'],
            reverse=True
        )
        
        return [item['doc'] for item in sorted_docs[:10]]
    
    def build_bm25_index(self, chunks: List[Document]):
        self.all_chunks = chunks
        tokenized_corpus = [doc.page_content.lower().split() for doc in chunks]
        self.bm25_index = BM25Okapi(tokenized_corpus)