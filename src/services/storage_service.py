from .weaviate_client import weaviate_client
from .supabase_client import supabase_client
import cohere
from helpers.config import get_settings
import uuid
import logging
from typing import List, Any

logger = logging.getLogger('uvicorn.error')

class StorageService:
    
    def __init__(self):
        settings = get_settings()
        self.cohere_client = cohere.Client(settings.COHERE_API_KEY)
        self.weaviate = weaviate_client
        self.supabase = supabase_client
    
    async def store_document(self, file_name: str, strategy: str, chunks: List[Any]) -> dict:
        document_id = None
        
        try:
            document_id = self.supabase.insert_document(file_name, strategy)
            
            chunk_texts = [chunk.page_content for chunk in chunks]
            chunk_uuids = [str(uuid.uuid4()) for _ in chunks]
            
            embeddings_response = self.cohere_client.embed(
                texts=chunk_texts,
                model='embed-multilingual-v3.0',
                input_type='search_document',
                embedding_types=['float']
            )
            embeddings = embeddings_response.embeddings.float
            
            collection = self.weaviate.get_collection()
            with collection.batch.dynamic() as batch:
                for idx, (uuid_str, embedding, chunk) in enumerate(zip(chunk_uuids, embeddings, chunks)):
                    batch.add_object(
                        properties={
                            "content": chunk.page_content,
                            "document_id": document_id,
                            "chunk_index": idx,
                            "file_name": file_name
                        },
                        uuid=uuid_str,
                        vector=embedding
                    )
            
            chunk_records = [
                {
                    "document_id": document_id,
                    "content": chunk.page_content,
                    "vector_id": uuid_str
                }
                for idx, (uuid_str, chunk) in enumerate(zip(chunk_uuids, chunks))
            ]
            self.supabase.bulk_insert_chunks(chunk_records)
            
            return {
                "document_id": document_id,
                "total_chunks": len(chunks),
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Error storing document: {e}")
            
            if document_id:
                try:
                    self.supabase.delete_document(document_id)
                    logger.info(f"Rolled back document {document_id}")
                except Exception as rollback_error:
                    logger.error(f"Rollback failed: {rollback_error}")
            
            raise Exception(f"Failed to store document: {str(e)}")

storage_service = StorageService()
