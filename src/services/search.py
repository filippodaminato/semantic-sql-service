"""
Search Service.
Handles logic for discovery searches and graph traversal.
"""
import json
from typing import List, Optional, Type, Any, Dict
from uuid import UUID
from fastapi import HTTPException

from sqlalchemy.orm import Session, joinedload, selectinload, aliased
from sqlalchemy import or_, select

from ..db.models import (
    Datasource, TableNode, ColumnNode, SchemaEdge, SemanticMetric,
    SemanticSynonym, ColumnContextRule, LowCardinalityValue, GoldenSQL
)
from ..schemas.discovery import (
    # Datasource
    DatasourceSearchResult,
    # Golden SQL
    GoldenSQLResult,
    # Physical
    TableSearchResult,
    ColumnSearchResult,
    EdgeSearchResult,
    # Semantic
    MetricSearchResult,
    SynonymSearchResult,
    ContextRuleSearchResult,
    # Values
    LowCardinalityValueSearchResult,
    # Pagination
    PaginatedResponse,
    # Graph
    GraphPathResult, GraphNode, GraphEdge
)

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
        offset: int = 0,
        min_ratio_to_best: float = None,
        **kwargs
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        Leverage SearchableMixin for Hybrid Search (RRF) with pagination support.
        
        Returns:
            Tuple of (results, total_count)
        """
        # Ensure model has SearchableMixin
        if not hasattr(model, 'search'):
            # Fallback for non-searchable models (should not happen for core entities)
            return [], 0
        
        # Ensure query is not None (handle None/empty strings)
        if query is None:
            query = ""
        
        # Get total count for pagination metadata
        total = 0
        if hasattr(model, 'search_count'):
            total = model.search_count(
                session=self.db,
                query=query,
                filters=filters or {},
                base_stmt=kwargs.get('base_stmt')
            )
            
        # Perform search with offset
        result = model.search(
            session=self.db,
            query=query,
            filters=filters or {},
            limit=limit,
            offset=offset,
            min_ratio_to_best=min_ratio_to_best,
            **kwargs
        )
        
        # Always return a list, never None
        results = result if result is not None else []
        return results, total

    # -------------------------------------------------------------------------
    # Helper: Build Paginated Response
    # -------------------------------------------------------------------------
    def _build_paginated_response(
        self,
        items: List[Any],
        total: int,
        page: int,
        limit: int
    ) -> PaginatedResponse[Any]:
        """
        Build a paginated response with metadata.
        
        Args:
            items: List of items for the current page
            total: Total number of items across all pages (from database count)
            page: Current page number (1-indexed)
            limit: Number of items per page
        
        Returns:
            PaginatedResponse with items and pagination metadata
        """
        # Calculate total_pages using ceiling division
        # Formula: ceil(total / limit) = (total + limit - 1) // limit
        # If total is 0, total_pages should be 0
        total_pages = (total + limit - 1) // limit if total > 0 else 0
        
        has_next = page < total_pages
        has_prev = page > 1
        
        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            limit=limit,
            has_next=has_next,
            has_prev=has_prev,
            total_pages=total_pages
        )
    
    # -------------------------------------------------------------------------
    # 1. Datasources
    # -------------------------------------------------------------------------
    def search_datasources(
        self, 
        query: str, 
        page: int = 1, 
        limit: int = 10,
        min_ratio_to_best: float = None
    ) -> PaginatedResponse[DatasourceSearchResult]:
        """Search datasources and return paginated results."""
        offset = (page - 1) * limit
        hits, total = self._generic_search(Datasource, query, {}, limit, offset, min_ratio_to_best=min_ratio_to_best)
        
        items = []
        for hit in hits:
            item = DatasourceSearchResult.model_validate(hit['entity'])
            item.score = hit['score']
            items.append(item)
        
        return self._build_paginated_response(items, total, page, limit)

    # -------------------------------------------------------------------------
    # 2. Golden SQL
    # -------------------------------------------------------------------------
    def search_golden_sql(
        self, 
        query: str, 
        datasource_slug: Optional[str], 
        page: int = 1,
        limit: int = 10,
        min_ratio_to_best: float = None
    ) -> PaginatedResponse[GoldenSQLResult]:
        """
        Search Golden SQL examples and return paginated results.
        
        Returns empty paginated response if query is empty or whitespace-only.
        For listing all golden SQL examples, use the GET endpoint instead.
        """
        # Allow empty queries to return all results (e.g. for listing)
        if query is None:
            query = ""
        
        filters = {}
        if datasource_slug:
            ds_id = self._resolve_datasource_id(datasource_slug)
            if not ds_id:
                return self._build_paginated_response([], 0, page, limit)
            filters['datasource_id'] = ds_id
        
        offset = (page - 1) * limit
        offset = (page - 1) * limit
        hits, total = self._generic_search(GoldenSQL, query, filters, limit, offset, min_ratio_to_best=min_ratio_to_best)
        
        items = []
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
            items.append(GoldenSQLResult(**result_dict))
        
        return self._build_paginated_response(items, total, page, limit)

    # -------------------------------------------------------------------------
    # 3. Tables
    # -------------------------------------------------------------------------
    def search_tables(
        self, 
        query: str, 
        datasource_slug: Optional[str], 
        page: int = 1,
        limit: int = 10,
        min_ratio_to_best: float = None
    ) -> PaginatedResponse[TableSearchResult]:
        """
        Search tables with optional filter by datasource.
        
        Args:
            query: Search query string
            datasource_slug: Optional filter by datasource slug
            page: Page number (1-indexed)
            limit: Maximum number of results per page
        
        Returns:
            PaginatedResponse with TableSearchResult items.
            Returns empty paginated response if datasource_slug is provided but not found.
        """
        filters = {}
        if datasource_slug:
            ds_id = self._resolve_datasource_id(datasource_slug)
            if not ds_id:
                # Datasource not found -> return empty paginated response
                return self._build_paginated_response([], 0, page, limit)
            filters['datasource_id'] = ds_id

        offset = (page - 1) * limit
        offset = (page - 1) * limit
        hits, total = self._generic_search(TableNode, query, filters, limit, offset, min_ratio_to_best=min_ratio_to_best)
        
        items = []
        for hit in hits:
            item = TableSearchResult.model_validate(hit['entity'])
            item.score = hit['score']
            items.append(item)
        
        return self._build_paginated_response(items, total, page, limit)

    # -------------------------------------------------------------------------
    # 4. Columns
    # -------------------------------------------------------------------------
    def search_columns(
        self, 
        query: str, 
        datasource_slug: Optional[str], 
        table_slug: Optional[str], 
        page: int = 1,
        limit: int = 10,
        min_ratio_to_best: float = None
    ) -> PaginatedResponse[ColumnSearchResult]:
        """
        Search columns with optional filters by datasource and/or table.
        
        Args:
            query: Search query string
            datasource_slug: Optional filter by datasource slug
            table_slug: Optional filter by table slug (can be used with or without datasource_slug)
            page: Page number (1-indexed)
            limit: Maximum number of results per page
        
        Returns:
            PaginatedResponse with ColumnSearchResult items
        
        Note:
            - If only datasource_slug is provided: searches all columns in that datasource
            - If only table_slug is provided: searches columns in that table (table slugs are globally unique)
            - If both are provided: searches columns in the table, with validation that table belongs to datasource
            - If neither is provided: searches all columns globally
        """
        filters = {}
        base_stmt = None
        
        ds_id = None
        if datasource_slug:
            ds_id = self._resolve_datasource_id(datasource_slug)
            if not ds_id:
                return self._build_paginated_response([], 0, page, limit)  # Datasource not found
        
        if table_slug:
            # Resolve table_id (with or without datasource context)
            # Table slugs are globally unique, so we can resolve without datasource
            # but if datasource is provided, we scope the search for better performance
            table_id = self._resolve_table_id(ds_id, table_slug)
            if not table_id:
                return self._build_paginated_response([], 0, page, limit)  # Table not found
            
            # Add table_id filter - this works directly on ColumnNode
            filters['table_id'] = table_id
            
            # If we also have datasource_id, we can add it to filters for additional validation
            # But since table_id already scopes to a specific table (which belongs to one datasource),
            # this is redundant but harmless
            if ds_id:
                # Verify table belongs to this datasource (safety check)
                table = self.db.query(TableNode).filter(TableNode.id == table_id).first()
                if table and table.datasource_id != ds_id:
                    return self._build_paginated_response([], 0, page, limit)  # Table doesn't belong to datasource
        elif ds_id:
            # Filter by datasource only -> Requires JOIN since ColumnNode doesn't have datasource_id
            # Create base_stmt with JOIN to TableNode and filter by datasource_id
            base_stmt = select(ColumnNode).join(TableNode).where(TableNode.datasource_id == ds_id)
        
        # Perform search with filters and optional base_stmt
        offset = (page - 1) * limit
        hits, total = self._generic_search(ColumnNode, query, filters, limit, offset, base_stmt=base_stmt, min_ratio_to_best=min_ratio_to_best)
        
        # Pre-load table relationships to avoid N+1 queries
        # Collect all column IDs and eager load their table relationships
        items = []
        if hits:
            column_ids = [hit['entity'].id for hit in hits]
            # Use selectinload for efficient batch loading
            columns_with_tables = self.db.query(ColumnNode).options(
                selectinload(ColumnNode.table)
            ).filter(ColumnNode.id.in_(column_ids)).all()
            
            # Create a map for quick lookup
            column_map = {col.id: col for col in columns_with_tables}
            
            # Build results using pre-loaded data
            for hit in hits:
                entity_id = hit['entity'].id
                entity = column_map.get(entity_id, hit['entity'])
                # Get table slug from pre-loaded relationship (no additional query)
                table_slug_val = entity.table.slug if entity.table else None
                # Create result with all fields
                result_dict = {
                    'id': entity.id,
                    'table_id': entity.table_id,
                    'table_slug': table_slug_val,
                    'slug': entity.slug,
                    'name': entity.name,
                    'semantic_name': entity.semantic_name,
                    'data_type': entity.data_type,
                    'is_primary_key': entity.is_primary_key,
                    'description': entity.description,
                    'context_note': entity.context_note,
                    'created_at': entity.created_at,
                    'updated_at': entity.updated_at,
                    'score': hit['score']
                }
                items.append(ColumnSearchResult(**result_dict))
        
        return self._build_paginated_response(items, total, page, limit)

    # -------------------------------------------------------------------------
    # 5. Edges
    # -------------------------------------------------------------------------
    def search_edges(
        self, 
        query: str, 
        datasource_slug: Optional[str], 
        table_slug: Optional[str] = None, 
        page: int = 1,
        limit: int = 10,
        min_ratio_to_best: float = None
    ) -> PaginatedResponse[EdgeSearchResult]:
        """
        Search edges (relationships) with optional filters using hybrid search.
        """
        filters = {}
        base_stmt = None
        
        # Aliases for better joining
        SourceCol = aliased(ColumnNode)
        TargetCol = aliased(ColumnNode)
        SourceTable = aliased(TableNode)
        TargetTable = aliased(TableNode)
        
        # Base statement with all necessary joins
        # This allows us to filter by datasource and table even in hybrid search
        base_stmt = select(SchemaEdge).\
            join(SourceCol, SchemaEdge.source_column_id == SourceCol.id).\
            join(SourceTable, SourceCol.table_id == SourceTable.id).\
            join(TargetCol, SchemaEdge.target_column_id == TargetCol.id).\
            join(TargetTable, TargetCol.table_id == TargetTable.id)
            
        if datasource_slug:
            ds_id = self._resolve_datasource_id(datasource_slug)
            if not ds_id:
                return self._build_paginated_response([], 0, page, limit)
            # Filter where source table belongs to datasource
            base_stmt = base_stmt.where(SourceTable.datasource_id == ds_id)
                
        if table_slug:
            # Filter edges where EITHER source OR target table matches the slug
            base_stmt = base_stmt.where(or_(
                SourceTable.slug == table_slug,
                TargetTable.slug == table_slug
            ))

        # Note: filters={} because we applied filters directly to base_stmt which handles the complex logic
        offset = (page - 1) * limit
        hits, total = self._generic_search(SchemaEdge, query, {}, limit, offset, base_stmt=base_stmt, min_ratio_to_best=min_ratio_to_best)
        
        items = []
        for hit in hits:
            edge = hit['entity']
            # Lazy loading will fetch related columns and tables
            # Format: table.column (flattened for convenience)
            try:
                src = f"{edge.source_column.table.slug}.{edge.source_column.slug}"
                tgt = f"{edge.target_column.table.slug}.{edge.target_column.slug}"
            except AttributeError:
                # Handle cases where relations might be missing/deleted (defensive)
                src = "unknown.unknown"
                tgt = "unknown.unknown"
            
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
                'created_at': edge.created_at,
                'score': hit['score']
            }
            items.append(EdgeSearchResult(**result_dict))
        
        return self._build_paginated_response(items, total, page, limit)

    # -------------------------------------------------------------------------
    # 6. Metrics
    # -------------------------------------------------------------------------
    def search_metrics(
        self, 
        query: str, 
        datasource_slug: Optional[str], 
        page: int = 1, 
        limit: int = 10,
        min_ratio_to_best: float = None
    ) -> PaginatedResponse[MetricSearchResult]:
        """
        Search metrics with optional filter by datasource.
        
        Args:
            query: Search query string
            datasource_slug: Optional filter by datasource slug
            page: Page number (1-indexed)
            limit: Maximum number of results per page
        
        Returns:
            PaginatedResponse with MetricSearchResult items.
            Returns empty paginated response if datasource_slug is provided but not found.
        """
        filters = {}
        base_stmt = None
        
        if datasource_slug:
            ds_id = self._resolve_datasource_id(datasource_slug)
            if not ds_id:
                return self._build_paginated_response([], 0, page, limit)
            # Create base_stmt to explicitly filter by datasource_id and exclude NULL
            base_stmt = select(SemanticMetric).where(
                SemanticMetric.datasource_id == ds_id,
                SemanticMetric.datasource_id.isnot(None)
            )
        
        offset = (page - 1) * limit
        hits, total = self._generic_search(SemanticMetric, query, filters, limit, offset, base_stmt=base_stmt, min_ratio_to_best=min_ratio_to_best)
        
        items = []

        # 1. First pass: Collect all IDs needing resolution
        all_required_ids = set()
        
        # Temp list to hold entities before converting to DTOs
        temp_entities = []

        for hit in hits:
            entity = hit['entity']
            # Parse IDs
            r_ids = []
            if entity.required_tables:
                if isinstance(entity.required_tables, list):
                    r_ids = entity.required_tables
                elif isinstance(entity.required_tables, str):
                    try:
                        parsed = json.loads(entity.required_tables)
                        if isinstance(parsed, list):
                            r_ids = parsed
                        else:
                            r_ids = [parsed]
                    except:
                        r_ids = [entity.required_tables]
            
            # Clean and collect IDs
            clean_ids = []
            for rid in r_ids:
                try:
                    # Validate it's a UUID
                    # Convert to string first to handle UUID objects if already present
                    rid_str = str(rid)
                    uuid_obj = UUID(rid_str)
                    all_required_ids.add(uuid_obj)
                    clean_ids.append(uuid_obj)
                except:
                    pass
            
            temp_entities.append((entity, clean_ids))

        # 2. Batch resolve IDs to Slugs
        id_to_slug_map = {}
        if all_required_ids:
            tables = self.db.query(TableNode).filter(TableNode.id.in_(all_required_ids)).all()
            id_to_slug_map = {t.id: t.slug for t in tables}

        # 3. Build final DTOs
        for entity, clean_ids in temp_entities:
            # Convert IDs to Slugs
            resolved_slugs = [id_to_slug_map.get(tid, str(tid)) for tid in clean_ids]

            result_dict = {
                'id': entity.id,
                'datasource_id': entity.datasource_id,
                'slug': entity.slug,
                'name': entity.name,
                'description': entity.description,
                'calculation_sql': entity.calculation_sql,
                'required_tables': resolved_slugs,
                'filter_condition': entity.filter_condition,
                'created_at': entity.created_at,
                'updated_at': entity.updated_at,
                'score': hit['score']
            }
            items.append(MetricSearchResult(**result_dict))
            
        return self._build_paginated_response(items, total, page, limit)

    # -------------------------------------------------------------------------
    # 7. Synonyms
    # -------------------------------------------------------------------------
    def search_synonyms(
        self, 
        query: str, 
        datasource_slug: Optional[str], 
        page: int = 1,
        limit: int = 10,
        min_ratio_to_best: float = None
    ) -> PaginatedResponse[SynonymSearchResult]:
        """Search synonyms and return paginated results with resolved target slugs."""
        offset = (page - 1) * limit
        hits, total = self._generic_search(SemanticSynonym, query, {}, limit, offset, min_ratio_to_best=min_ratio_to_best)
        
        if not hits:
            return self._build_paginated_response([], total, page, limit)
        
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
        items = []
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
                'created_at': entity.created_at,
                'score': hit['score']
            }
            items.append(SynonymSearchResult(**result_dict))
        
        return self._build_paginated_response(items, total, page, limit)

    # -------------------------------------------------------------------------
    # 8. Context Rules
    # -------------------------------------------------------------------------
    def search_context_rules(
        self, 
        query: str, 
        datasource_slug: Optional[str], 
        table_slug: Optional[str], 
        page: int = 1,
        limit: int = 10,
        min_ratio_to_best: float = None
    ) -> PaginatedResponse[ContextRuleSearchResult]:
        filters = {}
        base_stmt = None

        ds_id = None
        if datasource_slug:
            ds_id = self._resolve_datasource_id(datasource_slug)
            if not ds_id:
                return self._build_paginated_response([], 0, page, limit)

        if table_slug:
            if ds_id:
                 table_id = self._resolve_table_id(ds_id, table_slug)
                 if not table_id:
                     return self._build_paginated_response([], 0, page, limit)
                 base_stmt = select(ColumnContextRule).join(ColumnNode).where(ColumnNode.table_id == table_id)
            else:
                 return self._build_paginated_response([], 0, page, limit)  # Cannot resolve table without DS context
        elif ds_id:
             base_stmt = select(ColumnContextRule).join(ColumnNode).join(TableNode).where(TableNode.datasource_id == ds_id)

        offset = (page - 1) * limit
        hits, total = self._generic_search(ColumnContextRule, query, filters, limit, offset, base_stmt=base_stmt, min_ratio_to_best=min_ratio_to_best)
        
        # Helper to batch resolve column slugs and table slugs
        col_ids = {hit['entity'].column_id for hit in hits if hit['entity'].column_id}
        col_map = {}
        table_map = {}
        
        if col_ids:
            # Join TableNode to get table_slug efficiently
            results = self.db.query(ColumnNode, TableNode)\
                .join(TableNode, ColumnNode.table_id == TableNode.id)\
                .filter(ColumnNode.id.in_(col_ids))\
                .all()
            
            for col, tbl in results:
                col_map[col.id] = col.slug
                table_map[col.id] = tbl.slug # usage: table_map[column_id] -> table_slug

        items = []
        for hit in hits:
            entity = hit['entity']
            # Create dict for Pydantic validation
            item_dict = {
                "id": entity.id,
                "column_id": entity.column_id,
                "column_slug": col_map.get(entity.column_id, "unknown"),
                "table_slug": table_map.get(entity.column_id, "unknown"),
                "slug": entity.slug,
                "rule_text": entity.rule_text,
                "created_at": entity.created_at,
                "updated_at": entity.updated_at,
                "score": hit['score']
            }
            items.append(ContextRuleSearchResult(**item_dict))
        
        return self._build_paginated_response(items, total, page, limit)

    # -------------------------------------------------------------------------
    # 9. Low Cardinality Values
    # -------------------------------------------------------------------------
    def search_low_cardinality_values(
        self, 
        query: str, 
        datasource_slug: Optional[str], 
        table_slug: Optional[str], 
        column_slug: Optional[str], 
        page: int = 1, 
        limit: int = 10,
        min_ratio_to_best: float = None
    ) -> PaginatedResponse[LowCardinalityValueSearchResult]:
        filters = {}
        base_stmt = None
        
        ds_id = None
        if datasource_slug:
            ds_id = self._resolve_datasource_id(datasource_slug)
            if not ds_id:
                return self._build_paginated_response([], 0, page, limit)
        
        table_id = None
        if table_slug:
            # Table slug is unique, resolve directly
            table_node = self.db.query(TableNode).filter(TableNode.slug == table_slug).first()
            if not table_node:
                return self._build_paginated_response([], 0, page, limit)
            
            # If datasource specified, verify consistency
            if ds_id and table_node.datasource_id != ds_id:
                 return self._build_paginated_response([], 0, page, limit)
            table_id = table_node.id
        
        if table_id:
             if column_slug:
                 col_id = self._resolve_column_id(table_id, column_slug)
                 if not col_id:
                     return self._build_paginated_response([], 0, page, limit)
                 filters['column_id'] = col_id
             else:
                 base_stmt = select(LowCardinalityValue).join(ColumnNode).where(ColumnNode.table_id == table_id)
        elif ds_id:
             base_stmt = select(LowCardinalityValue).join(ColumnNode).join(TableNode).where(TableNode.datasource_id == ds_id)

        offset = (page - 1) * limit
        hits, total = self._generic_search(LowCardinalityValue, query, filters, limit, offset, base_stmt=base_stmt, min_ratio_to_best=min_ratio_to_best)
        
        # Pre-load column and table relationships to avoid N+1 queries
        items = []
        if hits:
            value_ids = [hit['entity'].id for hit in hits]
            # Use selectinload to eagerly load column and table relationships
            values_with_relations = self.db.query(LowCardinalityValue).options(
                selectinload(LowCardinalityValue.column).selectinload(ColumnNode.table)
            ).filter(LowCardinalityValue.id.in_(value_ids)).all()
            
            # Create a map for quick lookup
            value_map = {v.id: v for v in values_with_relations}
            
            # Build results using pre-loaded data
            for hit in hits:
                entity_id = hit['entity'].id
                entity = value_map.get(entity_id, hit['entity'])
                # Get slugs from pre-loaded relationships (no additional queries)
                column_slug_val = entity.column.slug if entity.column else None
                table_slug_val = entity.column.table.slug if entity.column and entity.column.table else None
                
                result_dict = {
                    'id': entity.id,
                    'column_id': entity.column_id,
                    'column_slug': column_slug_val,
                    'table_slug': table_slug_val,
                    'value_raw': entity.value_raw,
                    'value_label': entity.value_label,
                    'created_at': entity.created_at,
                    'updated_at': entity.updated_at,
                    'score': hit['score']
                }
                items.append(LowCardinalityValueSearchResult(**result_dict))
        
        return self._build_paginated_response(items, total, page, limit)

    # -------------------------------------------------------------------------
    # 10. Graph Paths
    # -------------------------------------------------------------------------
    def search_paths(
        self,
        source_table_slug: str,
        target_table_slug: str,
        max_depth: int = 3,
        datasource_slug: Optional[str] = None
    ) -> GraphPathResult:
        """Find valid paths between two tables using BFS."""
        
        # 1. Resolve Slugs to Table IDs
        ds = None
        if datasource_slug:
            ds = self.db.query(Datasource).filter(Datasource.slug == datasource_slug).first()
            if not ds:
                raise HTTPException(status_code=404, detail=f"Datasource '{datasource_slug}' not found")

        # Resolve Source Table
        source_query = self.db.query(TableNode).filter(
            or_(
                TableNode.slug == source_table_slug,
                TableNode.physical_name == source_table_slug
            )
        )
        if ds:
            source_query = source_query.filter(TableNode.datasource_id == ds.id)
        source_table = source_query.first()
        
        # Resolve Target Table
        target_query = self.db.query(TableNode).filter(
            or_(
                TableNode.slug == target_table_slug,
                TableNode.physical_name == target_table_slug
            )
        )
        if ds:
            target_query = target_query.filter(TableNode.datasource_id == ds.id)
        target_table = target_query.first()
        
        if not source_table:
            raise HTTPException(status_code=404, detail=f"Source table '{source_table_slug}' not found (tried slug and physical name)")
        if not target_table:
            raise HTTPException(status_code=404, detail=f"Target table '{target_table_slug}' not found (tried slug and physical name)")
            
        source_id = source_table.id
        target_id = target_table.id
        
        # 2. Build Adjacency List for Graph Traversal
        all_edges = self.db.query(SchemaEdge).options(
            joinedload(SchemaEdge.source_column),
            joinedload(SchemaEdge.target_column)
        ).all()
        
        adj = {}
        
        def add_edge(u, v, edge_info):
            if u not in adj: adj[u] = []
            adj[u].append((v, edge_info))
            
        for edge in all_edges:
            if not edge.source_column or not edge.target_column:
                continue
            u_table = edge.source_column.table_id
            v_table = edge.target_column.table_id
            
            # Forward edge (u -> v)
            add_edge(u_table, v_table, {"edge": edge, "direction": "forward"})
            # Reverse edge (v -> u)
            add_edge(v_table, u_table, {"edge": edge, "direction": "reverse"})
            
        # 3. BFS for Path Finding
        # Queue stores: (current_table_id, path_so_far)
        # path_so_far is list of (next_table_id, edge_info)
        queue = [(source_id, [])]
        valid_paths = []
        
        # We need to avoid cycles in standard BFS, but here we want paths.
        # We use a queue state: (current_node, history).
        # History tracks visited nodes in THIS path to avoid cycles.
        
        while queue:
            curr_id, path = queue.pop(0)
            
            if len(path) > max_depth:
                continue
                
            if curr_id == target_id and path:
                 # Found path
                 valid_paths.append(path)
                 continue
            
            if len(path) == max_depth:
                continue
                
            if curr_id in adj:
                visited_in_path = {source_id}
                for vid, _ in path:
                    visited_in_path.add(vid)
                
                for neighbor_id, edge_info in adj[curr_id]:
                    if neighbor_id not in visited_in_path:
                        queue.append((neighbor_id, path + [(neighbor_id, edge_info)]))

        # 4. Construct Response
        involved_table_ids = {source_id, target_id}
        for path in valid_paths:
            for tid, _ in path:
                involved_table_ids.add(tid)
                
        tables_map = {
            t.id: t 
            for t in self.db.query(TableNode).filter(TableNode.id.in_(involved_table_ids)).all()
        }
        
        result_paths = []
        for path in valid_paths:
            graph_edges = []
            curr_table_id = source_id
            
            for next_tid, info in path:
                edge_obj = info["edge"]
                direction = info["direction"]
                
                src_table_obj = tables_map[curr_table_id]
                dst_table_obj = tables_map[next_tid]
                
                if direction == 'forward':
                    src_col = edge_obj.source_column
                    dst_col = edge_obj.target_column
                else:
                    src_col = edge_obj.target_column
                    dst_col = edge_obj.source_column
                
                src_node = GraphNode(
                    table_slug=src_table_obj.slug,
                    column_slug=src_col.slug,
                    table_name=src_table_obj.physical_name,
                    column_name=src_col.name
                )
                
                dst_node = GraphNode(
                    table_slug=dst_table_obj.slug,
                    column_slug=dst_col.slug,
                    table_name=dst_table_obj.physical_name,
                    column_name=dst_col.name
                )
                
                graph_edges.append(GraphEdge(
                    source=src_node,
                    target=dst_node,
                    relationship_type=str(edge_obj.relationship_type),
                    description=edge_obj.description
                ))
                
                curr_table_id = next_tid
                
            result_paths.append(graph_edges)
            
        return GraphPathResult(
            source_table=source_table.physical_name,
            target_table=target_table.physical_name,
            paths=result_paths,
            total_paths=len(result_paths)
        )
