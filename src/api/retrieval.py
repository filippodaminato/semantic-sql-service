"""
Discovery API Suite.
The new interface for Agents to explore the Semantic Graph.
Replaces the old monolithic Retrieval API.
"""
import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import or_
from typing import List, Optional, Type, Any, Dict
from uuid import UUID

from ..core.database import get_db
from ..db.models import (
    Datasource, TableNode, ColumnNode, SchemaEdge, SemanticMetric,
    SemanticSynonym, ColumnContextRule, LowCardinalityValue, GoldenSQL
)
from ..schemas.discovery import (
    # Datasource
    DiscoverySearchRequest, DatasourceSearchResult,
    # Golden SQL
    GoldenSQLSearchRequest, GoldenSQLResult,
    # Physical
    TableSearchRequest, TableSearchResult,
    ColumnSearchRequest, ColumnSearchResult,
    EdgeSearchRequest, EdgeSearchResult,
    # Semantic
    MetricSearchRequest, MetricSearchResult,
    SynonymSearchRequest, SynonymSearchResult,
    ContextRuleSearchRequest, ContextRuleSearchResult,
    # Values
    LowCardinalityValueSearchRequest, LowCardinalityValueSearchResult,
    # Pagination
    PaginatedResponse,
    PaginatedDatasourceResponse,
    PaginatedGoldenSQLResponse,
    PaginatedTableResponse,
    PaginatedColumnResponse,
    PaginatedEdgeResponse,
    PaginatedMetricResponse,
    PaginatedSynonymResponse,
    PaginatedContextRuleResponse,
    PaginatedLowCardinalityValueResponse,
    # Graph
    GraphPathRequest, GraphPathResult, GraphNode, GraphEdge,
    # MCP
    MCPResponse,
    # Context
    ContextSearchItem, ContextResolutionResponse
)

from ..services.search import SearchService
from ..services.context_resolution import ContextResolver

router = APIRouter(prefix="/api/v1/discovery", tags=["Discovery"])


# =============================================================================
# API ENDPOINTS
# =============================================================================


@router.post("/resolve-context", response_model=ContextResolutionResponse)
def resolve_context(
    items: List[ContextSearchItem], 
    db: Session = Depends(get_db)
) -> ContextResolutionResponse:
    """
    Unified retrieval endpoint.
    Accepts a list of search entities and returns a resolved hierarchical graph.
    """
    resolver = ContextResolver(db)
    return resolver.resolve(items)


@router.post("/datasources", response_model=PaginatedDatasourceResponse)
def search_datasources(request: DiscoverySearchRequest, db: Session = Depends(get_db)):
    service = SearchService(db)
    return service.search_datasources(request.query, request.page, request.limit, request.min_ratio_to_best)


@router.post("/golden_sql", response_model=PaginatedGoldenSQLResponse)
def search_golden_sql(request: GoldenSQLSearchRequest, db: Session = Depends(get_db)):
    service = SearchService(db)
    return service.search_golden_sql(request.query, request.datasource_slug, request.page, request.limit, request.min_ratio_to_best)

@router.post("/tables", response_model=PaginatedTableResponse)
def search_tables(request: TableSearchRequest, db: Session = Depends(get_db)):
    service = SearchService(db)
    return service.search_tables(request.query, request.datasource_slug, request.page, request.limit, request.min_ratio_to_best)

@router.post("/columns", response_model=PaginatedColumnResponse)
def search_columns(request: ColumnSearchRequest, db: Session = Depends(get_db)):
    service = SearchService(db)
    return service.search_columns(request.query, request.datasource_slug, request.table_slug, request.page, request.limit, request.min_ratio_to_best)

@router.post("/edges", response_model=PaginatedEdgeResponse)
def search_edges(request: EdgeSearchRequest, db: Session = Depends(get_db)):
    service = SearchService(db)
    return service.search_edges(request.query, request.datasource_slug, request.table_slug, request.page, request.limit, request.min_ratio_to_best)

@router.post("/metrics", response_model=PaginatedMetricResponse)
def search_metrics(request: MetricSearchRequest, db: Session = Depends(get_db)):
    service = SearchService(db)
    return service.search_metrics(request.query, request.datasource_slug, request.page, request.limit, request.min_ratio_to_best)

@router.post("/synonyms", response_model=PaginatedSynonymResponse)
def search_synonyms(request: SynonymSearchRequest, db: Session = Depends(get_db)):
    service = SearchService(db)
    return service.search_synonyms(request.query, request.datasource_slug, request.page, request.limit, request.min_ratio_to_best)

@router.post("/context_rules", response_model=PaginatedContextRuleResponse)
def search_context_rules(request: ContextRuleSearchRequest, db: Session = Depends(get_db)):
    service = SearchService(db)
    return service.search_context_rules(request.query, request.datasource_slug, request.table_slug, request.page, request.limit, request.min_ratio_to_best)

@router.post("/low_cardinality_values", response_model=PaginatedLowCardinalityValueResponse)
def search_low_cardinality_values(request: LowCardinalityValueSearchRequest, db: Session = Depends(get_db)):
    service = SearchService(db)
    return service.search_low_cardinality_values(request.query, request.datasource_slug, request.table_slug, request.column_slug, request.page, request.limit, request.min_ratio_to_best)

@router.post("/paths", response_model=GraphPathResult)
def search_graph_paths(
    request: GraphPathRequest,
    db: Session = Depends(get_db)
) -> GraphPathResult:
    """
    Find all valid paths between two tables in the schema graph.
    Useful for understanding how tables can be joined.
    """
    service = SearchService(db)
    return service.search_paths(
        request.source_table_slug,
        request.target_table_slug,
        request.max_depth,
        request.datasource_slug
    )


# =============================================================================
# 11. MCP Endpoints
# =============================================================================

class MCPFormatter:
    """Helper to format paginated responses into human-readable strings for MCP."""

    @staticmethod
    def _format_pagination_footer(response: PaginatedResponse) -> str:
        return f"\n| Page: {response.page} of {response.total_pages} | Total: {response.total}"

    @staticmethod
    def format_datasources(response: PaginatedDatasourceResponse) -> str:
        lines = []
        for item in response.items:
            lines.append(f"### {item.slug}\nName: {item.name}\nEngine: {item.engine}")
            if item.description:
                lines.append(f"Description: {item.description}")
        
        if not lines:
            return "No datasources found."
            
        return "\n\n".join(lines) + MCPFormatter._format_pagination_footer(response)

    @staticmethod
    def format_golden_sql(response: PaginatedGoldenSQLResponse) -> str:
        lines = []
        for item in response.items:
            lines.append(f"### Golden SQL (ID: {item.id})\nPrompt: {item.prompt}\nSQL: {item.sql}\nScore: {item.score:.2f}")
        
        if not lines:
            return "No Golden SQL found."
            
        return "\n\n".join(lines) + MCPFormatter._format_pagination_footer(response)

    @staticmethod
    def format_tables(response: PaginatedTableResponse) -> str:
        lines = []
        for item in response.items:
            section = f"### {item.slug}\nName: {item.physical_name} ({item.semantic_name})"
            if item.description:
                section += f"\nDescription: {item.description}"
            # DDL context is often too long, maybe summarize or truncate? 
            # User example didn't ask for DDL, but let's include if present concisely?
            # User prompt example: "Columns: id uuid, email text UNIQUE..."
            # We don't have column details in TableSearchResult, only table info.
            # To match the user's specific "Columns:" request for *tables*, we'd ideally need to join columns.
            # However, the TableSearchResult only has table props. 
            # The user's example: 
            # ### customers
            # PK: id
            # Columns: id uuid, email text UNIQUE...
            # This implies the '/tables' endpoint should return column info? 
            # Standard '/tables' returns TableSearchResult which doesn't have columns list.
            # I will follow the TableSearchResult data for now.
            lines.append(section)
            
        if not lines:
            return "No tables found."
            
        return "\n\n".join(lines) + MCPFormatter._format_pagination_footer(response)

    @staticmethod
    def format_columns(response: PaginatedColumnResponse) -> str:
        # Group by table for better readability
        from collections import defaultdict
        grouped = defaultdict(list)
        for item in response.items:
            grouped[item.table_slug].append(item)
        
        lines = []
        for table_slug, columns in grouped.items():
            lines.append(f"### Table: {table_slug}")
            for col in columns:
                pk_marker = " [PK]" if col.is_primary_key else ""
                lines.append(f"- {col.name} ({col.data_type}){pk_marker}: {col.description or 'No description'}")
        
        if not lines:
            return "No columns found."
            
        return "\n\n".join(lines) + MCPFormatter._format_pagination_footer(response)

    @staticmethod
    def format_metrics(response: PaginatedMetricResponse) -> str:
        lines = []
        for item in response.items:
            lines.append(f"### {item.slug}\nName: {item.name}\nSQL: {item.calculation_sql}")
            if item.description:
                lines.append(f"Description: {item.description}")
        
        if not lines:
            return "No metrics found."
            
        return "\n\n".join(lines) + MCPFormatter._format_pagination_footer(response)

    @staticmethod
    def format_synonyms(response: PaginatedSynonymResponse) -> str:
        lines = []
        for item in response.items:
            lines.append(f"- {item.term} -> {item.maps_to_slug} ({item.target_type})")
        
        if not lines:
            return "No synonyms found."
            
        return "\n".join(lines) + MCPFormatter._format_pagination_footer(response)

    @staticmethod
    def format_context_rules(response: PaginatedContextRuleResponse) -> str:
        lines = []
        for item in response.items:
            lines.append(f"### {item.slug}\nTarget: {item.table_slug}.{item.column_slug}\nRule: {item.rule_text}")
        
        if not lines:
            return "No context rules found."
            
        return "\n\n".join(lines) + MCPFormatter._format_pagination_footer(response)

    @staticmethod
    def format_low_cardinality_values(response: PaginatedLowCardinalityValueResponse) -> str:
        lines = []
        for item in response.items:
            label = f" ({item.value_label})" if item.value_label else ""
            lines.append(f"- {item.table_slug}.{item.column_slug}: {item.value_raw}{label}")
        
        if not lines:
            return "No values found."
            
        return "\n".join(lines) + MCPFormatter._format_pagination_footer(response)

    @staticmethod
    def format_edges(response: PaginatedEdgeResponse) -> str:
        lines = []
        for item in response.items:
            lines.append(f"- {item.source} -> {item.target} ({item.relationship_type})")
            if item.description:
                lines.append(f"  Description: {item.description}")
        
        if not lines:
            return "No edges found."
            
        return "\n".join(lines) + MCPFormatter._format_pagination_footer(response)

    @staticmethod
    def format_resolved_context(response: ContextResolutionResponse) -> str:
        """
        Converts the hierarchical context response into a clean, token-efficient 
        Markdown format optimized for LLM ingestion.
        """
        blocks = []

        for ds in response.graph:
            ds_block = []
            
            # 1. Livello Datasource
            ds_block.append(f"# Datasource: `{ds.name}`")
            ds_block.append(f"- **Slug**: {ds.slug}")
            if ds.description:
                ds_block.append(f"- **Usage**: {ds.description} \n")
            
            # 2. Livello Tabelle
            ds_block.append(f"\t## Founded Tables:")
            for table in ds.tables:
                ds_block.append(f"\t\t### Table: `{table.physical_name}` ")
                ds_block.append(f"\t\t- **Slug**: `{table.slug}`")
                ds_block.append(f"\t\t- **Usage**: {table.description or 'No description available.'}")
                
                # 3. Livello Colonne (Mostriamo solo se ci sono colonne rilevanti)
                if table.columns:
                    ds_block.append(f"\n\t\t\t#### Founded Columns:")
                    for col in table.columns:
                        # Costruiamo la riga della colonna in modo compatto
                        ds_block.append(f"\t\t\t\t##### Column: `{col.name}` ")
                        ds_block.append(f"\t\t\t\t- **Slug**: `{col.slug}`")

                        if col.data_type:
                            ds_block.append(f"\t\t\t\t- **Type**: `{col.data_type}`")
                        
                        if col.description:
                            ds_block.append(f"\t\t\t\t- **Desc**: `{col.description}`")

                        if col.context_note:
                            ds_block.append(f"\t\t\t\t- **Notes**: `{col.context_note}`")

                        # 4a. Nominal Values (Low Cardinality)
                        if col.nominal_values:
                            vals = [v.value_raw for v in col.nominal_values]
                            # Limita a 5 valori per evitare bloat
                            val_str = ", ".join(vals[:5])
                            if len(vals) > 5:
                                val_str += ", ..."
                            ds_block.append(f"\t\t\t\t> Nominal Values: {val_str}")

                        # 4b. Context Rules
                        if col.context_rules:
                            for rule in col.context_rules:
                                ds_block.append(f"\t\t\t\t> Context Rule: {rule.rule_text}")
                        ds_block.append("\n")
                

            # 5. Metrics
            if ds.metrics:
                ds_block.append("\n\t### Semantic Metrics")
                for metric in ds.metrics:
                    ds_block.append(f"\t\t- **{metric.name}**")
                    if metric.description:
                        ds_block.append(f"\t\t- Desc : {metric.description}")
                    ds_block.append(f"\t\t- SQL: `{metric.calculation_sql}`")
                ds_block.append("\n\t\t---")
            
            # 6. Edges / Relationships
            if ds.edges:
                ds_block.append("\n\t\t### Relationships")
                for edge in ds.edges:
                    ds_block.append(f"\t\t- `{edge.source}` -> `{edge.target}` ({edge.relationship_type})")
                    if edge.description:
                         ds_block.append(f"\t\t- _{edge.description}_")
                ds_block.append("\n\t\t---")

            # 7. Golden SQL
            if ds.golden_sqls:
                ds_block.append("\n\t\t### Golden SQL Examples")
                for gs in ds.golden_sqls:
                    ds_block.append(f"\t\t- **Prompt**: \"{gs.prompt}\"")
                    ds_block.append(f"\t\t- `SQL`: {gs.sql}")
                ds_block.append("\n\t\t---")

            blocks.append("\n".join(ds_block))
            
        # Uniamo tutto in una singola stringa
        return "\n".join(blocks)


@router.post("/mcp/datasources", response_model=MCPResponse)
def mcp_search_datasources(request: DiscoverySearchRequest, db: Session = Depends(get_db)):
    service = SearchService(db)
    result = service.search_datasources(request.query, request.page, request.limit)
    return MCPResponse(res=MCPFormatter.format_datasources(result))

@router.post("/mcp/golden_sql", response_model=MCPResponse)
def mcp_search_golden_sql(request: GoldenSQLSearchRequest, db: Session = Depends(get_db)):
    service = SearchService(db)
    result = service.search_golden_sql(request.query, request.datasource_slug, request.page, request.limit)
    return MCPResponse(res=MCPFormatter.format_golden_sql(result))

@router.post("/mcp/tables", response_model=MCPResponse)
def mcp_search_tables(request: TableSearchRequest, db: Session = Depends(get_db)):
    service = SearchService(db)
    result = service.search_tables(request.query, request.datasource_slug, request.page, request.limit)
    
    # Custom Logic to match User's detailed example (PK, Columns, FK) requires more data
    # than just TableSearchResult. But for strict "format the response", we format what we have.
    # To truly match "Columns: id uuid...", we'd need to fetch columns for these tables.
    # For now, I will format the available TableSearchResult data stringly. 
    # If the user wants full column details per table in one go, they might need a specialized endpoint
    # or we'd need to enrich the service method. 
    # Given the prompt, I will stick to formatting the SearchResult objects.
    
    return MCPResponse(res=MCPFormatter.format_tables(result))

@router.post("/mcp/columns", response_model=MCPResponse)
def mcp_search_columns(request: ColumnSearchRequest, db: Session = Depends(get_db)):
    service = SearchService(db)
    result = service.search_columns(request.query, request.datasource_slug, request.table_slug, request.page, request.limit)
    return MCPResponse(res=MCPFormatter.format_columns(result))

@router.post("/mcp/edges", response_model=MCPResponse)
def mcp_search_edges(request: EdgeSearchRequest, db: Session = Depends(get_db)):
    service = SearchService(db)
    result = service.search_edges(request.query, request.datasource_slug, request.table_slug, request.page, request.limit)
    return MCPResponse(res=MCPFormatter.format_edges(result))

@router.post("/mcp/metrics", response_model=MCPResponse)
def mcp_search_metrics(request: MetricSearchRequest, db: Session = Depends(get_db)):
    service = SearchService(db)
    result = service.search_metrics(request.query, request.datasource_slug, request.page, request.limit)
    return MCPResponse(res=MCPFormatter.format_metrics(result))

@router.post("/mcp/synonyms", response_model=MCPResponse)
def mcp_search_synonyms(request: SynonymSearchRequest, db: Session = Depends(get_db)):
    service = SearchService(db)
    result = service.search_synonyms(request.query, request.datasource_slug, request.page, request.limit)
    return MCPResponse(res=MCPFormatter.format_synonyms(result))

@router.post("/mcp/context_rules", response_model=MCPResponse)
def mcp_search_context_rules(request: ContextRuleSearchRequest, db: Session = Depends(get_db)):
    service = SearchService(db)
    result = service.search_context_rules(request.query, request.datasource_slug, request.table_slug, request.page, request.limit)
    return MCPResponse(res=MCPFormatter.format_context_rules(result))

@router.post("/mcp/low_cardinality_values", response_model=MCPResponse)
def mcp_search_low_cardinality_values(request: LowCardinalityValueSearchRequest, db: Session = Depends(get_db)):
    service = SearchService(db)
    result = service.search_low_cardinality_values(request.query, request.datasource_slug, request.table_slug, request.column_slug, request.page, request.limit)
    return MCPResponse(res=MCPFormatter.format_low_cardinality_values(result))


@router.post("/mcp/resolve-context", response_model=MCPResponse)
def mcp_resolve_context(
    items: List[ContextSearchItem], 
    db: Session = Depends(get_db)
):
    resolver = ContextResolver(db)
    result = resolver.resolve(items)
    return MCPResponse(res=MCPFormatter.format_resolved_context(result))
