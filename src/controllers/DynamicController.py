from .BaseController import BaseController
from .FixedController import FixedController
from .SemanticController import SemanticController
import google.generativeai as genai
from typing import List, Any
import logging

logger = logging.getLogger('uvicorn.error')


class DynamicController(BaseController):
    """
    Intelligent chunking controller that uses Gemini AI to decide
    whether to apply fixed-size or semantic chunking based on document content.
    """
    
    def __init__(self, project_id: str):
        super().__init__()
        self.project_id = project_id
        self.fixed_controller = FixedController(project_id=project_id)
        self.semantic_controller = SemanticController(project_id=project_id)
        
        genai.configure(api_key=self.app_settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
    
    def analyze_document(self, preview_text: str) -> str:
        try:
            prompt = f"""Analyze this document preview and decide the best chunking strategy.

Document Preview (first 2000 characters):
{preview_text}

Choose ONE of the following:
- FIXED: If the document has distinct sections or should be split at regular intervals
- SEMANTIC: If the document has continuous narrative, related paragraphs.

Respond with ONLY one word: either "FIXED" or "SEMANTIC"
"""
            
            response = self.model.generate_content(prompt)
            decision = response.text.strip().upper()
            
            if "SEMANTIC" in decision:
                return "SEMANTIC"
            elif "FIXED" in decision:
                return "FIXED"
            else:
                logger.warning(f"Gemini returned unexpected response: {decision}. Defaulting to FIXED.")
                return "FIXED"
                
        except Exception as e:
            logger.error(f"Error analyzing document with Gemini: {e}. Defaulting to FIXED chunking.")
            return "FIXED"
    
    def process_document(self, file_id: str, chunk_size: int = 500, 
                        overlap_size: int = 25) -> dict:
        file_content = self.fixed_controller.get_file_content(file_id=file_id)
        
        full_text = "\n".join([doc.page_content for doc in file_content])
        preview_text = full_text[:2000]
        
        strategy = self.analyze_document(preview_text)
        
        if strategy == "SEMANTIC":
            chunks = self.semantic_controller.semantic_chunk(
                file_id=file_id,
                chunk_size=chunk_size,
                overlap_size=overlap_size
            )
        else:
            chunks = self.fixed_controller.process_file_content(
                file_content=file_content,
                file_id=file_id,
                chunk_size=chunk_size,
                overlap_size=overlap_size
            )
        
        return {
            "strategy": strategy,
            "chunks": chunks
        }
