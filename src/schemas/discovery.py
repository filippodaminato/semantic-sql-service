"""
Pydantic schemas for the Discovery API Suite.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Any, Literal
from uuid import UUID

# =============================================================================
# 2. Datasource & Memory Level
# =============================================================================

class DiscoverySearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 10

class DatasourceSearchResult(BaseModel):
    slug: str
    description: Optional[str] = None
    name: Optional[str] = None # Added for completeness

class GoldenSQLSearchRequest(BaseModel):
    query: str
    datasource_slug: Optional[str] = None
    limit: Optional[int] = 10

class GoldenSQLResult(BaseModel):
    prompt: str
    sql: str
    score: float

# =============================================================================
# 3. Physical Schema Level
# =============================================================================

class TableSearchRequest(BaseModel):
    query: str
    datasource_slug: Optional[str] = None
    limit: Optional[int] = 10

class TableSearchResult(BaseModel):
    slug: str
    semantic_name: str
    description: Optional[str] = None

class ColumnSearchRequest(BaseModel):
    query: str
    datasource_slug: Optional[str] = None
    table_slug: Optional[str] = None
    limit: Optional[int] = 10

class ColumnSearchResult(BaseModel):
    table_slug: str # Flattened for context
    slug: str
    type: str
    description: Optional[str] = None

class EdgeSearchRequest(BaseModel):
    query: str
    datasource_slug: Optional[str] = None
    table_slug: Optional[str] = None
    limit: Optional[int] = 10

class EdgeSearchResult(BaseModel):
    source: str # Format: table.column
    target: str # Format: table.column
    type: str # MANY_TO_ONE, etc.
    description: Optional[str] = None

# =============================================================================
# 4. Semantic & Logic Level
# =============================================================================

class MetricSearchRequest(BaseModel):
    query: str
    datasource_slug: Optional[str] = None
    limit: Optional[int] = 10

class MetricSearchResult(BaseModel):
    slug: str
    name: str # The human readable name
    sql_snippet: str
    tables_involved: List[str]

class SynonymSearchRequest(BaseModel):
    query: str
    datasource_slug: Optional[str] = None
    limit: Optional[int] = 10

class SynonymSearchResult(BaseModel):
    term: str
    maps_to_slug: str
    target_type: str # TABLE, COLUMN, etc.

class ContextRuleSearchRequest(BaseModel):
    query: str
    datasource_slug: Optional[str] = None
    table_slug: Optional[str] = None
    limit: Optional[int] = 10

class ContextRuleSearchResult(BaseModel):
    slug: str
    rule_text: str

# =============================================================================
# 5. Value Level
# =============================================================================

class LowCardinalityValueSearchRequest(BaseModel):
    query: str
    datasource_slug: Optional[str] = None
    table_slug: Optional[str] = None
    column_slug: Optional[str] = None
    limit: Optional[int] = 10

class LowCardinalityValueSearchResult(BaseModel):
    value_raw: str
    label: Optional[str] = None
    column_slug: str
    table_slug: str
