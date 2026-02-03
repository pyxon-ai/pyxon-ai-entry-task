from .BaseController import BaseController
from .FixedController import FixedController
import cohere
from typing import List, Dict, Any
import numpy as np


class SemanticController(BaseController):
    
    def __init__(self, similarity_threshold: float = 0.5):
        super().__init__()
        self.fixed_controller = FixedController()
        self.similarity_threshold = similarity_threshold
        self.cohere_client = cohere.Client(self.app_settings.COHERE_API_KEY)
    
    def get_embeddings(self, texts: List[str]) -> np.ndarray:
        response = self.cohere_client.embed(
            texts=texts,
            model='embed-multilingual-v3.0',
            input_type='search_document',
            embedding_types=['float']
        )
        embeddings = np.array(response.embeddings.float)
        return embeddings
    
    def calculate_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        similarity = np.dot(embedding1, embedding2) / (np.linalg.norm(embedding1) * np.linalg.norm(embedding2))
        return float(similarity)
    
    def merge_chunks(self, chunk1: Any, chunk2: Any) -> Any:
        merged_content = chunk1.page_content + "\n" + chunk2.page_content
        merged_metadata = chunk1.metadata.copy()
        merged_metadata['merged'] = True
        merged_metadata['original_chunks'] = 2
        
        from langchain_core.documents import Document
        merged_chunk = Document(
            page_content=merged_content,
            metadata=merged_metadata
        )
        return merged_chunk
    
    def semantic_chunk(self, file_content: list, chunk_size: int = 500, 
                      overlap_size: int = 25) -> List[Any]:
        initial_chunks = self.fixed_controller.process_file_content(
            file_content=file_content,
            chunk_size=chunk_size,
            overlap_size=overlap_size
        )
        
        if not initial_chunks or len(initial_chunks) <= 1:
            return initial_chunks
        
        chunk_texts = [chunk.page_content for chunk in initial_chunks]
        embeddings = self.get_embeddings(chunk_texts)
        
        merged_chunks = []
        i = 0
        
        while i < len(initial_chunks):
            current_chunk = initial_chunks[i]
            current_embedding = embeddings[i]
            
            if i + 1 < len(initial_chunks):
                next_chunk = initial_chunks[i + 1]
                next_embedding = embeddings[i + 1]
                similarity = self.calculate_similarity(current_embedding, next_embedding)
                
                if similarity >= self.similarity_threshold:
                    merged_chunk = self.merge_chunks(current_chunk, next_chunk)
                    merged_chunks.append(merged_chunk)
                    i += 2
                else:
                    merged_chunks.append(current_chunk)
                    i += 1
            else:
                merged_chunks.append(current_chunk)
                i += 1
        
        return merged_chunks
