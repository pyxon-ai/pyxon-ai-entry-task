from supabase import create_client, Client
from helpers.config import get_settings
import logging
from typing import List, Dict, Any

logger = logging.getLogger('uvicorn.error')

class SupabaseClient:
    
    def __init__(self):
        settings = get_settings()
        self.client: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_API_KEY
        )
    
    def insert_document(self, file_name: str, strategy_used: str) -> int:
        data = {
            "file_name": file_name,
            "strategy_used": strategy_used
        }
        response = self.client.table("documents").insert(data).execute()
        return response.data[0]["id"]
    
    def bulk_insert_chunks(self, chunks: List[Dict[str, Any]]) -> None:
        self.client.table("chunks").insert(chunks).execute()
    
    def delete_document(self, document_id: int) -> None:
        self.client.table("documents").delete().eq("id", document_id).execute()
    
    def advanced_search(
        self,
        content: str = None,
        file_name: str = None,
        strategy: str = None,
        document_id: int = None,
        from_date: str = None,
        to_date: str = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        query = self.client.table("chunks").select(
            "*, documents(id, file_name, strategy_used, created_at)"
        )
        
        if content:
            query = query.ilike("content", f"%{content}%")
        
        if document_id:
            query = query.eq("document_id", document_id)
        
        if file_name:
            query = query.filter("documents.file_name", "ilike", f"%{file_name}%")
        
        if strategy:
            query = query.filter("documents.strategy_used", "ilike", f"%{strategy}%")
        
        if from_date:
            query = query.filter("documents.created_at", "gte", from_date)
        
        if to_date:
            query = query.filter("documents.created_at", "lte", to_date)
        
        response = query.limit(limit).execute()
        return response.data
    
    def get_all_documents(self, limit: int = 50) -> List[Dict[str, Any]]:
        response = self.client.table("documents").select("*").order("created_at", desc=True).limit(limit).execute()
        return response.data

supabase_client = SupabaseClient()
