from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):

    APP_NAME: str
    APP_VERSION: str
    GEMINI_API_KEY: str
    COHERE_API_KEY: str

    weaviate_api_key: str
    weaviate_url: str
    supabase_api_key: str
    supabase_url: str
    database_url: str

    FILE_ALLOWED_TYPES: list
    FILE_MAX_SIZE: int
    FILE_DEFAULT_CHUNK_SIZE: int

    class Config:
        env_file = ".env"

def get_settings():
    return Settings()