from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):

    APP_NAME: str = "AI-Parser"
    APP_VERSION: str = "0.1"
    GEMINI_API_KEY: str
    COHERE_API_KEY: str

    WEAVIATE_API_KEY: str
    WEAVIATE_URL: str
    SUPABASE_API_KEY: str
    SUPABASE_URL: str
    DATABASE_URL: str

    FILE_ALLOWED_TYPES: list = ["text/plain", "application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
    FILE_MAX_SIZE: int = 10485760
    FILE_DEFAULT_CHUNK_SIZE: int = 512000

    class Config:
        env_file = ".env"

def get_settings():
    try:
        import streamlit as st
        if hasattr(st, 'secrets') and len(st.secrets) > 0:
            return Settings(
                GEMINI_API_KEY=st.secrets.get("GEMINI_API_KEY"),
                COHERE_API_KEY=st.secrets.get("COHERE_API_KEY"),
                WEAVIATE_API_KEY=st.secrets.get("WEAVIATE_API_KEY"),
                WEAVIATE_URL=st.secrets.get("WEAVIATE_URL"),
                SUPABASE_API_KEY=st.secrets.get("SUPABASE_API_KEY"),
                SUPABASE_URL=st.secrets.get("SUPABASE_URL"),
                DATABASE_URL=st.secrets.get("DATABASE_URL")
            )
    except (ImportError, FileNotFoundError):
        pass
    
    return Settings()