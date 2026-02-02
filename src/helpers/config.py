from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):

    APP_NAME: str
    APP_VERSION: str
    GEMINI_API_KEY: str
    COHERE_API_KEY: str

    WEAVIATE_API_KEY: str
    WEAVIATE_URL: str
    SUPABASE_API_KEY: str
    SUPABASE_URL: str
    DATABASE_URL: str

    FILE_ALLOWED_TYPES: list
    FILE_MAX_SIZE: int
    FILE_DEFAULT_CHUNK_SIZE: int

    class Config:
        env_file = ".env"

def get_settings():
    return Settings()
