import httpx
from typing import Optional, List, Dict, Any
from langchain_core.tools import tool
from pydantic import BaseModel, Field

BASE_URL = "http://localhost:8000/api/v1/discovery"

def _post(endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        # Filter out None values to avoid sending them in JSON
        clean_payload = {k: v for k, v in payload.items() if v is not None}
        response = httpx.post(f"{BASE_URL}{endpoint}", json=clean_payload, timeout=30.0)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP Error {e.response.status_code}: {e.response.text}"}
    except Exception as e:
        return {"error": str(e)}

# -----------------------------------------------------------------------------
# 1. Datasources
# -----------------------------------------------------------------------------
class DatasourceSearchInput(BaseModel):
    query: str = Field(description="Search query for datasources")
    page: int = Field(default=1, description="Page number")
    limit: int = Field(default=10, description="Items per page")

@tool("search_datasources", args_schema=DatasourceSearchInput)
def search_datasources_tool(query: str, page: int = 1, limit: int = 10) -> Dict[str, Any]:
    """Search for available datasources."""
    return _post("/datasources", {"query": query, "page": page, "limit": limit})

# -----------------------------------------------------------------------------
# 2. Golden SQL
# -----------------------------------------------------------------------------
class GoldenSQLSearchInput(BaseModel):
    query: str = Field(description="Search query for Golden SQL examples")
    datasource_slug: Optional[str] = Field(default=None, description="Filter by datasource slug")
    page: int = Field(default=1, description="Page number")
    limit: int = Field(default=10, description="Items per page")

@tool("search_golden_sql", args_schema=GoldenSQLSearchInput)
def search_golden_sql_tool(query: str, datasource_slug: Optional[str] = None, page: int = 1, limit: int = 10) -> Dict[str, Any]:
    """Search for verified Golden SQL examples (prompt-SQL pairs)."""
    return _post("/golden_sql", {
        "query": query, "datasource_slug": datasource_slug, "page": page, "limit": limit
    })

# -----------------------------------------------------------------------------
# 3. Tables
# -----------------------------------------------------------------------------
class TableSearchInput(BaseModel):
    query: str = Field(description="Search query for tables")
    datasource_slug: Optional[str] = Field(default=None, description="Filter by datasource slug")
    page: int = Field(default=1, description="Page number")
    limit: int = Field(default=10, description="Items per page")

@tool("search_tables", args_schema=TableSearchInput)
def search_tables_tool(query: str, datasource_slug: Optional[str] = None, page: int = 1, limit: int = 10) -> Dict[str, Any]:
    """Search for tables in the schema, optionally filtered by datasource."""
    return _post("/tables", {
        "query": query, "datasource_slug": datasource_slug, "page": page, "limit": limit
    })

# -----------------------------------------------------------------------------
# 4. Columns
# -----------------------------------------------------------------------------
class ColumnSearchInput(BaseModel):
    query: str = Field(description="Search query for columns")
    datasource_slug: Optional[str] = Field(default=None, description="Filter by datasource slug")
    table_slug: Optional[str] = Field(default=None, description="Filter by table slug")
    page: int = Field(default=1, description="Page number")
    limit: int = Field(default=10, description="Items per page")

@tool("search_columns", args_schema=ColumnSearchInput)
def search_columns_tool(query: str, datasource_slug: Optional[str] = None, table_slug: Optional[str] = None, page: int = 1, limit: int = 10) -> Dict[str, Any]:
    """Search for columns, optionally filtered by datasource and/or table."""
    return _post("/columns", {
        "query": query, "datasource_slug": datasource_slug, "table_slug": table_slug, "page": page, "limit": limit
    })

# -----------------------------------------------------------------------------
# 5. Edges
# -----------------------------------------------------------------------------
class EdgeSearchInput(BaseModel):
    query: str = Field(description="Search query for relationships/edges")
    datasource_slug: Optional[str] = Field(default=None, description="Filter by datasource slug")
    table_slug: Optional[str] = Field(default=None, description="Filter by table slug")
    page: int = Field(default=1, description="Page number")
    limit: int = Field(default=10, description="Items per page")

@tool("search_edges", args_schema=EdgeSearchInput)
def search_edges_tool(query: str, datasource_slug: Optional[str] = None, table_slug: Optional[str] = None, page: int = 1, limit: int = 10) -> Dict[str, Any]:
    """Search for schema relationships (edges) between tables/columns."""
    return _post("/edges", {
        "query": query, "datasource_slug": datasource_slug, "table_slug": table_slug, "page": page, "limit": limit
    })

# -----------------------------------------------------------------------------
# 6. Metrics
# -----------------------------------------------------------------------------
class MetricSearchInput(BaseModel):
    query: str = Field(description="Search query for metrics")
    datasource_slug: Optional[str] = Field(default=None, description="Filter by datasource slug")
    page: int = Field(default=1, description="Page number")
    limit: int = Field(default=10, description="Items per page")

@tool("search_metrics", args_schema=MetricSearchInput)
def search_metrics_tool(query: str, datasource_slug: Optional[str] = None, page: int = 1, limit: int = 10) -> Dict[str, Any]:
    """Search for semantic metrics definitions."""
    return _post("/metrics", {
        "query": query, "datasource_slug": datasource_slug, "page": page, "limit": limit
    })

# -----------------------------------------------------------------------------
# 7. Synonyms
# -----------------------------------------------------------------------------
class SynonymSearchInput(BaseModel):
    query: str = Field(description="Search query for synonyms")
    datasource_slug: Optional[str] = Field(default=None, description="Filter by datasource slug")
    page: int = Field(default=1, description="Page number")
    limit: int = Field(default=10, description="Items per page")

@tool("search_synonyms", args_schema=SynonymSearchInput)
def search_synonyms_tool(query: str, datasource_slug: Optional[str] = None, page: int = 1, limit: int = 10) -> Dict[str, Any]:
    """Search for semantic synonyms mapping terms to schema entities."""
    return _post("/synonyms", {
        "query": query, "datasource_slug": datasource_slug, "page": page, "limit": limit
    })

# -----------------------------------------------------------------------------
# 8. Context Rules
# -----------------------------------------------------------------------------
class ContextRuleSearchInput(BaseModel):
    query: str = Field(description="Search query for context rules")
    datasource_slug: Optional[str] = Field(default=None, description="Filter by datasource slug")
    table_slug: Optional[str] = Field(default=None, description="Filter by table slug")
    page: int = Field(default=1, description="Page number")
    limit: int = Field(default=10, description="Items per page")

@tool("search_context_rules", args_schema=ContextRuleSearchInput)
def search_context_rules_tool(query: str, datasource_slug: Optional[str] = None, table_slug: Optional[str] = None, page: int = 1, limit: int = 10) -> Dict[str, Any]:
    """Search for context rules applying to columns or tables."""
    return _post("/context_rules", {
        "query": query, "datasource_slug": datasource_slug, "table_slug": table_slug, "page": page, "limit": limit
    })

# -----------------------------------------------------------------------------
# 9. Low Cardinality Values
# -----------------------------------------------------------------------------
class LowCardinalityValueSearchInput(BaseModel):
    query: str = Field(description="Search query for values")
    datasource_slug: Optional[str] = Field(default=None, description="Filter by datasource slug")
    table_slug: Optional[str] = Field(default=None, description="Filter by table slug")
    column_slug: Optional[str] = Field(default=None, description="Filter by column slug")
    page: int = Field(default=1, description="Page number")
    limit: int = Field(default=10, description="Items per page")

@tool("search_low_cardinality_values", args_schema=LowCardinalityValueSearchInput)
def search_low_cardinality_values_tool(query: str, datasource_slug: Optional[str] = None, table_slug: Optional[str] = None, column_slug: Optional[str] = None, page: int = 1, limit: int = 10) -> Dict[str, Any]:
    """Search for specific low-cardinality values in the database."""
    return _post("/low_cardinality_values", {
        "query": query, "datasource_slug": datasource_slug, "table_slug": table_slug, "column_slug": column_slug, "page": page, "limit": limit
    })

# -----------------------------------------------------------------------------
# 10. Paths
# -----------------------------------------------------------------------------
class GraphPathInput(BaseModel):
    source_table_slug: str = Field(description="Start table slug")
    target_table_slug: str = Field(description="End table slug")
    datasource_slug: Optional[str] = Field(default=None, description="Datasource slug")
    max_depth: int = Field(default=3, description="Max traversal depth")

@tool("search_graph_paths", args_schema=GraphPathInput)
def search_graph_paths_tool(source_table_slug: str, target_table_slug: str, datasource_slug: Optional[str] = None, max_depth: int = 3) -> Dict[str, Any]:
    """Find valid join paths between two tables."""
    return _post("/paths", {
        "source_table_slug": source_table_slug, 
        "target_table_slug": target_table_slug, 
        "datasource_slug": datasource_slug, 
        "max_depth": max_depth
    })

ALL_TOOLS = [
    search_datasources_tool,
    search_golden_sql_tool,
    search_tables_tool,
    search_columns_tool,
    search_edges_tool,
    search_metrics_tool,
    search_synonyms_tool,
    search_context_rules_tool,
    search_low_cardinality_values_tool,
    search_graph_paths_tool
]
