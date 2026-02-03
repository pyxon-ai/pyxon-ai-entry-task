import weaviate
from weaviate.classes.init import Auth
from helpers.config import get_settings
import logging

logger = logging.getLogger('uvicorn.error')

class WeaviateClient:
    
    def __init__(self):
        settings = get_settings()
        
        self.client = weaviate.connect_to_weaviate_cloud(
            cluster_url=f"https://{settings.WEAVIATE_URL}",
            auth_credentials=Auth.api_key(settings.WEAVIATE_API_KEY)
        )
        
        self.collection_name = "DocumentChunk"
        self._ensure_collection()
    
    def _ensure_collection(self):
        try:
            if not self.client.collections.exists(self.collection_name):
                from weaviate.classes.config import Property, DataType
                
                self.client.collections.create(
                    name=self.collection_name,
                    properties=[
                        Property(name="content", data_type=DataType.TEXT),
                        Property(name="document_id", data_type=DataType.INT),
                        Property(name="chunk_index", data_type=DataType.INT),
                        Property(name="file_name", data_type=DataType.TEXT)
                    ]
                )
                logger.info(f"Created collection: {self.collection_name}")
        except Exception as e:
            logger.warning(f"Collection might already exist: {e}")
    
    def get_collection(self):
        return self.client.collections.get(self.collection_name)
    
    def semantic_search(self, query_vector, limit: int = 10):
        collection = self.get_collection()
        response = collection.query.near_vector(
            near_vector=query_vector,
            limit=limit,
            return_metadata=['distance']
        )
        
        results = []
        for obj in response.objects:
            results.append({
                "uuid": str(obj.uuid),
                "content": obj.properties.get("content"),
                "document_id": obj.properties.get("document_id"),
                "chunk_index": obj.properties.get("chunk_index"),
                "file_name": obj.properties.get("file_name"),
                "distance": obj.metadata.distance if hasattr(obj.metadata, 'distance') else None
            })
        
        return results
    
    def close(self):
        self.client.close()

weaviate_client = WeaviateClient()
