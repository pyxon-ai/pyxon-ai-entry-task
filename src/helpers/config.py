import os

_HAS_STREAMLIT = False
_IN_STREAMLIT = False

try:
    import streamlit as st
    from streamlit.runtime.scriptrunner import get_script_run_ctx
    _HAS_STREAMLIT = True
    _IN_STREAMLIT = get_script_run_ctx() is not None
except:
    pass

def _is_streamlit_cloud():
    if not _HAS_STREAMLIT or not _IN_STREAMLIT:
        return False
    try:
        return len(st.secrets) > 0
    except:
        return False

class Settings:
    def __init__(self):
        if _is_streamlit_cloud():
            self._load_from_streamlit()
        else:
            self._load_from_env()
    
    def _load_from_streamlit(self):
        import streamlit as st
        self.APP_NAME = st.secrets.get("APP_NAME", "AI-Parser")
        self.APP_VERSION = st.secrets.get("APP_VERSION", "0.1")
        self.GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
        self.COHERE_API_KEY = st.secrets["COHERE_API_KEY"]
        self.WEAVIATE_API_KEY = st.secrets["WEAVIATE_API_KEY"]
        self.WEAVIATE_URL = st.secrets["WEAVIATE_URL"]
        self.SUPABASE_API_KEY = st.secrets["SUPABASE_API_KEY"]
        self.SUPABASE_URL = st.secrets["SUPABASE_URL"]
        self.DATABASE_URL = st.secrets["DATABASE_URL"]
        
        file_types = st.secrets.get("FILE_ALLOWED_TYPES", '["text/plain", "application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]')
        if isinstance(file_types, str):
            import json
            self.FILE_ALLOWED_TYPES = json.loads(file_types)
        else:
            self.FILE_ALLOWED_TYPES = list(file_types)
        
        self.FILE_MAX_SIZE = int(st.secrets.get("FILE_MAX_SIZE", 10485760))
        self.FILE_DEFAULT_CHUNK_SIZE = int(st.secrets.get("FILE_DEFAULT_CHUNK_SIZE", 512000))
    
    def _load_from_env(self):
        from pydantic_settings import BaseSettings
        
        class EnvSettings(BaseSettings):
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
        
        env = EnvSettings()
        self.APP_NAME = env.APP_NAME
        self.APP_VERSION = env.APP_VERSION
        self.GEMINI_API_KEY = env.GEMINI_API_KEY
        self.COHERE_API_KEY = env.COHERE_API_KEY
        self.WEAVIATE_API_KEY = env.WEAVIATE_API_KEY
        self.WEAVIATE_URL = env.WEAVIATE_URL
        self.SUPABASE_API_KEY = env.SUPABASE_API_KEY
        self.SUPABASE_URL = env.SUPABASE_URL
        self.DATABASE_URL = env.DATABASE_URL
        self.FILE_ALLOWED_TYPES = env.FILE_ALLOWED_TYPES
        self.FILE_MAX_SIZE = env.FILE_MAX_SIZE
        self.FILE_DEFAULT_CHUNK_SIZE = env.FILE_DEFAULT_CHUNK_SIZE

_settings = None

def get_settings():
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
