"""
Pydantic schemas for the Discovery API Suite.

These schemas define the complete response structures for discovery/search endpoints.
All entities return their full data, not just basic fields.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Any, Literal
from uuid import UUID
from datetime import datetime

# =============================================================================
# 2. Datasource & Memory Level
# =============================================================================

class DiscoverySearchRequest(BaseModel):
    """Request schema for discovery searches."""
    query: str
    limit: Optional[int] = 10

class DatasourceSearchResult(BaseModel):
    """Complete datasource information returned by search."""
    id: UUID
    slug: str
    name: str
    description: Optional[str] = None
    engine: str  # SQL engine type (postgres, bigquery, etc.)
    context_signature: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class GoldenSQLSearchRequest(BaseModel):
    """Request schema for Golden SQL search."""
    query: str
    datasource_slug: Optional[str] = None
    limit: Optional[int] = 10

class GoldenSQLResult(BaseModel):
    """Golden SQL example result."""
    id: UUID
    datasource_id: UUID
    prompt: str  # prompt_text
    sql: str  # sql_query
    complexity: int
    verified: bool
    score: float  # Search relevance score
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

# =============================================================================
# 3. Physical Schema Level
# =============================================================================

class TableSearchRequest(BaseModel):
    """Request schema for table search."""
    query: str
    datasource_slug: Optional[str] = None
    limit: Optional[int] = 10

class TableSearchResult(BaseModel):
    """Complete table information returned by search."""
    id: UUID
    datasource_id: UUID
    slug: str
    physical_name: str
    semantic_name: str
    description: Optional[str] = None
    ddl_context: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class ColumnSearchRequest(BaseModel):
    """Request schema for column search."""
    query: str
    datasource_slug: Optional[str] = None
    table_slug: Optional[str] = None
    limit: Optional[int] = 10

class ColumnSearchResult(BaseModel):
    """Complete column information returned by search."""
    id: UUID
    table_id: UUID
    table_slug: str  # Flattened for context
    slug: str
    name: str  # Physical column name
    semantic_name: Optional[str] = None
    data_type: str  # type field
    is_primary_key: bool
    description: Optional[str] = None
    context_note: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class EdgeSearchRequest(BaseModel):
    """Request schema for relationship/edge search."""
    query: str
    datasource_slug: Optional[str] = None
    table_slug: Optional[str] = None
    limit: Optional[int] = 10

class EdgeSearchResult(BaseModel):
    """Complete relationship/edge information returned by search."""
    id: UUID
    source_column_id: UUID
    target_column_id: UUID
    source: str  # Format: table.column (flattened for convenience)
    target: str  # Format: table.column (flattened for convenience)
    relationship_type: str  # ONE_TO_ONE, ONE_TO_MANY, MANY_TO_MANY
    is_inferred: bool
    description: Optional[str] = None
    context_note: Optional[str] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# =============================================================================
# 4. Semantic & Logic Level
# =============================================================================

class MetricSearchRequest(BaseModel):
    """Request schema for metric search."""
    query: str
    datasource_slug: Optional[str] = None
    limit: Optional[int] = 10

class MetricSearchResult(BaseModel):
    """Complete metric information returned by search."""
    id: UUID
    datasource_id: Optional[UUID] = None
    slug: str
    name: str
    description: Optional[str] = None
    calculation_sql: str  # sql_snippet
    required_tables: Optional[List[str]] = None  # List of table IDs as strings
    filter_condition: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class SynonymSearchRequest(BaseModel):
    """Request schema for synonym search."""
    query: str
    datasource_slug: Optional[str] = None
    limit: Optional[int] = 10

class SynonymSearchResult(BaseModel):
    """Complete synonym information returned by search."""
    id: UUID
    term: str
    target_id: UUID
    target_type: str  # TABLE, COLUMN, METRIC, VALUE
    maps_to_slug: str  # Resolved slug of target entity (if available)
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class ContextRuleSearchRequest(BaseModel):
    """Request schema for context rule search."""
    query: str
    datasource_slug: Optional[str] = None
    table_slug: Optional[str] = None
    limit: Optional[int] = 10

class ContextRuleSearchResult(BaseModel):
    """Complete context rule information returned by search."""
    id: UUID
    column_id: UUID
    slug: str
    rule_text: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

# =============================================================================
# 5. Value Level
# =============================================================================

class LowCardinalityValueSearchRequest(BaseModel):
    """Request schema for low cardinality value search."""
    query: str
    datasource_slug: Optional[str] = None
    table_slug: Optional[str] = None
    column_slug: Optional[str] = None
    limit: Optional[int] = 10

class LowCardinalityValueSearchResult(BaseModel):
    """Complete low cardinality value information returned by search."""
    id: UUID
    column_id: UUID
    column_slug: str  # Flattened for context
    table_slug: str  # Flattened for context
    value_raw: str
    value_label: Optional[str] = None  # label
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)
