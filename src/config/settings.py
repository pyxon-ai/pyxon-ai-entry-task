"""Application settings and configuration."""

import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = Field(
        default="postgresql://pyxon:pyxon@localhost:5432/pyxon_docs",
        description="PostgreSQL database connection URL"
    )
    pgvector_extension: bool = True

    @field_validator('database_url')
    def validate_database_url(cls, v):
        """Validate database URL format."""
        if not v or not v.startswith(('postgresql://', 'postgresql+')):
            raise ValueError("DATABASE_URL must be a valid PostgreSQL connection string")
        return v

    # API Keys
    openai_api_key: str = Field(default="", description="OpenAI API key for LLM")
    anthropic_api_key: str = Field(default="", description="Anthropic API key for LLM")

    # Models
    embedding_model: str = "BAAI/bge-m3"
    llm_model: str = "gpt-4o"
    chunking_strategy: str = "auto"

    # Processing
    max_file_size: int = Field(
        default=10 * 1024 * 1024,
        description="Maximum file size in bytes (default: 10MB)"
    )
    chunk_size: int = 512
    chunk_overlap: int = 50
    batch_size: int = 32

    @field_validator('max_file_size')
    def validate_max_file_size(cls, v):
        """Validate max file size."""
        if v < 1024 or v > 100 * 1024 * 1024:  # Min 1KB, Max 100MB
            raise ValueError("max_file_size must be between 1KB and 100MB")
        return v

    @field_validator('chunk_size')
    def validate_chunk_size(cls, v):
        """Validate chunk size."""
        if v < 100 or v > 2000:
            raise ValueError("chunk_size must be between 100 and 2000")
        return v

    # Demo
    demo_port: int = Field(default=8000, description="Port for demo server")
    demo_host: str = Field(default="0.0.0.0", description="Host for demo server")

    @field_validator('demo_port')
    def validate_demo_port(cls, v):
        """Validate demo port."""
        if v < 1 or v > 65535:
            raise ValueError("demo_port must be between 1 and 65535")
        return v

    def validate_settings(self):
        """Validate all settings and log warnings."""
        logger.info("Validating application settings...")
        
        # Check for required API keys
        if not self.openai_api_key and not self.anthropic_api_key:
            logger.warning(
                "No LLM API keys configured. Query functionality will be limited. "
                "Set OPENAI_API_KEY or ANTHROPIC_API_KEY in .env file."
            )
        
        # Check database URL
        if "user:password" in self.database_url:
            logger.warning(
                "Using default database credentials. Please update DATABASE_URL in .env file."
            )
        
        logger.info("Settings validated successfully")
        return True


settings = Settings()
settings.validate_settings()
