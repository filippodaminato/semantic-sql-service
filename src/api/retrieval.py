"""
Router for Retrieval & Search domain.

This module implements the 6 Retrieval API endpoints for Agentic RAG:
1. Omni-Search: Unified semantic and structural search
2. Graph Resolver: Topology navigation and JOIN path resolution
3. Value Validator: Anti-hallucination value verification
4. Schema Inspector: Technical DDL and metadata profiling
5. Wisdom Archive: Few-shot learning from golden SQL examples
6. Semantic Explainer: Business concept and metric dictionary

All endpoints are designed to be consumed by an external AI Agent (e.g., LangGraph)
to enable fully autonomous SQL generation.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from typing import List, Optional, Dict, Set
import networkx as nx
from uuid import UUID

from ..core.database import get_db
from ..db.models import (
    Datasource, TableNode, ColumnNode, SchemaEdge, SemanticMetric,
    LowCardinalityValue, SemanticSynonym, GoldenSQL, ColumnContextRule,
    RelationshipType
)
from ..services.embedding_service import embedding_service
from ..schemas.retrieval import (
    # 1. Omni-Search
    SearchRequest, SearchResponse, SearchFilters, EntityType,
    TableSearchHit, ColumnSearchHit, DatasourceSearchHit, MetricSearchHit,
    # 2. Graph Resolver
    GraphRequest, GraphResponse, SchemaEdgeDTO, RelationshipTypeEnum,
    # 3. Value Validator
    ValueValidationRequest, ValueValidationResponse,
    # 4. Schema Inspector
    InspectRequest, InspectResponse, TableSchema, ColumnMetadata,
    # 5. Wisdom Archive
    GoldenSqlSearchRequest, GoldenSqlResponse, GoldenSqlMatch,
    # 6. Semantic Explainer
    ConceptExplainRequest, ConceptExplainResponse, MetricExplanation, SynonymExplanation,
)

router = APIRouter(prefix="/api/v1/retrieval", tags=["Retrieval"])


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _get_datasource_by_slug(db: Session, slug: str) -> Datasource:
    """Retrieve datasource by slug or raise 404."""
    ds = db.query(Datasource).filter(Datasource.slug == slug).first()
    if not ds:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Datasource with slug '{slug}' not found"
        )
    return ds


def _get_critical_rules_for_table(db: Session, table_id: UUID) -> List[str]:
    """
    Get critical context rules for columns in a table.
    These are rules that should ALWAYS be considered (e.g., soft delete filters).
    
    For now, we return ALL rules. A future enhancement could add an `is_critical`
    flag to the ColumnContextRule model.
    """
    # Get all columns for the table
    columns = db.query(ColumnNode).filter(ColumnNode.table_id == table_id).all()
    rules = []
    for col in columns:
        for rule in col.context_rules:
            # Prefix with column name for context
            rules.append(f"[{col.name}] {rule.rule_text}")
    return rules


def _build_join_condition(source_table: str, source_col: str, 
                          target_table: str, target_col: str) -> str:
    """Build SQL JOIN condition string."""
    return f"{source_table}.{source_col} = {target_table}.{target_col}"


# =============================================================================
# 1. OMNI-SEARCH (The Discovery Engine)
# =============================================================================

@router.post("/search", response_model=SearchResponse)
def unified_search(
    request: SearchRequest,
    db: Session = Depends(get_db)
):
    """
    Unified semantic search across Datasources, Tables, Columns, and Metrics.
    
    Supports two main use cases:
    - **Semantic Search**: When `query` is provided, performs vector similarity search
    - **Drill-Down**: When `filters.parent_id` is provided, returns children of that entity
    
    The response includes polymorphic hits with type-specific metadata.
    For TABLE results, critical context rules are included to warn the agent.
    """
    hits = []
    filters = request.filters or SearchFilters()
    limit = request.limit
    
    # Determine which entity types to search
    entity_types = filters.entity_types or [
        EntityType.DATASOURCE, EntityType.TABLE, EntityType.COLUMN, EntityType.METRIC
    ]
    
    # Check if this is a drill-down request (parent_id provided)
    if filters.parent_id:
        return _handle_drilldown(db, filters.parent_id, entity_types, limit)
    
    # Semantic search mode - requires query
    if not request.query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'query' or 'filters.parent_id' must be provided"
        )
    
    query_embedding = embedding_service.generate_embedding(request.query)
    
    # Get datasource filter if specified
    datasource_id = None
    if filters.datasource_slug:
        ds = _get_datasource_by_slug(db, filters.datasource_slug)
        datasource_id = ds.id
    
    # Search Datasources
    if EntityType.DATASOURCE in entity_types:
        ds_query = db.query(
            Datasource,
            Datasource.embedding.cosine_distance(query_embedding).label("distance")
        ).filter(Datasource.embedding.isnot(None))
        
        if datasource_id:
            ds_query = ds_query.filter(Datasource.id == datasource_id)
            
        ds_results = ds_query.order_by("distance").limit(limit).all()
        
        for ds, dist in ds_results:
            hits.append(DatasourceSearchHit(
                id=ds.id,
                name=ds.name,
                slug=ds.slug,
                description=ds.description,
                engine=ds.engine.value,
                score=max(0.0, 1 - dist)
            ))
    
    # Search Tables
    if EntityType.TABLE in entity_types:
        table_query = db.query(
            TableNode,
            TableNode.embedding.cosine_distance(query_embedding).label("distance")
        ).filter(TableNode.embedding.isnot(None))
        
        if datasource_id:
            table_query = table_query.filter(TableNode.datasource_id == datasource_id)
            
        table_results = table_query.order_by("distance").limit(limit).all()
        
        for table, dist in table_results:
            critical_rules = _get_critical_rules_for_table(db, table.id)
            hits.append(TableSearchHit(
                id=table.id,
                name=table.semantic_name,
                physical_name=table.physical_name,
                description=table.description,
                score=max(0.0, 1 - dist),
                datasource_id=table.datasource_id,
                critical_rules=critical_rules
            ))
    
    # Search Columns
    if EntityType.COLUMN in entity_types:
        column_query = db.query(
            ColumnNode,
            ColumnNode.embedding.cosine_distance(query_embedding).label("distance")
        ).join(TableNode).filter(ColumnNode.embedding.isnot(None))
        
        if datasource_id:
            column_query = column_query.filter(TableNode.datasource_id == datasource_id)
            
        column_results = column_query.order_by("distance").limit(limit).all()
        
        for col, dist in column_results:
            # Check if this column is a FK
            is_fk = db.query(SchemaEdge).filter(
                SchemaEdge.source_column_id == col.id
            ).first() is not None
            
            hits.append(ColumnSearchHit(
                id=col.id,
                name=col.name,
                semantic_name=col.semantic_name,
                description=col.description,
                score=max(0.0, 1 - dist),
                table_id=col.table_id,
                table_name=col.table.physical_name,
                data_type=col.data_type,
                is_pk=col.is_primary_key,
                is_fk=is_fk,
                context_note=col.context_note
            ))
    
    # Search Metrics
    if EntityType.METRIC in entity_types:
        metric_query = db.query(
            SemanticMetric,
            SemanticMetric.embedding.cosine_distance(query_embedding).label("distance")
        ).filter(SemanticMetric.embedding.isnot(None))
        
        metric_results = metric_query.order_by("distance").limit(limit).all()
        
        for metric, dist in metric_results:
            hits.append(MetricSearchHit(
                id=metric.id,
                name=metric.name,
                description=metric.description,
                sql_template=metric.calculation_sql,
                score=max(0.0, 1 - dist)
            ))
    
    # Sort all hits by score descending
    hits.sort(key=lambda x: x.score, reverse=True)
    
    return SearchResponse(
        hits=hits[:limit],
        total=len(hits)
    )


def _handle_drilldown(
    db: Session, 
    parent_id: UUID, 
    entity_types: List[EntityType],
    limit: int
) -> SearchResponse:
    """
    Handle drill-down navigation: return children of a parent entity.
    - Datasource -> Tables
    - Table -> Columns
    """
    hits = []
    
    # Try as Datasource first
    datasource = db.query(Datasource).filter(Datasource.id == parent_id).first()
    if datasource and EntityType.TABLE in entity_types:
        # Return tables in this datasource
        tables = db.query(TableNode).filter(
            TableNode.datasource_id == parent_id
        ).limit(limit).all()
        
        for table in tables:
            critical_rules = _get_critical_rules_for_table(db, table.id)
            hits.append(TableSearchHit(
                id=table.id,
                name=table.semantic_name,
                physical_name=table.physical_name,
                description=table.description,
                score=1.0,  # Hierarchical match
                datasource_id=table.datasource_id,
                critical_rules=critical_rules
            ))
        
        return SearchResponse(hits=hits, total=len(hits))
    
    # Try as Table
    table = db.query(TableNode).filter(TableNode.id == parent_id).first()
    if table and EntityType.COLUMN in entity_types:
        # Return columns in this table
        columns = db.query(ColumnNode).filter(
            ColumnNode.table_id == parent_id
        ).limit(limit).all()
        
        for col in columns:
            is_fk = db.query(SchemaEdge).filter(
                SchemaEdge.source_column_id == col.id
            ).first() is not None
            
            hits.append(ColumnSearchHit(
                id=col.id,
                name=col.name,
                semantic_name=col.semantic_name,
                description=col.description,
                score=1.0,
                table_id=col.table_id,
                table_name=table.physical_name,
                data_type=col.data_type,
                is_pk=col.is_primary_key,
                is_fk=is_fk,
                context_note=col.context_note
            ))
        
        return SearchResponse(hits=hits, total=len(hits))
    
    # Parent not found or invalid type
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Entity with ID '{parent_id}' not found or cannot be expanded"
    )


# =============================================================================
# 2. GRAPH RESOLVER (The Topology Navigator)
# =============================================================================

@router.post("/graph/expand", response_model=GraphResponse)
def expand_graph(
    request: GraphRequest,
    db: Session = Depends(get_db)
):
    """
    Resolve the JOIN path between anchor entities.
    
    Given sparse entities (e.g., "products" and "regions"), this endpoint
    finds the optimal JOIN path, including any bridge tables needed.
    
    Uses NetworkX for pathfinding in the schema graph.
    """
    # Validate datasource
    datasource = _get_datasource_by_slug(db, request.datasource_slug)
    
    # Get all tables in this datasource
    tables = db.query(TableNode).filter(
        TableNode.datasource_id == datasource.id
    ).all()
    table_map = {t.physical_name.lower(): t for t in tables}
    table_id_map = {t.id: t for t in tables}
    
    # Resolve anchor entities to table IDs
    anchor_table_ids: Set[UUID] = set()
    for anchor in request.anchor_entities:
        # Try as table name first
        if anchor.lower() in table_map:
            anchor_table_ids.add(table_map[anchor.lower()].id)
        else:
            # Try as UUID
            try:
                anchor_uuid = UUID(anchor)
                if anchor_uuid in table_id_map:
                    anchor_table_ids.add(anchor_uuid)
                else:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Entity '{anchor}' not found in datasource"
                    )
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Entity '{anchor}' not found in datasource"
                )
    
    if len(anchor_table_ids) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least 2 distinct anchor tables required"
        )
    
    # Build NetworkX graph from SchemaEdges
    G = nx.Graph()
    
    # Add all tables as nodes
    for table in tables:
        G.add_node(table.id, name=table.physical_name)
    
    # Get all edges involving tables in this datasource
    edges = db.query(SchemaEdge).join(
        ColumnNode, SchemaEdge.source_column_id == ColumnNode.id
    ).join(
        TableNode, ColumnNode.table_id == TableNode.id
    ).filter(
        TableNode.datasource_id == datasource.id
    ).options(
        joinedload(SchemaEdge.source_column).joinedload(ColumnNode.table),
        joinedload(SchemaEdge.target_column).joinedload(ColumnNode.table)
    ).all()
    
    # Build edge metadata
    edge_details: Dict[tuple, SchemaEdge] = {}
    for edge in edges:
        source_table_id = edge.source_column.table_id
        target_table_id = edge.target_column.table_id
        
        # Add edge (undirected for pathfinding)
        G.add_edge(source_table_id, target_table_id)
        edge_details[(source_table_id, target_table_id)] = edge
        edge_details[(target_table_id, source_table_id)] = edge  # Store both directions
    
    # Find paths between all anchor pairs
    anchor_list = list(anchor_table_ids)
    all_tables_in_path: Set[UUID] = set(anchor_table_ids)
    relationships: List[SchemaEdgeDTO] = []
    path_found = True
    
    # Find shortest path connecting all anchors
    try:
        # Use Steiner tree approximation for multiple terminals
        if len(anchor_list) == 2:
            # Simple case: shortest path between two nodes
            path = nx.shortest_path(G, anchor_list[0], anchor_list[1])
            all_tables_in_path.update(path)
        else:
            # Multiple anchors: find paths pairwise
            for i in range(len(anchor_list)):
                for j in range(i + 1, len(anchor_list)):
                    try:
                        path = nx.shortest_path(G, anchor_list[i], anchor_list[j])
                        all_tables_in_path.update(path)
                    except nx.NetworkXNoPath:
                        path_found = False
    except nx.NetworkXNoPath:
        path_found = False
    
    if not path_found:
        return GraphResponse(
            bridge_tables=[],
            relationships=[],
            path_found=False
        )
    
    # Extract edges along the path
    visited_edges: Set[tuple] = set()
    for table_id in all_tables_in_path:
        for neighbor in G.neighbors(table_id):
            if neighbor in all_tables_in_path:
                edge_key = tuple(sorted([table_id, neighbor]))
                if edge_key not in visited_edges:
                    visited_edges.add(edge_key)
                    
                    # Get edge details
                    edge = edge_details.get((table_id, neighbor))
                    if edge:
                        source_table = edge.source_column.table
                        target_table = edge.target_column.table
                        
                        relationships.append(SchemaEdgeDTO(
                            source_table=source_table.physical_name,
                            source_column=edge.source_column.name,
                            target_table=target_table.physical_name,
                            target_column=edge.target_column.name,
                            relationship_type=RelationshipTypeEnum(edge.relationship_type.value),
                            join_condition=_build_join_condition(
                                source_table.physical_name,
                                edge.source_column.name,
                                target_table.physical_name,
                                edge.target_column.name
                            )
                        ))
    
    # Identify bridge tables (tables in path but not in original anchors)
    bridge_table_ids = all_tables_in_path - anchor_table_ids
    bridge_tables = [table_id_map[tid].physical_name for tid in bridge_table_ids]
    
    return GraphResponse(
        bridge_tables=bridge_tables,
        relationships=relationships,
        path_found=True
    )


# =============================================================================
# 3. VALUE VALIDATOR (Anti-Hallucination)
# =============================================================================

@router.post("/values/validate", response_model=ValueValidationResponse)
def validate_values(
    request: ValueValidationRequest,
    db: Session = Depends(get_db)
):
    """
    Validate and resolve categorical values before SQL generation.
    
    The agent knows WHERE to filter but doesn't know the exact values
    (e.g., "Lombardia" vs "LOM"). This endpoint corrects such mismatches.
    
    Uses exact match first, then falls back to vector similarity search.
    """
    # Validate datasource
    datasource = _get_datasource_by_slug(db, request.datasource_slug)
    
    # Find the target column
    column = db.query(ColumnNode).join(TableNode).filter(
        TableNode.datasource_id == datasource.id,
        TableNode.physical_name.ilike(request.target.table),
        ColumnNode.name.ilike(request.target.column)
    ).first()
    
    if not column:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Column {request.target.table}.{request.target.column} not found in datasource"
        )
    
    mappings: Dict[str, str] = {}
    unresolved: List[str] = []
    
    for proposed_value in request.proposed_values:
        # 1. Try exact match (case-insensitive)
        exact_match = db.query(LowCardinalityValue).filter(
            LowCardinalityValue.column_id == column.id,
            or_(
                LowCardinalityValue.value_label.ilike(proposed_value),
                LowCardinalityValue.value_raw.ilike(proposed_value)
            )
        ).first()
        
        if exact_match:
            mappings[proposed_value] = exact_match.value_raw
            continue
        
        # 2. Fallback to vector similarity search
        value_embedding = embedding_service.generate_embedding(proposed_value)
        
        vector_match = db.query(
            LowCardinalityValue,
            LowCardinalityValue.embedding.cosine_distance(value_embedding).label("distance")
        ).filter(
            LowCardinalityValue.column_id == column.id,
            LowCardinalityValue.embedding.isnot(None)
        ).order_by("distance").limit(1).first()
        
        if vector_match:
            lcv, distance = vector_match
            similarity = 1 - distance
            
            # Threshold: 0.85 similarity for auto-resolution
            if similarity >= 0.85:
                mappings[proposed_value] = lcv.value_raw
            else:
                unresolved.append(proposed_value)
        else:
            unresolved.append(proposed_value)
    
    return ValueValidationResponse(
        valid=len(unresolved) == 0,
        mappings=mappings,
        unresolved=unresolved
    )


# =============================================================================
# 4. SCHEMA INSPECTOR (The Technical Profiler)
# =============================================================================

@router.post("/schema/inspect", response_model=InspectResponse)
def inspect_schema(
    request: InspectRequest,
    db: Session = Depends(get_db)
):
    """
    Get detailed technical information about specific tables.
    
    Returns:
    - DDL statements
    - Column metadata with types and constraints
    - Context rules aggregated per table
    - Optionally, sample values (useful for date format detection)
    """
    # Validate datasource
    datasource = _get_datasource_by_slug(db, request.datasource_slug)
    
    schemas: List[TableSchema] = []
    
    for table_name in request.table_names:
        # Find the table
        table = db.query(TableNode).filter(
            TableNode.datasource_id == datasource.id,
            TableNode.physical_name.ilike(table_name)
        ).first()
        
        if not table:
            continue  # Skip unknown tables silently
        
        # Get columns with context rules
        columns = db.query(ColumnNode).filter(
            ColumnNode.table_id == table.id
        ).options(joinedload(ColumnNode.context_rules)).all()
        
        columns_metadata: List[ColumnMetadata] = []
        global_rules: List[str] = []
        
        for col in columns:
            # Check if FK
            is_fk = db.query(SchemaEdge).filter(
                SchemaEdge.source_column_id == col.id
            ).first() is not None
            
            # Get sample values if requested
            sample_values = []
            if request.include_samples:
                lcv_samples = db.query(LowCardinalityValue).filter(
                    LowCardinalityValue.column_id == col.id
                ).limit(5).all()
                sample_values = [s.value_raw for s in lcv_samples]
            
            columns_metadata.append(ColumnMetadata(
                name=col.name,
                data_type=col.data_type,
                is_nullable=True,  # TODO: Add to model
                is_primary_key=col.is_primary_key,
                is_foreign_key=is_fk,
                description=col.description,
                context_note=col.context_note,
                sample_values=sample_values
            ))
            
            # Collect rules
            for rule in col.context_rules:
                global_rules.append(f"[{col.name}] {rule.rule_text}")
        
        # Build DDL (use stored or generate from metadata)
        ddl = table.ddl_context or _generate_ddl(table, columns_metadata)
        
        schemas.append(TableSchema(
            table_name=table.physical_name,
            ddl=ddl,
            columns_metadata=columns_metadata,
            global_rules=global_rules
        ))
    
    return InspectResponse(schemas=schemas)


def _generate_ddl(table: TableNode, columns: List[ColumnMetadata]) -> str:
    """Generate a minimal DDL statement from column metadata."""
    col_defs = []
    for col in columns:
        col_def = f"  {col.name} {col.data_type}"
        if col.is_primary_key:
            col_def += " PRIMARY KEY"
        col_defs.append(col_def)
    
    return f"CREATE TABLE {table.physical_name} (\n" + ",\n".join(col_defs) + "\n);"


# =============================================================================
# 5. WISDOM ARCHIVE (Few-Shot Learning Memory)
# =============================================================================

@router.post("/golden-sql/search", response_model=GoldenSqlResponse)
def search_golden_sql(
    request: GoldenSqlSearchRequest,
    db: Session = Depends(get_db)
):
    """
    Find semantically similar validated SQL examples.
    
    Essential for Few-Shot Learning: provides proven examples that help
    the LLM understand query patterns specific to this datasource.
    """
    # Validate datasource
    datasource = _get_datasource_by_slug(db, request.datasource_slug)
    
    # Generate embedding for the query
    query_embedding = embedding_service.generate_embedding(request.query)
    
    # Search golden SQL examples
    results = db.query(
        GoldenSQL,
        GoldenSQL.embedding.cosine_distance(query_embedding).label("distance")
    ).filter(
        GoldenSQL.datasource_id == datasource.id,
        GoldenSQL.embedding.isnot(None),
        GoldenSQL.verified == True
    ).order_by("distance").limit(request.limit).all()
    
    matches = []
    for golden, distance in results:
        matches.append(GoldenSqlMatch(
            question=golden.prompt_text,
            sql=golden.sql_query,
            explanation=None,  # TODO: Add explanation field to GoldenSQL model
            score=max(0.0, 1 - distance),
            complexity=golden.complexity_score
        ))
    
    return GoldenSqlResponse(matches=matches)


# =============================================================================
# 6. SEMANTIC EXPLAINER (Business Dictionary)
# =============================================================================

@router.post("/concepts/explain", response_model=ConceptExplainResponse)
def explain_concepts(
    request: ConceptExplainRequest,
    db: Session = Depends(get_db)
):
    """
    Decode business concepts like metrics and domain jargon.
    
    For each concept:
    - Search SemanticMetrics for formula definitions
    - Search SemanticSynonyms for term mappings
    """
    # Get optional datasource filter
    datasource_id = None
    if request.datasource_slug:
        datasource = _get_datasource_by_slug(db, request.datasource_slug)
        datasource_id = datasource.id
    
    metrics: List[MetricExplanation] = []
    synonyms: List[SynonymExplanation] = []
    unresolved: List[str] = []
    
    for concept in request.concepts:
        found = False
        
        # 1. Search in Metrics (by name, case-insensitive)
        metric = db.query(SemanticMetric).filter(
            SemanticMetric.name.ilike(f"%{concept}%")
        ).first()
        
        if metric:
            found = True
            # Get dependency table names
            dependencies = []
            if metric.required_tables:
                for table_id_str in metric.required_tables:
                    try:
                        table = db.query(TableNode).filter(
                            TableNode.id == table_id_str
                        ).first()
                        if table:
                            dependencies.append(table.physical_name)
                    except:
                        pass
            
            metrics.append(MetricExplanation(
                name=metric.name,
                sql_template=metric.calculation_sql,
                description=metric.description,
                dependencies=dependencies
            ))
        
        # 2. Search in Synonyms (by term, case-insensitive)
        synonym = db.query(SemanticSynonym).filter(
            SemanticSynonym.term.ilike(f"%{concept}%")
        ).first()
        
        if synonym:
            found = True
            # Build resolved_to description based on target type
            resolved_to = f"Maps to {synonym.target_type.value} with ID {synonym.target_id}"
            
            # Try to get actual target name
            if synonym.target_type.value == "TABLE":
                target = db.query(TableNode).filter(TableNode.id == synonym.target_id).first()
                if target:
                    resolved_to = f"Table: {target.physical_name}"
            elif synonym.target_type.value == "COLUMN":
                target = db.query(ColumnNode).filter(ColumnNode.id == synonym.target_id).first()
                if target:
                    resolved_to = f"Column: {target.table.physical_name}.{target.name}"
            elif synonym.target_type.value == "METRIC":
                target = db.query(SemanticMetric).filter(SemanticMetric.id == synonym.target_id).first()
                if target:
                    resolved_to = f"Metric: {target.name}"
                    
            synonyms.append(SynonymExplanation(
                term=synonym.term,
                resolved_to=resolved_to,
                target_type=synonym.target_type.value,
                target_id=synonym.target_id
            ))
        
        if not found:
            unresolved.append(concept)
    
    return ConceptExplainResponse(
        metrics=metrics,
        synonyms=synonyms,
        unresolved=unresolved
    )


# =============================================================================
# ADMIN ENDPOINT (Embedding Sync)
# =============================================================================

@router.post("/admin/sync-embeddings", status_code=status.HTTP_200_OK)
def sync_embeddings(db: Session = Depends(get_db)):
    """
    Admin: Re-calculate embeddings where content hash doesn't match stored hash.
    Useful for system maintenance or after bulk updates.
    """
    updated_count = 0
    
    # 1. Sync Datasources
    datasources = db.query(Datasource).all()
    for ds in datasources:
        content = f"{ds.description or ''} {ds.context_signature or ''}".strip()
        current_hash = embedding_service.calculate_hash(content)
        if current_hash != ds.embedding_hash:
            if content:
                ds.embedding = embedding_service.generate_embedding(content)
                ds.embedding_hash = current_hash
                updated_count += 1
            elif ds.embedding is not None:
                ds.embedding = None
                ds.embedding_hash = None
                updated_count += 1

    # 2. Sync Tables
    tables = db.query(TableNode).all()
    for t in tables:
        content = f"{t.semantic_name}"
        if t.description:
            content += f" {t.description}"
        
        current_hash = embedding_service.calculate_hash(content)
        if current_hash != t.embedding_hash:
            t.embedding = embedding_service.generate_embedding(content)
            t.embedding_hash = current_hash
            updated_count += 1

    # 3. Sync Columns
    columns = db.query(ColumnNode).all()
    for c in columns:
        content = c.semantic_name or c.name
        if c.description:
            content += f" {c.description}"
        if c.context_note:
            content += f" {c.context_note}"
        
        current_hash = embedding_service.calculate_hash(content)
        if current_hash != c.embedding_hash:
            c.embedding = embedding_service.generate_embedding(content)
            c.embedding_hash = current_hash
            updated_count += 1
            
    # 4. Sync Metrics
    metrics = db.query(SemanticMetric).all()
    for m in metrics:
        content = f"{m.name}"
        if m.description:
            content += f" {m.description}"
        
        current_hash = embedding_service.calculate_hash(content)
        if current_hash != m.embedding_hash:
            m.embedding = embedding_service.generate_embedding(content)
            m.embedding_hash = current_hash
            updated_count += 1
    
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error syncing embeddings: {str(e)}"
        )
        
    return {"status": "success", "updated_entities": updated_count}
