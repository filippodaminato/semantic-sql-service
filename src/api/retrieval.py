"""
Discovery API Suite.
The new interface for Agents to explore the Semantic Graph.
Replaces the old monolithic Retrieval API.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
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
        if not slug or not datasource_id:
            return None
        table = self.db.query(TableNode).filter(
            TableNode.datasource_id == datasource_id,
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
            
        return model.search(
            session=self.db,
            query=query,
            filters=filters,
            limit=limit,
            **kwargs
        )

    # -------------------------------------------------------------------------
    # 1. Datasources
    # -------------------------------------------------------------------------
    def search_datasources(self, query: str, limit: int = 10) -> List[DatasourceSearchResult]:
        hits = self._generic_search(Datasource, query, {}, limit)
        return [
            DatasourceSearchResult(
                slug=hit['entity'].slug,
                name=hit['entity'].name,
                description=hit['entity'].description
            )
            for hit in hits
        ]

    # -------------------------------------------------------------------------
    # 2. Golden SQL
    # -------------------------------------------------------------------------
    def search_golden_sql(self, query: str, datasource_slug: Optional[str], limit: int = 10) -> List[GoldenSQLResult]:
        filters = {}
        if datasource_slug:
            ds_id = self._resolve_datasource_id(datasource_slug)
            if not ds_id:
                return []
            filters['datasource_id'] = ds_id
        
        hits = self._generic_search(GoldenSQL, query, filters, limit)
        return [
            GoldenSQLResult(
                prompt=hit['entity'].prompt_text,
                sql=hit['entity'].sql_query,
                score=hit['score']
            )
            for hit in hits
        ]

    # -------------------------------------------------------------------------
    # 3. Tables
    # -------------------------------------------------------------------------
    def search_tables(self, query: str, datasource_slug: Optional[str], limit: int = 10) -> List[TableSearchResult]:
        filters = {}
        if datasource_slug:
            ds_id = self._resolve_datasource_id(datasource_slug)
            if ds_id:
                filters['datasource_id'] = ds_id

        hits = self._generic_search(TableNode, query, filters, limit)
        return [
            TableSearchResult(
                slug=hit['entity'].slug,
                semantic_name=hit['entity'].semantic_name,
                description=hit['entity'].description
            )
            for hit in hits
        ]

    # -------------------------------------------------------------------------
    # 4. Columns
    # -------------------------------------------------------------------------
    def search_columns(self, query: str, datasource_slug: Optional[str], table_slug: Optional[str], limit: int = 10) -> List[ColumnSearchResult]:
        filters = {}
        base_stmt = None
        from sqlalchemy import select
        
        ds_id = None
        if datasource_slug:
            ds_id = self._resolve_datasource_id(datasource_slug)
            if not ds_id:
                return [] # Datasource not found -> No results
        
        if table_slug:
            if not ds_id:
                # Table slug requires datasource context usually, or we search usage?
                # API spec usually implies hierarchal. If no DS provided, maybe resolving table globaly?
                # For now assume hierarchal as per logic.
                pass 
            
            if ds_id:
                 table_id = self._resolve_table_id(ds_id, table_slug)
                 if not table_id:
                     return [] # Table not found in this DS -> No results
                 filters['table_id'] = table_id
            else:
                 # If user provided table_slug but NO datasource_slug, and we need DS to resolve table?
                 # Current logic required ds_id for table resolution.
                 # If we assume global uniqueness of table slugs (which models enforce), we could resolve globaly.
                 # But let's stick to the existing strict hierarchy logic for now.
                 pass

        if ds_id and 'table_id' not in filters:
            # Filter by datasource only -> Requires JOIN
            base_stmt = select(ColumnNode).join(TableNode).where(TableNode.datasource_id == ds_id)
        
        hits = self._generic_search(ColumnNode, query, filters, limit, base_stmt=base_stmt)
        return [
            ColumnSearchResult(
                table_slug=hit['entity'].table.slug, # N+1 but okay for 10 items
                slug=hit['entity'].slug,
                type=hit['entity'].data_type,
                description=hit['entity'].description
            )
            for hit in hits
        ]

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
            # Re-fetch or rely on lazy loading (which uses un-aliased models? careful).
            # The query returned SchemaEdge objects. Accessing .source_column might trigger lazy load.
            # Lazy load should work fine.
            
            # Format: table.column
            src = f"{edge.source_column.table.slug}.{edge.source_column.slug}"
            tgt = f"{edge.target_column.table.slug}.{edge.target_column.slug}"
            output.append(EdgeSearchResult(
                source=src,
                target=tgt,
                type=edge.relationship_type.value,
                description=edge.description
            ))
        return output

    # -------------------------------------------------------------------------
    # 6. Metrics
    # -------------------------------------------------------------------------
    def search_metrics(self, query: str, datasource_slug: Optional[str], limit: int = 10) -> List[MetricSearchResult]:
        filters = {}
        if datasource_slug:
            ds_id = self._resolve_datasource_id(datasource_slug)
            if ds_id:
                filters['datasource_id'] = ds_id
        
        hits = self._generic_search(SemanticMetric, query, filters, limit)
        return [
            MetricSearchResult(
                slug=hit['entity'].slug,
                name=hit['entity'].name,
                sql_snippet=hit['entity'].calculation_sql,
                tables_involved=[]
            )
            for hit in hits
        ]

    # -------------------------------------------------------------------------
    # 7. Synonyms
    # -------------------------------------------------------------------------
    def search_synonyms(self, query: str, datasource_slug: Optional[str], limit: int = 10) -> List[SynonymSearchResult]:
        hits = self._generic_search(SemanticSynonym, query, {}, limit)
        return [
            SynonymSearchResult(
                term=hit['entity'].term,
                # We need to find the slug of the target. logic depends on target_type.
                # For efficiency, we might just return the ID or do a quick lookup.
                # Let's just return the term and type for now as the schema requires 'maps_to_slug'.
                maps_to_slug="unknown", # TODO: Resolve target slug
                target_type=hit['entity'].target_type.value
            )
            for hit in hits
        ]

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
            ContextRuleSearchResult(
                slug=hit['entity'].slug,
                rule_text=hit['entity'].rule_text
            )
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
        return [
            LowCardinalityValueSearchResult(
                value_raw=hit['entity'].value_raw,
                label=hit['entity'].value_label,
                column_slug=hit['entity'].column.slug,
                table_slug=hit['entity'].column.table.slug
            )
            for hit in hits
        ]


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
