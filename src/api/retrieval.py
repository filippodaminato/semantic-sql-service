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
    LowCardinalityValueSearchRequest, LowCardinalityValueSearchResult
)

router = APIRouter(prefix="/api/v1/discovery", tags=["Discovery"])


class SearchService:
    """
    Service to handle discovery searches.
    Abstracts the logic of resolving slugs and calling the backend search engine.
    """
    def __init__(self, db: Session):
        self.db = db

    def _resolve_datasource_id(self, slug: Optional[str]) -> Optional[UUID]:
        if not slug:
            return None
        ds = self.db.query(Datasource).filter(Datasource.slug == slug).first()
        return ds.id if ds else None

    def _resolve_table_id(self, datasource_id: UUID, slug: Optional[str]) -> Optional[UUID]:
        """
        Resolve table ID from slug, optionally scoped to a datasource.
        
        Args:
            datasource_id: Optional datasource ID to scope the search
            slug: Table slug to resolve
        
        Returns:
            Table UUID if found, None otherwise
        """
        if not slug:
            return None
        
        if datasource_id:
            # Scoped search within datasource
            table = self.db.query(TableNode).filter(
                TableNode.datasource_id == datasource_id,
                TableNode.slug == slug
            ).first()
        else:
            # Global search (table slugs are unique)
            table = self.db.query(TableNode).filter(
                TableNode.slug == slug
            ).first()
        
        return table.id if table else None

    def _resolve_column_id(self, table_id: UUID, slug: Optional[str]) -> Optional[UUID]:
        if not slug or not table_id:
            return None
        col = self.db.query(ColumnNode).filter(
            ColumnNode.table_id == table_id,
            ColumnNode.slug == slug
        ).first()
        return col.id if col else None

    def _generic_search(
        self, 
        model: Type[Any], 
        query: str, 
        filters: Dict[str, Any], 
        limit: int = 10,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Leverage SearchableMixin for Hybrid Search (RRF).
        """
        # Ensure model has SearchableMixin
        if not hasattr(model, 'search'):
            # Fallback for non-searchable models (should not happen for core entities)
            return []
        
        # Ensure query is not None (handle None/empty strings)
        if query is None:
            query = ""
            
        result = model.search(
            session=self.db,
            query=query,
            filters=filters or {},
            limit=limit,
            **kwargs
        )
        
        # Always return a list, never None
        return result if result is not None else []

    # -------------------------------------------------------------------------
    # 1. Datasources
    # -------------------------------------------------------------------------
    def search_datasources(self, query: str, limit: int = 10) -> List[DatasourceSearchResult]:
        """Search datasources and return complete information."""
        hits = self._generic_search(Datasource, query, {}, limit)
        # Always return a list, never None
        if not hits:
            return []
        return [
            DatasourceSearchResult.model_validate(hit['entity'])
            for hit in hits
        ]

    # -------------------------------------------------------------------------
    # 2. Golden SQL
    # -------------------------------------------------------------------------
    def search_golden_sql(self, query: str, datasource_slug: Optional[str], limit: int = 10) -> List[GoldenSQLResult]:
        """
        Search Golden SQL examples and return complete information.
        
        Returns empty list if query is empty or whitespace-only.
        For listing all golden SQL examples, use the GET endpoint instead.
        """
        # Reject empty queries - search requires actual content
        if not query or not query.strip():
            return []
        
        filters = {}
        if datasource_slug:
            ds_id = self._resolve_datasource_id(datasource_slug)
            if not ds_id:
                return []
            filters['datasource_id'] = ds_id
        
        hits = self._generic_search(GoldenSQL, query, filters, limit)
        results = []
        for hit in hits:
            entity = hit['entity']
            # Create result with all fields, including search score
            result_dict = {
                'id': entity.id,
                'datasource_id': entity.datasource_id,
                'prompt': entity.prompt_text,
                'sql': entity.sql_query,
                'complexity': entity.complexity_score,
                'verified': entity.verified,
                'score': hit['score'],
                'created_at': entity.created_at,
                'updated_at': entity.updated_at
            }
            results.append(GoldenSQLResult(**result_dict))
        return results

    # -------------------------------------------------------------------------
    # 3. Tables
    # -------------------------------------------------------------------------
    def search_tables(self, query: str, datasource_slug: Optional[str], limit: int = 10) -> List[TableSearchResult]:
        """
        Search tables with optional filter by datasource.
        
        Args:
            query: Search query string
            datasource_slug: Optional filter by datasource slug
            limit: Maximum number of results
        
        Returns:
            List of TableSearchResult matching the query and filters.
            Returns empty list if datasource_slug is provided but not found.
        """
        filters = {}
        if datasource_slug:
            ds_id = self._resolve_datasource_id(datasource_slug)
            if not ds_id:
                # Datasource not found -> return empty list
                return []
            filters['datasource_id'] = ds_id

        hits = self._generic_search(TableNode, query, filters, limit)
        return [
            TableSearchResult.model_validate(hit['entity'])
            for hit in hits
        ]

    # -------------------------------------------------------------------------
    # 4. Columns
    # -------------------------------------------------------------------------
    def search_columns(self, query: str, datasource_slug: Optional[str], table_slug: Optional[str], limit: int = 10) -> List[ColumnSearchResult]:
        """
        Search columns with optional filters by datasource and/or table.
        
        Args:
            query: Search query string
            datasource_slug: Optional filter by datasource slug
            table_slug: Optional filter by table slug (can be used with or without datasource_slug)
            limit: Maximum number of results
        
        Returns:
            List of ColumnSearchResult matching the query and filters
        
        Note:
            - If only datasource_slug is provided: searches all columns in that datasource
            - If only table_slug is provided: searches columns in that table (table slugs are globally unique)
            - If both are provided: searches columns in the table, with validation that table belongs to datasource
            - If neither is provided: searches all columns globally
        """
        filters = {}
        base_stmt = None
        from sqlalchemy import select
        
        ds_id = None
        if datasource_slug:
            ds_id = self._resolve_datasource_id(datasource_slug)
            if not ds_id:
                return []  # Datasource not found -> No results
        
        if table_slug:
            # Resolve table_id (with or without datasource context)
            # Table slugs are globally unique, so we can resolve without datasource
            # but if datasource is provided, we scope the search for better performance
            table_id = self._resolve_table_id(ds_id, table_slug)
            if not table_id:
                return []  # Table not found -> No results
            
            # Add table_id filter - this works directly on ColumnNode
            filters['table_id'] = table_id
            
            # If we also have datasource_id, we can add it to filters for additional validation
            # But since table_id already scopes to a specific table (which belongs to one datasource),
            # this is redundant but harmless
            if ds_id:
                # Verify table belongs to this datasource (safety check)
                table = self.db.query(TableNode).filter(TableNode.id == table_id).first()
                if table and table.datasource_id != ds_id:
                    return []  # Table doesn't belong to specified datasource
        elif ds_id:
            # Filter by datasource only -> Requires JOIN since ColumnNode doesn't have datasource_id
            # Create base_stmt with JOIN to TableNode and filter by datasource_id
            base_stmt = select(ColumnNode).join(TableNode).where(TableNode.datasource_id == ds_id)
        
        # Perform search with filters and optional base_stmt
        hits = self._generic_search(ColumnNode, query, filters, limit, base_stmt=base_stmt)
        
        # Pre-load table relationships to avoid N+1 queries
        # Collect all column IDs and eager load their table relationships
        if hits:
            column_ids = [hit['entity'].id for hit in hits]
            # Use selectinload for efficient batch loading
            columns_with_tables = self.db.query(ColumnNode).options(
                selectinload(ColumnNode.table)
            ).filter(ColumnNode.id.in_(column_ids)).all()
            
            # Create a map for quick lookup
            column_map = {col.id: col for col in columns_with_tables}
            
            # Build results using pre-loaded data
            results = []
            for hit in hits:
                entity_id = hit['entity'].id
                entity = column_map.get(entity_id, hit['entity'])
                # Get table slug from pre-loaded relationship (no additional query)
                table_slug = entity.table.slug if entity.table else None
                # Create result with all fields
                result_dict = {
                    'id': entity.id,
                    'table_id': entity.table_id,
                    'table_slug': table_slug,
                    'slug': entity.slug,
                    'name': entity.name,
                    'semantic_name': entity.semantic_name,
                    'data_type': entity.data_type,
                    'is_primary_key': entity.is_primary_key,
                    'description': entity.description,
                    'context_note': entity.context_note,
                    'created_at': entity.created_at,
                    'updated_at': entity.updated_at
                }
                results.append(ColumnSearchResult(**result_dict))
            return results
        return []

    # -------------------------------------------------------------------------
    # 5. Edges (Custom Implementation - No SearchableMixin)
    # -------------------------------------------------------------------------
    def search_edges(self, query: str, datasource_slug: Optional[str], table_slug: Optional[str] = None, limit: int = 10) -> List[EdgeSearchResult]:
        # Start generic query: Join Source Column -> Source Table AND Target Column -> Target Table
        # We need aliases if we join TableNode twice? 
        # Actually, simpler: just join source column/table and then check conditions.
        # But if we want to support "edges involving table X (either as source or target)", we need deeper filtering.
        
        from sqlalchemy.orm import aliased
        
        SourceCol = aliased(ColumnNode)
        TargetCol = aliased(ColumnNode)
        SourceTable = aliased(TableNode)
        TargetTable = aliased(TableNode)
        
        stmt = self.db.query(SchemaEdge).\
            join(SourceCol, SchemaEdge.source_column_id == SourceCol.id).\
            join(SourceTable, SourceCol.table_id == SourceTable.id).\
            join(TargetCol, SchemaEdge.target_column_id == TargetCol.id).\
            join(TargetTable, TargetCol.table_id == TargetTable.id)
        
        if datasource_slug:
            ds = self.db.query(Datasource).filter(Datasource.slug == datasource_slug).first()
            if not ds:
                return []
            stmt = stmt.filter(SourceTable.datasource_id == ds.id)
                
        if table_slug:
            # Filter edges where EITHER source OR target table matches the slug
            stmt = stmt.filter(or_(
                SourceTable.slug == table_slug,
                TargetTable.slug == table_slug
            ))

        if query:
            # Simple ILIKE on description
            stmt = stmt.filter(SchemaEdge.description.ilike(f"%{query}%"))
            
        results = stmt.limit(limit).all()
        
        output = []
        for edge in results:
            # Lazy loading will fetch related columns and tables
            # Format: table.column (flattened for convenience)
            src = f"{edge.source_column.table.slug}.{edge.source_column.slug}"
            tgt = f"{edge.target_column.table.slug}.{edge.target_column.slug}"
            
            # Create result with all fields
            result_dict = {
                'id': edge.id,
                'source_column_id': edge.source_column_id,
                'target_column_id': edge.target_column_id,
                'source': src,
                'target': tgt,
                'relationship_type': edge.relationship_type.value,
                'is_inferred': edge.is_inferred,
                'description': edge.description,
                'context_note': getattr(edge, 'context_note', None),
                'created_at': edge.created_at
            }
            output.append(EdgeSearchResult(**result_dict))
        return output

    # -------------------------------------------------------------------------
    # 6. Metrics
    # -------------------------------------------------------------------------
    def search_metrics(self, query: str, datasource_slug: Optional[str], limit: int = 10) -> List[MetricSearchResult]:
        """
        Search metrics with optional filter by datasource.
        
        Args:
            query: Search query string
            datasource_slug: Optional filter by datasource slug
            limit: Maximum number of results
        
        Returns:
            List of MetricSearchResult matching the query and filters.
            Returns empty list if datasource_slug is provided but not found.
        """
        filters = {}
        base_stmt = None
        from sqlalchemy import select
        
        if datasource_slug:
            ds_id = self._resolve_datasource_id(datasource_slug)
            if not ds_id:
                # Datasource not found -> return empty list
                return []
            # Create base_stmt to explicitly filter by datasource_id and exclude NULL
            # This ensures metrics without datasource_id are not included in results
            # We use base_stmt instead of filters to have more control over the WHERE clause
            # and to explicitly exclude NULL values (which col == value should do, but this is safer)
            base_stmt = select(SemanticMetric).where(
                SemanticMetric.datasource_id == ds_id,
                SemanticMetric.datasource_id.isnot(None)  # Explicitly exclude NULL values
            )
            # Don't add to filters since we're using base_stmt (filters would be redundant)
        
        hits = self._generic_search(SemanticMetric, query, filters, limit, base_stmt=base_stmt)
        results = []
        for hit in hits:
            entity = hit['entity']
            # Parse required_tables from JSON if present
            required_tables = None
            if entity.required_tables:
                if isinstance(entity.required_tables, list):
                    required_tables = entity.required_tables
                elif isinstance(entity.required_tables, str):
                    try:
                        required_tables = json.loads(entity.required_tables)
                    except:
                        required_tables = [entity.required_tables]
            
            result_dict = {
                'id': entity.id,
                'datasource_id': entity.datasource_id,
                'slug': entity.slug,
                'name': entity.name,
                'description': entity.description,
                'calculation_sql': entity.calculation_sql,
                'required_tables': required_tables,
                'filter_condition': entity.filter_condition,
                'created_at': entity.created_at,
                'updated_at': entity.updated_at
            }
            results.append(MetricSearchResult(**result_dict))
        return results

    # -------------------------------------------------------------------------
    # 7. Synonyms
    # -------------------------------------------------------------------------
    def search_synonyms(self, query: str, datasource_slug: Optional[str], limit: int = 10) -> List[SynonymSearchResult]:
        """Search synonyms and return complete information with resolved target slugs."""
        hits = self._generic_search(SemanticSynonym, query, {}, limit)
        
        if not hits:
            return []
        
        # Batch load all target entities to avoid N+1 queries
        # Group synonyms by target_type and collect IDs
        table_ids = []
        column_ids = []
        metric_ids = []
        value_ids = []
        
        for hit in hits:
            entity = hit['entity']
            target_type = entity.target_type.value
            if target_type == "TABLE":
                table_ids.append(entity.target_id)
            elif target_type == "COLUMN":
                column_ids.append(entity.target_id)
            elif target_type == "METRIC":
                metric_ids.append(entity.target_id)
            elif target_type == "VALUE":
                value_ids.append(entity.target_id)
        
        # Batch load all targets in parallel
        table_map = {}
        if table_ids:
            tables = self.db.query(TableNode).filter(TableNode.id.in_(table_ids)).all()
            table_map = {t.id: t.slug for t in tables}
        
        column_map = {}
        if column_ids:
            columns = self.db.query(ColumnNode).filter(ColumnNode.id.in_(column_ids)).all()
            column_map = {c.id: c.slug for c in columns}
        
        metric_map = {}
        if metric_ids:
            metrics = self.db.query(SemanticMetric).filter(SemanticMetric.id.in_(metric_ids)).all()
            metric_map = {m.id: m.slug for m in metrics}
        
        value_map = {}
        if value_ids:
            values = self.db.query(LowCardinalityValue).filter(LowCardinalityValue.id.in_(value_ids)).all()
            value_map = {v.id: v.slug for v in values}
        
        # Build results using batch-loaded data
        results = []
        for hit in hits:
            entity = hit['entity']
            # Resolve target slug from batch-loaded maps
            maps_to_slug = "unknown"
            try:
                target_type = entity.target_type.value
                if target_type == "TABLE":
                    maps_to_slug = table_map.get(entity.target_id, "unknown")
                elif target_type == "COLUMN":
                    maps_to_slug = column_map.get(entity.target_id, "unknown")
                elif target_type == "METRIC":
                    maps_to_slug = metric_map.get(entity.target_id, "unknown")
                elif target_type == "VALUE":
                    maps_to_slug = value_map.get(entity.target_id, "unknown")
            except Exception:
                # If resolution fails, keep "unknown"
                pass
            
            result_dict = {
                'id': entity.id,
                'term': entity.term,
                'target_id': entity.target_id,
                'target_type': entity.target_type.value,
                'maps_to_slug': maps_to_slug,
                'created_at': entity.created_at
            }
            results.append(SynonymSearchResult(**result_dict))
        return results

    # -------------------------------------------------------------------------
    # 8. Context Rules
    # -------------------------------------------------------------------------
    def search_context_rules(self, query: str, datasource_slug: Optional[str], table_slug: Optional[str], limit: int = 10) -> List[ContextRuleSearchResult]:
        filters = {}
        base_stmt = None
        from sqlalchemy import select

        ds_id = None
        if datasource_slug:
            ds_id = self._resolve_datasource_id(datasource_slug)
            if not ds_id:
                return []

        if table_slug:
            # Need ds_id to resolve table reliably usually, but if we trust unique slug:
            # But let's verify context.
            if ds_id:
                 table_id = self._resolve_table_id(ds_id, table_slug)
                 if not table_id:
                     return []
                 base_stmt = select(ColumnContextRule).join(ColumnNode).where(ColumnNode.table_id == table_id)
            else:
                 # If no DS, we should probably fail or search global?
                 # Consistent behavior: if table filter requested but resolution fails (requires DS context usually):
                 # For now, if no DS provided, try global resolution of table?
                 # Implementation detail: _resolve_table_id requires ds_id.
                 # Let's enforce DS for table filter or fail if ambiguous?
                 # To be safe and strict:
                 return [] # Cannot resolve table without DS context in current architecture
        elif ds_id:
             base_stmt = select(ColumnContextRule).join(ColumnNode).join(TableNode).where(TableNode.datasource_id == ds_id)

        hits = self._generic_search(ColumnContextRule, query, filters, limit, base_stmt=base_stmt)
        return [
            ContextRuleSearchResult.model_validate(hit['entity'])
            for hit in hits
        ]

    # -------------------------------------------------------------------------
    # 9. Low Cardinality Values
    # -------------------------------------------------------------------------
    def search_low_cardinality_values(self, query: str, datasource_slug: Optional[str], table_slug: Optional[str], column_slug: Optional[str], limit: int = 10) -> List[LowCardinalityValueSearchResult]:
        filters = {}
        base_stmt = None
        from sqlalchemy import select
        
        ds_id = None
        if datasource_slug:
            ds_id = self._resolve_datasource_id(datasource_slug)
            if not ds_id:
                return []
        
        if ds_id and table_slug:
             table_id = self._resolve_table_id(ds_id, table_slug)
             if not table_id:
                 return []
             
             if column_slug:
                 col_id = self._resolve_column_id(table_id, column_slug)
                 if not col_id:
                     return []
                 filters['column_id'] = col_id
             else:
                 base_stmt = select(LowCardinalityValue).join(ColumnNode).where(ColumnNode.table_id == table_id)
        elif ds_id:
             base_stmt = select(LowCardinalityValue).join(ColumnNode).join(TableNode).where(TableNode.datasource_id == ds_id)

        hits = self._generic_search(LowCardinalityValue, query, filters, limit, base_stmt=base_stmt)
        
        # Pre-load column and table relationships to avoid N+1 queries
        if hits:
            value_ids = [hit['entity'].id for hit in hits]
            # Use selectinload to eagerly load column and table relationships
            values_with_relations = self.db.query(LowCardinalityValue).options(
                selectinload(LowCardinalityValue.column).selectinload(ColumnNode.table)
            ).filter(LowCardinalityValue.id.in_(value_ids)).all()
            
            # Create a map for quick lookup
            value_map = {v.id: v for v in values_with_relations}
            
            # Build results using pre-loaded data
            results = []
            for hit in hits:
                entity_id = hit['entity'].id
                entity = value_map.get(entity_id, hit['entity'])
                # Get slugs from pre-loaded relationships (no additional queries)
                column_slug = entity.column.slug if entity.column else None
                table_slug = entity.column.table.slug if entity.column and entity.column.table else None
                
                result_dict = {
                    'id': entity.id,
                    'column_id': entity.column_id,
                    'column_slug': column_slug,
                    'table_slug': table_slug,
                    'value_raw': entity.value_raw,
                    'value_label': entity.value_label,
                    'created_at': entity.created_at,
                    'updated_at': entity.updated_at
                }
                results.append(LowCardinalityValueSearchResult(**result_dict))
            return results
        return []


# =============================================================================
# API ENDPOINTS
# =============================================================================

@router.post("/datasources", response_model=List[DatasourceSearchResult])
def search_datasources(request: DiscoverySearchRequest, db: Session = Depends(get_db)):
    service = SearchService(db)
    return service.search_datasources(request.query, request.limit)

@router.post("/golden_sql", response_model=List[GoldenSQLResult])
def search_golden_sql(request: GoldenSQLSearchRequest, db: Session = Depends(get_db)):
    service = SearchService(db)
    return service.search_golden_sql(request.query, request.datasource_slug, request.limit)

@router.post("/tables", response_model=List[TableSearchResult])
def search_tables(request: TableSearchRequest, db: Session = Depends(get_db)):
    service = SearchService(db)
    return service.search_tables(request.query, request.datasource_slug, request.limit)

@router.post("/columns", response_model=List[ColumnSearchResult])
def search_columns(request: ColumnSearchRequest, db: Session = Depends(get_db)):
    service = SearchService(db)
    return service.search_columns(request.query, request.datasource_slug, request.table_slug, request.limit)

@router.post("/edges", response_model=List[EdgeSearchResult])
def search_edges(request: EdgeSearchRequest, db: Session = Depends(get_db)):
    service = SearchService(db)
    return service.search_edges(request.query, request.datasource_slug, request.table_slug, request.limit)

@router.post("/metrics", response_model=List[MetricSearchResult])
def search_metrics(request: MetricSearchRequest, db: Session = Depends(get_db)):
    service = SearchService(db)
    return service.search_metrics(request.query, request.datasource_slug, request.limit)

@router.post("/synonyms", response_model=List[SynonymSearchResult])
def search_synonyms(request: SynonymSearchRequest, db: Session = Depends(get_db)):
    service = SearchService(db)
    return service.search_synonyms(request.query, request.datasource_slug, request.limit)

@router.post("/context_rules", response_model=List[ContextRuleSearchResult])
def search_context_rules(request: ContextRuleSearchRequest, db: Session = Depends(get_db)):
    service = SearchService(db)
    return service.search_context_rules(request.query, request.datasource_slug, request.table_slug, request.limit)

@router.post("/low_cardinality_values", response_model=List[LowCardinalityValueSearchResult])
def search_low_cardinality_values(request: LowCardinalityValueSearchRequest, db: Session = Depends(get_db)):
    service = SearchService(db)
    return service.search_low_cardinality_values(request.query, request.datasource_slug, request.table_slug, request.column_slug, request.limit)
