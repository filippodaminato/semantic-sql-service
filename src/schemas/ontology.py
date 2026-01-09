"""DTOs for Physical Ontology domain"""
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import List, Optional
from uuid import UUID
from datetime import datetime


# Column DTOs
class ColumnCreateDTO(BaseModel):
    """DTO for creating a column"""
    name: str = Field(..., min_length=1, max_length=255, description="Physical column name")
    data_type: str = Field(..., min_length=1, max_length=100, description="SQL data type")
    is_primary_key: bool = Field(default=False, description="Whether this is a primary key")
    slug: Optional[str] = Field(None, max_length=255, description="Unique slug")
    semantic_name: Optional[str] = Field(None, max_length=255, description="Semantic name for the column")
    description: Optional[str] = Field(None, description="Column description")
    context_note: Optional[str] = Field(None, description="Business context note")


class ColumnUpdateDTO(BaseModel):
    """DTO for updating a column"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    semantic_name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    context_note: Optional[str] = None
    is_primary_key: Optional[bool] = None
    data_type: Optional[str] = Field(None, max_length=100)


class ColumnResponseDTO(BaseModel):
    """DTO for column response"""
    id: UUID
    table_id: UUID
    name: str
    slug: str
    semantic_name: Optional[str]
    data_type: str
    is_primary_key: bool
    description: Optional[str]
    context_note: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)


# Table DTOs
class TableCreateDTO(BaseModel):
    """DTO for deep creating a table with columns"""
    datasource_id: UUID = Field(..., description="Datasource UUID")
    physical_name: str = Field(..., min_length=1, max_length=255, description="Physical table name")
    slug: Optional[str] = Field(None, max_length=255, description="Unique slug")
    semantic_name: str = Field(..., min_length=1, max_length=255, description="Semantic table name")
    description: Optional[str] = Field(None, description="Table description")
    ddl_context: Optional[str] = Field(None, description="DDL CREATE TABLE statement")
    columns: Optional[List[ColumnCreateDTO]] = Field(default_factory=list, description="Columns to create")
    
    @field_validator('physical_name')
    @classmethod
    def validate_physical_name(cls, v: str) -> str:
        """Validate physical name doesn't contain spaces"""
        if ' ' in v:
            raise ValueError("Physical name cannot contain spaces")
        return v


class TableResponseDTO(BaseModel):
    """DTO for table response"""
    id: UUID
    datasource_id: UUID
    physical_name: str
    slug: str
    semantic_name: str
    description: Optional[str]
    ddl_context: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    columns: List[ColumnResponseDTO] = []
    
    model_config = ConfigDict(from_attributes=True)


class TableUpdateDTO(BaseModel):
    """DTO for updating a table"""
    semantic_name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    ddl_context: Optional[str] = None


# Relationship DTOs
class RelationshipCreateDTO(BaseModel):
    """DTO for creating a relationship"""
    source_column_id: UUID = Field(..., description="Source column UUID")
    target_column_id: UUID = Field(..., description="Target column UUID")
    relationship_type: str = Field(
        ...,
        pattern="^(ONE_TO_ONE|ONE_TO_MANY|MANY_TO_MANY)$",
        description="Type of relationship"
    )
    is_inferred: bool = Field(default=False, description="Whether relationship is inferred")
    description: Optional[str] = Field(None, description="Semantic description of the relationship")


class RelationshipUpdateDTO(BaseModel):
    """DTO for updating a relationship"""
    relationship_type: Optional[str] = Field(
        None,
        pattern="^(ONE_TO_ONE|ONE_TO_MANY|MANY_TO_MANY)$"
    )
    is_inferred: Optional[bool] = None
    description: Optional[str] = None


class RelationshipResponseDTO(BaseModel):
    """DTO for relationship response"""
    id: UUID
    source_column_id: UUID
    target_column_id: UUID
    relationship_type: str
    is_inferred: bool
    description: Optional[str]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class RelationshipWithContextDTO(BaseModel):
    """DTO for relationship with source/target table context"""
    id: UUID
    source_column_id: UUID
    source_column_name: str
    source_table_id: UUID
    source_table_name: str
    target_column_id: UUID
    target_column_name: str
    target_table_id: UUID
    target_table_name: str
    relationship_type: str
    is_inferred: bool
    description: Optional[str]
    created_at: datetime


class TableFullResponseDTO(BaseModel):
    """DTO for table with columns and all relationships"""
    id: UUID
    datasource_id: UUID
    physical_name: str
    slug: str
    semantic_name: str
    description: Optional[str]
    ddl_context: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    columns: List[ColumnResponseDTO] = []
    outgoing_relationships: List[RelationshipWithContextDTO] = []
    incoming_relationships: List[RelationshipWithContextDTO] = []
    
    model_config = ConfigDict(from_attributes=True)

