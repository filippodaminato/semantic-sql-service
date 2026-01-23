"""
Pydantic schemas for the Discovery API Suite.

These schemas define the complete response structures for discovery/search endpoints.
All entities return their full data, not just basic fields.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Any, Literal, Generic, TypeVar
from uuid import UUID
from datetime import datetime
from enum import Enum as PyEnum

# =============================================================================
# 1. Pagination Support
# =============================================================================

T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper for all discovery endpoints."""
    items: List[T] = Field(description="List of results for current page")
    total: int = Field(description="Total number of results across all pages")
    page: int = Field(description="Current page number (1-indexed)")
    limit: int = Field(description="Number of items per page")
    has_next: bool = Field(description="Whether there are more pages")
    has_prev: bool = Field(description="Whether there are previous pages")
    total_pages: int = Field(description="Total number of pages")
    
    model_config = ConfigDict(from_attributes=True)

# =============================================================================
# 2. Datasource & Memory Level
# =============================================================================

class DiscoverySearchRequest(BaseModel):
    """Request schema for discovery searches."""
    query: str
    page: Optional[int] = Field(default=1, ge=1, description="Page number (1-indexed)")
    limit: Optional[int] = Field(default=10, ge=1, le=1000, description="Number of items per page (max 1000)")
    min_ratio_to_best: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Filter results with score < best_score * min_ratio")

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
    score: Optional[float] = None
    
    model_config = ConfigDict(from_attributes=True)

class GoldenSQLSearchRequest(BaseModel):
    """Request schema for Golden SQL search."""
    query: str
    datasource_slug: Optional[str] = None
    page: Optional[int] = Field(default=1, ge=1, description="Page number (1-indexed)")
    limit: Optional[int] = Field(default=10, ge=1, le=1000, description="Number of items per page (max 1000)")
    min_ratio_to_best: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Filter results with score < best_score * min_ratio")

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
    page: Optional[int] = Field(default=1, ge=1, description="Page number (1-indexed)")
    limit: Optional[int] = Field(default=10, ge=1, le=1000, description="Number of items per page (max 1000)")
    min_ratio_to_best: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Filter results with score < best_score * min_ratio")

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
    score: Optional[float] = None
    
    model_config = ConfigDict(from_attributes=True)

class ColumnSearchRequest(BaseModel):
    """Request schema for column search."""
    query: str
    datasource_slug: Optional[str] = None
    table_slug: Optional[str] = None
    page: Optional[int] = Field(default=1, ge=1, description="Page number (1-indexed)")
    limit: Optional[int] = Field(default=10, ge=1, le=1000, description="Number of items per page (max 1000)")
    min_ratio_to_best: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Filter results with score < best_score * min_ratio")

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
    score: Optional[float] = None
    
    model_config = ConfigDict(from_attributes=True)

class EdgeSearchRequest(BaseModel):
    """Request schema for relationship/edge search."""
    query: str
    datasource_slug: Optional[str] = None
    table_slug: Optional[str] = None
    page: Optional[int] = Field(default=1, ge=1, description="Page number (1-indexed)")
    limit: Optional[int] = Field(default=10, ge=1, le=1000, description="Number of items per page (max 1000)")
    min_ratio_to_best: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Filter results with score < best_score * min_ratio")

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
    score: Optional[float] = None
    
    model_config = ConfigDict(from_attributes=True)

# =============================================================================
# 4. Semantic & Logic Level
# =============================================================================

class MetricSearchRequest(BaseModel):
    """Request schema for metric search."""
    query: str
    datasource_slug: Optional[str] = None
    page: Optional[int] = Field(default=1, ge=1, description="Page number (1-indexed)")
    limit: Optional[int] = Field(default=10, ge=1, le=1000, description="Number of items per page (max 1000)")
    min_ratio_to_best: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Filter results with score < best_score * min_ratio")

class MetricSearchResult(BaseModel):
    """Complete metric information returned by search."""
    id: UUID
    datasource_id: Optional[UUID] = None
    slug: str
    name: str
    description: Optional[str] = None
    calculation_sql: str  # sql_snippet
    required_tables: Optional[List[str]] = None  # List of table slugs (resolved from IDs)
    filter_condition: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    score: Optional[float] = None
    
    model_config = ConfigDict(from_attributes=True)

class SynonymSearchRequest(BaseModel):
    """Request schema for synonym search."""
    query: str
    datasource_slug: Optional[str] = None
    page: Optional[int] = Field(default=1, ge=1, description="Page number (1-indexed)")
    limit: Optional[int] = Field(default=10, ge=1, le=1000, description="Number of items per page (max 1000)")
    min_ratio_to_best: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Filter results with score < best_score * min_ratio")

class SynonymSearchResult(BaseModel):
    """Complete synonym information returned by search."""
    id: UUID
    term: str
    target_id: UUID
    target_type: str  # TABLE, COLUMN, METRIC, VALUE
    maps_to_slug: str  # Resolved slug of target entity (if available)
    created_at: datetime
    score: Optional[float] = None
    
    model_config = ConfigDict(from_attributes=True)

class ContextRuleSearchRequest(BaseModel):
    """Request schema for context rule search."""
    query: str
    datasource_slug: Optional[str] = None
    table_slug: Optional[str] = None
    page: Optional[int] = Field(default=1, ge=1, description="Page number (1-indexed)")
    limit: Optional[int] = Field(default=10, ge=1, le=1000, description="Number of items per page (max 1000)")
    min_ratio_to_best: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Filter results with score < best_score * min_ratio")

class ContextRuleSearchResult(BaseModel):
    """Complete context rule information returned by search."""
    id: UUID
    column_id: UUID
    column_slug: str
    table_slug: str
    slug: str
    rule_text: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    score: Optional[float] = None
    
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
    page: Optional[int] = Field(default=1, ge=1, description="Page number (1-indexed)")
    limit: Optional[int] = Field(default=10, ge=1, le=1000, description="Number of items per page (max 1000)")
    min_ratio_to_best: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Filter results with score < best_score * min_ratio")

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
    score: Optional[float] = None
    
    model_config = ConfigDict(from_attributes=True)

# =============================================================================
# 6. Paginated Response Type Aliases
# =============================================================================

# Type aliases for paginated responses (for better type hints and IDE support)
PaginatedDatasourceResponse = PaginatedResponse[DatasourceSearchResult]
PaginatedGoldenSQLResponse = PaginatedResponse[GoldenSQLResult]
PaginatedTableResponse = PaginatedResponse[TableSearchResult]
PaginatedColumnResponse = PaginatedResponse[ColumnSearchResult]
PaginatedEdgeResponse = PaginatedResponse[EdgeSearchResult]
PaginatedMetricResponse = PaginatedResponse[MetricSearchResult]
PaginatedSynonymResponse = PaginatedResponse[SynonymSearchResult]
PaginatedContextRuleResponse = PaginatedResponse[ContextRuleSearchResult]
PaginatedLowCardinalityValueResponse = PaginatedResponse[LowCardinalityValueSearchResult]

# =============================================================================
# 9. Graph Traversal
# =============================================================================

class GraphPathRequest(BaseModel):
    """Request for finding paths between tables."""
    source_table_slug: str
    target_table_slug: str
    datasource_slug: Optional[str] = Field(default=None, description="Optional datasource slug to filter/validate tables")
    max_depth: Optional[int] = Field(default=3, ge=1, le=5, description="Maximum path depth (hops)")
    
class GraphNode(BaseModel):
    """Node in a graph path."""
    table_slug: str
    column_slug: str
    table_name: str
    column_name: str
    
class GraphEdge(BaseModel):
    """Edge in a graph path."""
    source: GraphNode
    target: GraphNode
    relationship_type: str
    description: Optional[str] = None
    
class GraphPathResult(BaseModel):
    """Result containing all valid paths found."""
    source_table: str
    target_table: str
    paths: List[List[GraphEdge]]
    total_paths: int

# =============================================================================
# 10. MCP Support
# =============================================================================

class MCPResponse(BaseModel):
    """Response wrapper for Model Context Protocol (MCP) formatted strings."""
    res: str

# =============================================================================
# 11. Context Resolution (Unified Batch Execution)
# =============================================================================

class ContextSearchEntity(str, PyEnum):
    """Entities supported for context resolution search."""
    # Core
    DATASOURCES = "datasources"
    TABLES = "tables"
    COLUMNS = "columns"
    EDGES = "edges"
    # Semantic
    METRICS = "metrics"
    # Context & Values
    CONTEXT_RULES = "context_rules"
    LOW_CARDINALITY_VALUES = "low_cardinality_values"
    # Learning
    GOLDEN_SQL = "golden_sql"

class ContextSearchItem(BaseModel):
    """Single item in the batch context search request."""
    entity: ContextSearchEntity
    search_text: str
    min_ratio_to_best: Optional[float] = None

class ResolvedColumn(ColumnSearchResult):
    """Column with nested context details."""
    context_rules: List[ContextRuleSearchResult] = []
    nominal_values: List[LowCardinalityValueSearchResult] = []

    model_config = ConfigDict(from_attributes=True)

class ResolvedTable(TableSearchResult):
    """Table with nested columns."""
    columns: List[ResolvedColumn] = []

    model_config = ConfigDict(from_attributes=True)

class ResolvedDatasource(DatasourceSearchResult):
    """Root of the resolved context graph."""
    tables: List[ResolvedTable] = []
    metrics: List[MetricSearchResult] = []
    golden_sqls: List[GoldenSQLResult] = []
    edges: List[EdgeSearchResult] = []

    model_config = ConfigDict(from_attributes=True)

class ContextResolutionResponse(BaseModel):
    """Final response for the resolve-context endpoint."""
    graph: List[ResolvedDatasource]


