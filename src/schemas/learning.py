"""DTOs for Learning domain"""
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime


class GoldenSQLDTO(BaseModel):
    """DTO for creating golden SQL example"""
    datasource_id: UUID = Field(..., description="Datasource UUID")
    prompt_text: str = Field(..., min_length=1, description="User prompt in natural language")
    sql_query: str = Field(..., min_length=1, description="Correct SQL query")
    complexity: int = Field(default=1, ge=1, le=5, description="Complexity score (1-5)")
    verified: bool = Field(default=True, description="Whether this example is verified")
    
    @field_validator('prompt_text', 'sql_query')
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        """Validate text is not empty"""
        if not v.strip():
            raise ValueError("Text cannot be empty")
        return v.strip()


class GoldenSQLResponseDTO(BaseModel):
    """DTO for golden SQL response"""
    id: UUID
    datasource_id: UUID
    prompt_text: str
    sql_query: str
    complexity_score: int
    verified: bool
    created_at: datetime
    updated_at: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)


class GoldenSQLUpdateDTO(BaseModel):
    """DTO for updating golden SQL example"""
    prompt_text: Optional[str] = Field(None, min_length=1)
    sql_query: Optional[str] = Field(None, min_length=1)
    complexity: Optional[int] = Field(None, ge=1, le=5)
    verified: Optional[bool] = None


class AmbiguityLogCreateDTO(BaseModel):
    """DTO for creating ambiguity log"""
    user_query: str = Field(..., min_length=1, description="User query text")
    detected_ambiguity: Optional[dict] = Field(None, description="JSON details of ambiguity")
    user_resolution: Optional[str] = Field(None, description="User provided resolution")


class AmbiguityLogUpdateDTO(BaseModel):
    """DTO for updating ambiguity log"""
    user_resolution: Optional[str] = Field(None, description="User provided resolution")
    detected_ambiguity: Optional[dict] = None


class AmbiguityLogResponseDTO(BaseModel):
    """DTO for ambiguity log response"""
    id: UUID
    user_query: str
    detected_ambiguity: Optional[dict]
    user_resolution: Optional[str]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class GenerationTraceCreateDTO(BaseModel):
    """DTO for creating generation trace"""
    user_prompt: str = Field(..., min_length=1, description="User original prompt")
    retrieved_context_snapshot: Optional[dict] = Field(None, description="Snapshot of context")
    generated_sql: Optional[str] = Field(None, description="Generated SQL")
    error_message: Optional[str] = Field(None, description="Error message if any")
    user_feedback: Optional[int] = Field(None, ge=-1, le=1, description="User feedback (-1, 0, 1)")


class GenerationTraceUpdateDTO(BaseModel):
    """DTO for updating generation trace"""
    user_feedback: Optional[int] = Field(None, ge=-1, le=1)
    error_message: Optional[str] = None
    generated_sql: Optional[str] = None


class GenerationTraceResponseDTO(BaseModel):
    """DTO for generation trace response"""
    id: UUID
    user_prompt: str
    retrieved_context_snapshot: Optional[dict]
    generated_sql: Optional[str]
    error_message: Optional[str]
    user_feedback: Optional[int]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

