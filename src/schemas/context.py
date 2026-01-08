"""DTOs for Context & Values domain"""
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import List, Optional
from uuid import UUID
from datetime import datetime


class NominalValueItemDTO(BaseModel):
    """Single nominal value mapping"""
    raw: str = Field(..., min_length=1, max_length=255, description="Raw database value")
    label: str = Field(..., min_length=1, max_length=255, description="Human-readable label")


class NominalValueCreateDTO(BaseModel):
    """DTO for creating nominal values"""
    column_id: UUID = Field(..., description="Column UUID")
    values: List[NominalValueItemDTO] = Field(..., min_length=1, description="List of value mappings")
    
    @classmethod
    def validate_values(cls, v: List[NominalValueItemDTO]) -> List[NominalValueItemDTO]:
        """Validate no duplicate raw values"""
        raw_values = [item.raw for item in v]
        if len(raw_values) != len(set(raw_values)):
            raise ValueError("Duplicate raw values are not allowed")
        return v


class NominalValueUpdateDTO(BaseModel):
    """DTO for updating nominal value"""
    value_raw: Optional[str] = Field(None, min_length=1, max_length=255)
    value_label: Optional[str] = Field(None, min_length=1, max_length=255)


class NominalValueResponseDTO(BaseModel):
    """DTO for nominal value response"""
    id: UUID
    column_id: UUID
    value_raw: str
    value_label: str
    created_at: datetime
    updated_at: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)


class ContextRuleDTO(BaseModel):
    """DTO for creating a context rule"""
    column_id: UUID = Field(..., description="Column UUID")
    rule_text: str = Field(..., min_length=1, description="Business rule text")
    
    @field_validator('rule_text')
    @classmethod
    def validate_rule_text(cls, v: str) -> str:
        """Validate rule text is not empty"""
        if not v.strip():
            raise ValueError("Rule text cannot be empty")
        return v.strip()


class ContextRuleUpdateDTO(BaseModel):
    """DTO for updating context rule"""
    rule_text: Optional[str] = Field(None, min_length=1)
    
    @field_validator('rule_text')
    @classmethod
    def validate_rule_text(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("Rule text cannot be empty")
        return v.strip() if v else v


class ContextRuleResponseDTO(BaseModel):
    """DTO for context rule response"""
    id: UUID
    column_id: UUID
    rule_text: str
    created_at: datetime
    updated_at: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)
