"""DTOs for Datasource management"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime


class DatasourceCreateDTO(BaseModel):
    """DTO for creating a datasource"""
    name: str = Field(..., min_length=1, max_length=255, description="Datasource name")
    slug: Optional[str] = Field(None, min_length=1, max_length=255, description="Unique slug (auto-generated if empty)")
    description: Optional[str] = Field(None, description="Description of the datasource")
    engine: str = Field(
        ...,
        pattern="^(postgres|bigquery|snowflake|tsql|mysql)$",
        description="SQL engine type"
    )
    context_signature: Optional[str] = Field(None, description="Context signature for embedding")


class DatasourceUpdateDTO(BaseModel):
    """DTO for updating a datasource"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    slug: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    engine: Optional[str] = Field(
        None,
        pattern="^(postgres|bigquery|snowflake|tsql|mysql)$"
    )
    context_signature: Optional[str] = None


class DatasourceResponseDTO(BaseModel):
    """DTO for datasource response"""
    id: UUID
    name: str
    slug: str
    description: Optional[str]
    engine: str
    context_signature: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)
