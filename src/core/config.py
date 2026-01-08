"""Application configuration"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""
    
    # Database
    database_url: str = Field(
        default="postgresql://semantic_user:semantic_pass@db:5432/semantic_sql",
        alias="DATABASE_URL"
    )
    
    # OpenAI
    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    openai_model: str = Field(
        default="text-embedding-3-small",
        alias="OPENAI_MODEL"
    )
    
    # Application
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    
    # Embedding dimensions (for text-embedding-3-small)
    embedding_dimensions: int = 1536
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
