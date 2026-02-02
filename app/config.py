from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional, Union


class Settings(BaseSettings):
    """Application configuration settings"""
    
    # Application
    app_name: str = "Pyxon AI Document Parser"
    app_version: str = "1.0.0"
    debug: bool = True
    
    # Database
    database_url: str
    postgres_user: str = "pyxon_user"
    postgres_password: str = "secure_password_here"
    postgres_db: str = "pyxon_rag"
    
    # Vector Database
    chroma_persist_directory: str = "./chroma_db"
    
    # LLM API Keys
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    
    # Embedding Model
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    
    # Chunking Configuration
    default_chunk_size: int = 512
    default_chunk_overlap: int = 50
    max_file_size_mb: int = 50
    
    # Upload Directory
    upload_dir: str = "./uploads"
    
    # CORS
    allowed_origins: Union[str, list] = ["http://localhost:3000", "http://localhost:8000"]
    
    @field_validator('allowed_origins', mode='before')
    @classmethod
    def parse_allowed_origins(cls, v):
        """Parse comma-separated string into list"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


settings = Settings()
