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
    
    def search_by_document_name(self, file_name: str, limit: int = 50) -> List[Dict[str, Any]]:
        response = self.client.table("documents").select(
            "id, file_name, strategy_used, created_at"
        ).ilike("file_name", f"%{file_name}%").limit(limit).execute()
        return response.data
    
    def search_by_document_id(self, document_id: int) -> Dict[str, Any]:
        response = self.client.table("documents").select(
            "id, file_name, strategy_used, created_at"
        ).eq("id", document_id).single().execute()
        return response.data
    
    def get_chunks_by_document(self, document_id: int) -> List[Dict[str, Any]]:
        response = self.client.table("chunks").select("*").eq("document_id", document_id).execute()
        return response.data
    
    def get_all_documents(self, limit: int = 50) -> List[Dict[str, Any]]:
        response = self.client.table("documents").select("*").order("created_at", desc=True).limit(limit).execute()
        return response.data

supabase_client = SupabaseClient()
