"""
Application configuration management using Pydantic Settings.

This module provides centralized configuration management with:
- Environment variable support
- Type validation
- Default values
- .env file support

All configuration values can be overridden via environment variables.
The .env file is automatically loaded if present in the project root.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """
    Application settings with environment variable support.
    
    All settings can be configured via environment variables or .env file.
    Settings are validated on instantiation using Pydantic.
    
    Attributes:
        database_url: PostgreSQL connection string
        openai_api_key: OpenAI API key (required)
        openai_model: OpenAI model for embeddings
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        environment: Application environment (development, staging, production)
        embedding_dimensions: Vector dimension for embeddings
    
    Example:
        ```python
        from .core.config import settings
        print(settings.database_url)
        ```
    
    Environment Variables:
        DATABASE_URL: PostgreSQL connection string
        OPENAI_API_KEY: OpenAI API key (required)
        OPENAI_MODEL: OpenAI model name (default: text-embedding-3-small)
        LOG_LEVEL: Logging level (default: INFO)
        ENVIRONMENT: Environment name (default: development)
    """
    
    # Database Configuration
    database_url: str = Field(
        default="postgresql://semantic_user:semantic_pass@db:5432/semantic_sql",
        alias="DATABASE_URL",
        description="PostgreSQL connection string in format: "
                   "postgresql://user:password@host:port/database"
    )
    
    # OpenAI Configuration
    openai_api_key: str = Field(
        ...,
        alias="OPENAI_API_KEY",
        description="OpenAI API key for generating embeddings. Required."
    )
    
    openai_model: str = Field(
        default="text-embedding-3-small",
        alias="OPENAI_MODEL",
        description="OpenAI model for embeddings. "
                   "text-embedding-3-small provides 1536 dimensions."
    )
    
    # Application Configuration
    log_level: str = Field(
        default="INFO",
        alias="LOG_LEVEL",
        description="Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL"
    )
    
    environment: str = Field(
        default="development",
        alias="ENVIRONMENT",
        description="Application environment: development, staging, production"
    )
    
    # Embedding Configuration
    # Note: This must match the dimensions of the selected OpenAI model
    # text-embedding-3-small: 1536 dimensions
    # text-embedding-3-large: 3072 dimensions
    embedding_dimensions: int = Field(
        default=1536,
        description="Vector dimensions for embeddings. "
                   "Must match the selected OpenAI model dimensions."
    )
    
    class Config:
        """
        Pydantic configuration for Settings.
        
        env_file: Loads .env file from project root if present
        case_sensitive: Environment variable names are case-insensitive
        """
        env_file = ".env"
        case_sensitive = False


# Global settings instance
# Import this in other modules: from .core.config import settings
settings = Settings()
