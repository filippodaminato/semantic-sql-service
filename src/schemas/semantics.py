"""DTOs for Business Semantics domain"""
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import List, Optional
from uuid import UUID
from datetime import datetime


class MetricCreateDTO(BaseModel):
    """DTO for creating a semantic metric"""
    name: str = Field(..., min_length=1, max_length=255, description="Metric name")
    description: Optional[str] = Field(None, description="Business description")
    sql_expression: str = Field(..., min_length=1, description="SQL calculation expression")
    required_table_ids: List[UUID] = Field(default_factory=list, description="Required table UUIDs")
    filter_condition: Optional[str] = Field(None, description="Optional filter condition")
    
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate metric name is unique-friendly"""
        if not v.strip():
            raise ValueError("Metric name cannot be empty")
        return v.strip()


class MetricUpdateDTO(BaseModel):
    """DTO for updating a metric"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    sql_expression: Optional[str] = Field(None, min_length=1)
    required_table_ids: Optional[List[UUID]] = None
    filter_condition: Optional[str] = None


class MetricResponseDTO(BaseModel):
    """DTO for metric response"""
    id: UUID
    name: str
    description: Optional[str]
    calculation_sql: str
    required_tables: Optional[List[str]]
    filter_condition: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)


class SynonymBulkDTO(BaseModel):
    """DTO for bulk creating synonyms"""
    target_id: UUID = Field(..., description="Target entity UUID")
    target_type: str = Field(
        ...,
        pattern="^(TABLE|COLUMN|METRIC|VALUE)$",
        description="Type of target entity"
    )
    terms: List[str] = Field(..., min_length=1, description="List of synonym terms")
    
    @field_validator('terms')
    @classmethod
    def validate_terms(cls, v: List[str]) -> List[str]:
        """Validate terms are not empty"""
        if not v:
            raise ValueError("At least one term is required")
        # Filter empty strings and strip
        cleaned = [t.strip() for t in v if t and t.strip()]
        if not cleaned:
            raise ValueError("At least one non-empty term is required")
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("Duplicate terms are not allowed")
        return cleaned


class SynonymCreateDTO(BaseModel):
    """DTO for creating a single synonym"""
    term: str = Field(..., min_length=1)
    target_id: UUID = Field(..., description="Target entity UUID")
    target_type: str = Field(
        ...,
        pattern="^(TABLE|COLUMN|METRIC|VALUE)$",
        description="Type of target entity"
    )

    @field_validator('term')
    @classmethod
    def validate_term(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Term cannot be empty")
        return v.strip()


class SynonymUpdateDTO(BaseModel):
    """DTO for updating a synonym"""
    term: Optional[str] = Field(None, min_length=1)
    target_id: Optional[UUID] = None
    target_type: Optional[str] = Field(
        None,
        pattern="^(TABLE|COLUMN|METRIC|VALUE)$"
    )

    @field_validator('term')
    @classmethod
    def validate_term(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("Term cannot be empty")
        return v.strip() if v else v


class SynonymResponseDTO(BaseModel):
    """DTO for synonym response"""
    id: UUID
    term: str
    target_type: str
    target_id: UUID
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
