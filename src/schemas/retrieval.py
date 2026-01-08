"""
Pydantic schemas for the Retrieval API.

This module defines all Request and Response models for the 6 Retrieval API endpoints:
1. Omni-Search (POST /search)
2. Graph Resolver (POST /graph/expand)
3. Value Validator (POST /values/validate)
4. Schema Inspector (POST /schema/inspect)
5. Wisdom Archive (POST /golden-sql/search)
6. Semantic Explainer (POST /concepts/explain)

These endpoints are designed to be consumed by an external AI Agent (e.g., LangGraph)
for Agentic RAG workflows.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from uuid import UUID
from enum import Enum


# =============================================================================
# ENUMS
# =============================================================================

class EntityType(str, Enum):
    """Types of searchable entities in the semantic layer."""
    DATASOURCE = "DATASOURCE"
    TABLE = "TABLE"
    COLUMN = "COLUMN"
    METRIC = "METRIC"


class RelationshipTypeEnum(str, Enum):
    """Types of relationships between tables/columns."""
    ONE_TO_ONE = "ONE_TO_ONE"
    ONE_TO_MANY = "ONE_TO_MANY"
    MANY_TO_MANY = "MANY_TO_MANY"


# =============================================================================
# 1. OMNI-SEARCH (The Discovery Engine)
# =============================================================================

class SearchFilters(BaseModel):
    """
    Filters for the Omni-Search endpoint.
    Supports both structural drill-down and semantic search.
    """
    entity_types: Optional[List[EntityType]] = Field(
        default=None,
        description="Filter results to specific entity types: DATASOURCE, TABLE, COLUMN, METRIC"
    )
    datasource_slug: Optional[str] = Field(
        default=None,
        description="Restrict search to a specific datasource by its slug"
    )
    parent_id: Optional[UUID] = Field(
        default=None,
        description="ID of a parent entity (Table or Datasource) to get children. "
                    "For drill-down navigation: Datasource -> Tables, Table -> Columns"
    )


class SearchRequest(BaseModel):
    """
    Request body for the unified search endpoint.
    
    Supports two main use cases:
    1. Semantic Search: Provide `query` to find entities by meaning
    2. Drill-Down Navigation: Provide `filters.parent_id` to get children of an entity
    """
    query: Optional[str] = Field(
        default=None,
        min_length=1,
        description="Natural language query for semantic search (e.g., 'Data cancellazione ordine')"
    )
    filters: Optional[SearchFilters] = Field(
        default=None,
        description="Structural filters for narrowing down results"
    )
    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of results to return"
    )


class TableSearchHit(BaseModel):
    """Search result for a TABLE entity with critical rules."""
    type: Literal["TABLE"] = "TABLE"
    id: UUID
    name: str = Field(description="Semantic name of the table")
    physical_name: str = Field(description="Actual table name in the database")
    description: Optional[str] = None
    score: float = Field(ge=0.0, le=1.0, description="Relevance score (0-1)")
    datasource_id: UUID
    # CRITICAL: Include critical rules directly on table hits to warn the agent
    critical_rules: List[str] = Field(
        default_factory=list,
        description="Critical context rules (e.g., 'Soft delete attivo, SEMPRE filtrare is_deleted=false')"
    )


class ColumnSearchHit(BaseModel):
    """Search result for a COLUMN entity with metadata."""
    type: Literal["COLUMN"] = "COLUMN"
    id: UUID
    name: str = Field(description="Physical column name")
    semantic_name: Optional[str] = Field(default=None, description="Human-readable name")
    description: Optional[str] = None
    score: float = Field(ge=0.0, le=1.0)
    table_id: UUID
    table_name: str = Field(description="Parent table's physical name")
    # Technical metadata crucial for SQL generation
    data_type: str = Field(description="Native SQL type (VARCHAR, INT, etc.)")
    is_pk: bool = Field(default=False, description="Is this a primary key?")
    is_fk: bool = Field(default=False, description="Is this a foreign key?")
    context_note: Optional[str] = Field(
        default=None,
        description="Additional context (e.g., JSON structure, date format)"
    )


class DatasourceSearchHit(BaseModel):
    """Search result for a DATASOURCE entity."""
    type: Literal["DATASOURCE"] = "DATASOURCE"
    id: UUID
    name: str
    slug: str
    description: Optional[str] = None
    engine: str = Field(description="SQL dialect (postgres, bigquery, etc.)")
    score: float = Field(ge=0.0, le=1.0)


class MetricSearchHit(BaseModel):
    """Search result for a METRIC entity."""
    type: Literal["METRIC"] = "METRIC"
    id: UUID
    name: str
    description: Optional[str] = None
    sql_template: str = Field(description="The SQL calculation formula")
    score: float = Field(ge=0.0, le=1.0)


# Union type for polymorphic hits
SearchHit = TableSearchHit | ColumnSearchHit | DatasourceSearchHit | MetricSearchHit


class SearchResponse(BaseModel):
    """
    Response from the Omni-Search endpoint.
    Contains a polymorphic list of search hits.
    """
    hits: List[SearchHit] = Field(
        default_factory=list,
        description="List of search results, sorted by relevance score"
    )
    total: int = Field(default=0, description="Total number of matching results")


# =============================================================================
# 2. GRAPH RESOLVER (The Topology Navigator)
# =============================================================================

class GraphRequest(BaseModel):
    """
    Request for the Graph Resolver endpoint.
    Given sparse entities, resolves the JOIN path between them.
    """
    datasource_slug: str = Field(
        ...,
        description="The datasource slug (required to scope the graph)"
    )
    anchor_entities: List[str] = Field(
        ...,
        min_length=2,
        description="List of table names or UUIDs to connect (e.g., ['products', 'regions'])"
    )


class SchemaEdgeDTO(BaseModel):
    """Represents a relationship/edge in the schema graph."""
    source_table: str = Field(description="Source table physical name")
    source_column: str = Field(description="Source column name")
    target_table: str = Field(description="Target table physical name")
    target_column: str = Field(description="Target column name")
    relationship_type: RelationshipTypeEnum
    join_condition: str = Field(
        description="Ready-to-use JOIN condition (e.g., 'products.id = sales_log.prod_id')"
    )


class GraphResponse(BaseModel):
    """
    Response from the Graph Resolver.
    Contains bridge tables and relationships needed to connect the anchor entities.
    """
    bridge_tables: List[str] = Field(
        default_factory=list,
        description="Intermediate tables needed for the JOIN path (not explicitly requested)"
    )
    relationships: List[SchemaEdgeDTO] = Field(
        default_factory=list,
        description="List of edges (relationships) connecting the entities"
    )
    path_found: bool = Field(
        default=True,
        description="Whether a valid path was found between all anchors"
    )


# =============================================================================
# 3. VALUE VALIDATOR (Anti-Hallucination)
# =============================================================================

class ValueTarget(BaseModel):
    """Target column for value validation."""
    table: str = Field(description="Table name")
    column: str = Field(description="Column name")


class ValueValidationRequest(BaseModel):
    """
    Request for validating/correcting WHERE clause values.
    Prevents LLM hallucinations on categorical values.
    """
    datasource_slug: str = Field(..., description="Datasource slug (required)")
    target: ValueTarget = Field(
        ...,
        description="The table.column to validate values against"
    )
    proposed_values: List[str] = Field(
        ...,
        min_length=1,
        description="Values proposed by the LLM (e.g., ['Attivo', 'Cancellato'])"
    )


class ValueValidationResponse(BaseModel):
    """
    Response from the Value Validator.
    Provides corrections and warnings for proposed values.
    """
    valid: bool = Field(
        description="True if ALL proposed values were successfully mapped"
    )
    mappings: Dict[str, str] = Field(
        default_factory=dict,
        description="Correction map: proposed_value -> actual_db_value"
    )
    unresolved: List[str] = Field(
        default_factory=list,
        description="Values that could NOT be mapped (agent should warn user)"
    )


# =============================================================================
# 4. SCHEMA INSPECTOR (The Technical Profiler)
# =============================================================================

class InspectRequest(BaseModel):
    """Request for detailed schema inspection."""
    datasource_slug: str = Field(..., description="Datasource slug (required)")
    table_names: List[str] = Field(
        ...,
        min_length=1,
        description="List of table names to inspect"
    )
    include_samples: bool = Field(
        default=False,
        description="If true, include sample values for columns (requires DB access)"
    )


class ColumnMetadata(BaseModel):
    """Detailed metadata for a single column."""
    name: str
    data_type: str
    is_nullable: bool = True
    is_primary_key: bool = False
    is_foreign_key: bool = False
    description: Optional[str] = None
    context_note: Optional[str] = None
    sample_values: List[str] = Field(
        default_factory=list,
        description="Example values to understand format (e.g., date format)"
    )


class TableSchema(BaseModel):
    """Complete schema information for a single table."""
    table_name: str
    ddl: str = Field(description="Optimized CREATE TABLE statement")
    columns_metadata: List[ColumnMetadata] = Field(default_factory=list)
    global_rules: List[str] = Field(
        default_factory=list,
        description="Aggregated context rules for this table"
    )


class InspectResponse(BaseModel):
    """Response from the Schema Inspector."""
    schemas: List[TableSchema] = Field(default_factory=list)


# =============================================================================
# 5. WISDOM ARCHIVE (Few-Shot Learning Memory)
# =============================================================================

class GoldenSqlSearchRequest(BaseModel):
    """Request to search for validated SQL examples."""
    query: str = Field(
        ...,
        min_length=1,
        description="The user's natural language question"
    )
    datasource_slug: str = Field(..., description="Datasource slug (required)")
    limit: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Number of examples to return"
    )


class GoldenSqlMatch(BaseModel):
    """A single golden SQL example."""
    question: str = Field(description="Original natural language question")
    sql: str = Field(description="Validated SQL query")
    explanation: Optional[str] = Field(
        default=None,
        description="Human explanation of the query (if available)"
    )
    score: float = Field(ge=0.0, le=1.0, description="Semantic similarity score")
    complexity: int = Field(
        default=1,
        ge=1,
        le=5,
        description="Complexity rating (1=simple, 5=very complex)"
    )


class GoldenSqlResponse(BaseModel):
    """Response from the Wisdom Archive."""
    matches: List[GoldenSqlMatch] = Field(default_factory=list)


# =============================================================================
# 6. SEMANTIC EXPLAINER (Business Dictionary)
# =============================================================================

class ConceptExplainRequest(BaseModel):
    """Request to explain business concepts."""
    concepts: List[str] = Field(
        ...,
        min_length=1,
        description="Terms to explain (e.g., ['Churn Rate', 'Clienti VIP'])"
    )
    datasource_slug: Optional[str] = Field(
        default=None,
        description="Optional datasource to scope the lookup"
    )


class MetricExplanation(BaseModel):
    """Explanation of a semantic metric."""
    name: str
    sql_template: str = Field(description="The SQL formula for this metric")
    description: Optional[str] = None
    dependencies: List[str] = Field(
        default_factory=list,
        description="Table names involved in this calculation"
    )


class SynonymExplanation(BaseModel):
    """Explanation of a semantic synonym."""
    term: str = Field(description="The original term/alias")
    resolved_to: str = Field(
        description="What this term maps to (e.g., 'Filter on revenue > 10000')"
    )
    target_type: str = Field(description="Type of target: TABLE, COLUMN, METRIC, VALUE")
    target_id: Optional[UUID] = None


class ConceptExplainResponse(BaseModel):
    """Response from the Semantic Explainer."""
    metrics: List[MetricExplanation] = Field(
        default_factory=list,
        description="Metrics matching the requested concepts"
    )
    synonyms: List[SynonymExplanation] = Field(
        default_factory=list,
        description="Synonyms matching the requested concepts"
    )
    unresolved: List[str] = Field(
        default_factory=list,
        description="Concepts that could not be found"
    )
