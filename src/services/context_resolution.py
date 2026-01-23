"""
Context Resolution Service.
Implements the Unified Batch Execution logic for resolving context from search queries.
"""
from typing import List, Dict, Set, Any
from uuid import UUID
from collections import defaultdict

from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select

from ..db.models import (
    Datasource, TableNode, ColumnNode, SchemaEdge, SemanticMetric, GoldenSQL,
    ColumnContextRule, LowCardinalityValue
)
from ..schemas.discovery import (
    ContextSearchItem, ContextSearchEntity,
    ContextResolutionResponse,
    ResolvedDatasource, ResolvedTable, ResolvedColumn,
    MetricSearchResult, GoldenSQLResult, EdgeSearchResult,
    ContextRuleSearchResult, LowCardinalityValueSearchResult
)
from .search import SearchService

class ContextResolver:
    """
    Orchestrates the resolution of context from mixed search queries.
    Pipeline:
    A. Scatter-Gather (Parallel Search)
    B. Hierarchical Inference (Resolve Parents)
    C. Bulk Fetch (Eager Load Graph)
    """
    def __init__(self, db: Session):
        self.db = db
        self.search_service = SearchService(db)

    def resolve(self, items: List[ContextSearchItem]) -> ContextResolutionResponse:
        """
        Main entry point for context resolution.
        """
        # Stage A: Search
        # Collect raw hits for each entity type
        raw_hits = self._stage_a_scatter_gather(items)

        # Stage B: Inference
        # Resolve all hits to their parent containers (Table -> Datasource)
        # and collect specific IDs to fetch
        resolved_ids = self._stage_b_inference(raw_hits)

        # Stage C: Bulk Fetch
        # Efficiently fetch the graph structure
        graph = self._stage_c_bulk_fetch(resolved_ids)

        return ContextResolutionResponse(graph=graph)

    def _stage_a_scatter_gather(self, items: List[ContextSearchItem]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Execute searches for each item based on its entity type.
        """
        results = defaultdict(list)
        
        for item in items:
            query = item.search_text
            entity_type = item.entity

            # We assume a default limit for resolution hints, e.g., 5 top hits per query
            # to avoid polluting the context with irrelevant matches.
            LIMIT = 5 
            
            hits = []
            if entity_type == ContextSearchEntity.TABLES:
                # We use the generic search from service but we want raw hits first 
                # (though service returns formatted objects, inner method returns dicts)
                # We'll use the public methods which return Pydantic models, 
                # but we actually need the IDs mostly. 
                # Let's trust the service methods.
                res = self.search_service.search_tables(query, None, page=1, limit=LIMIT, min_ratio_to_best=item.min_ratio_to_best)
                hits = [{'type': 'TABLE', 'entity': x} for x in res.items]
                
            elif entity_type == ContextSearchEntity.COLUMNS:
                res = self.search_service.search_columns(query, None, None, page=1, limit=LIMIT, min_ratio_to_best=item.min_ratio_to_best)
                hits = [{'type': 'COLUMN', 'entity': x} for x in res.items]

            elif entity_type == ContextSearchEntity.METRICS:
                res = self.search_service.search_metrics(query, None, page=1, limit=LIMIT, min_ratio_to_best=item.min_ratio_to_best)
                hits = [{'type': 'METRIC', 'entity': x} for x in res.items]

            elif entity_type == ContextSearchEntity.GOLDEN_SQL:
                res = self.search_service.search_golden_sql(query, None, page=1, limit=LIMIT, min_ratio_to_best=item.min_ratio_to_best)
                hits = [{'type': 'GOLDEN_SQL', 'entity': x} for x in res.items]
            
            elif entity_type == ContextSearchEntity.EDGES:
                res = self.search_service.search_edges(query, None, None, page=1, limit=LIMIT, min_ratio_to_best=item.min_ratio_to_best)
                hits = [{'type': 'EDGE', 'entity': x} for x in res.items]
            
            elif entity_type == ContextSearchEntity.CONTEXT_RULES:
                res = self.search_service.search_context_rules(query, None, None, page=1, limit=LIMIT, min_ratio_to_best=item.min_ratio_to_best)
                hits = [{'type': 'CONTEXT_RULE', 'entity': x} for x in res.items]

            elif entity_type == ContextSearchEntity.LOW_CARDINALITY_VALUES:
                res = self.search_service.search_low_cardinality_values(query, None, None, None, page=1, limit=LIMIT, min_ratio_to_best=item.min_ratio_to_best)
                hits = [{'type': 'VALUE', 'entity': x} for x in res.items]

            elif entity_type == ContextSearchEntity.DATASOURCES:
                res = self.search_service.search_datasources(query, page=1, limit=LIMIT, min_ratio_to_best=item.min_ratio_to_best)
                hits = [{'type': 'DATASOURCE', 'entity': x} for x in res.items]

            # Accumulate results
            results[entity_type.value].extend(hits)
            
        return results

        return {
            "table_ids": table_ids,
            "column_ids": set(), # Will be populated if we track columns
            "rule_ids": set(),
            "value_ids": set(),
            "datasource_ids": datasource_ids,
            "metric_ids": metric_ids,
            "golden_sql_ids": golden_sql_ids
        }

    def _stage_b_inference(self, raw_hits: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        Resolve orphan entities to their parents.
        Returns unique sets of IDs to fetch and a map of scores.
        """
        table_ids = set()
        column_ids = set()
        rule_ids = set()
        value_ids = set()
        datasource_ids = set()
        metric_ids = set()
        golden_sql_ids = set()
        edge_ids = set()
        
        scores: Dict[UUID, float] = {}

        def add_score(entity):
             if hasattr(entity, 'score') and entity.score is not None:
                 # If multiple hits for same entity, keep max score? 
                 # Or just overwrite. Overwrite is fine for now usually irrelevant.
                 # Actually max is better if we have duplicate hits.
                 current = scores.get(entity.id, 0.0)
                 if entity.score > current:
                     scores[entity.id] = entity.score

        # 1. Process Tables
        if "tables" in raw_hits:
            for hit in raw_hits["tables"]:
                table = hit['entity']
                table_ids.add(table.id)
                datasource_ids.add(table.datasource_id)
                add_score(table)

        # 2. Process Columns (Resolve to Table)
        if "columns" in raw_hits:
            for hit in raw_hits["columns"]:
                col = hit['entity']
                column_ids.add(col.id)
                table_ids.add(col.table_id)
                add_score(col)

        # 3. Process Metrics (Resolve required tables)
        if "metrics" in raw_hits:
            for hit in raw_hits["metrics"]:
                metric = hit['entity']
                metric_ids.add(metric.id)
                if metric.datasource_id:
                    datasource_ids.add(metric.datasource_id)
                add_score(metric)

        # 4. Process Golden SQL
        if "golden_sql" in raw_hits:
            for hit in raw_hits["golden_sql"]:
                gs = hit['entity']
                golden_sql_ids.add(gs.id)
                if gs.datasource_id:
                    datasource_ids.add(gs.datasource_id)
                add_score(gs)

        # 5. Process Datasources (Direct)
        if "datasources" in raw_hits:
            for hit in raw_hits["datasources"]:
                ds = hit['entity']
                datasource_ids.add(ds.id)
                add_score(ds)

        # 6. Process Context Rules
        if "context_rules" in raw_hits:
            for hit in raw_hits["context_rules"]:
                rule = hit['entity']
                rule_ids.add(rule.id)
                if rule.column_id:
                    column_ids.add(rule.column_id)
                add_score(rule)
        
        # 7. Process Low Cardinality Values
        if "low_cardinality_values" in raw_hits:
            for hit in raw_hits["low_cardinality_values"]:
                val = hit['entity']
                value_ids.add(val.id)
                if val.column_id:
                    column_ids.add(val.column_id)
                add_score(val)

        # 8. Process Edges
        if "edges" in raw_hits:
            for hit in raw_hits["edges"]:
                edge = hit['entity']
                edge_ids.add(edge.id)
                add_score(edge)

        return {
            "table_ids": table_ids,
            "column_ids": column_ids,
            "rule_ids": rule_ids,
            "value_ids": value_ids,
            "datasource_ids": datasource_ids,
            "metric_ids": metric_ids,
            "golden_sql_ids": golden_sql_ids,
            "edge_ids": edge_ids,
            "scores": scores
        }

    def _stage_c_bulk_fetch(self, resolved_ids: Dict[str, Any]) -> List[ResolvedDatasource]:
        """
        Bulk fetch the graph structure, ensuring bottom-up resolution.
        """
        known_table_ids = resolved_ids.get("table_ids", set())
        known_column_ids = resolved_ids.get("column_ids", set())
        known_rule_ids = resolved_ids.get("rule_ids", set())
        known_value_ids = resolved_ids.get("value_ids", set())
        known_ds_ids = resolved_ids.get("datasource_ids", set())
        metric_ids = resolved_ids.get("metric_ids", set())
        golden_sql_ids = resolved_ids.get("golden_sql_ids", set())
        known_edge_ids = resolved_ids.get("edge_ids", set())
        scores = resolved_ids.get("scores", {})

        # ---------------------------------------------------------
        # 1. Fetch Leaf Nodes (Rules, Values) -> Bubble up to Columns
        # ---------------------------------------------------------
        fetched_rules = []
        if known_rule_ids:
            fetched_rules = self.db.query(ColumnContextRule).filter(ColumnContextRule.id.in_(known_rule_ids)).all()
            for r in fetched_rules:
                known_column_ids.add(r.column_id)

        fetched_values = []
        if known_value_ids:
            fetched_values = self.db.query(LowCardinalityValue).filter(LowCardinalityValue.id.in_(known_value_ids)).all()
            for v in fetched_values:
                known_column_ids.add(v.column_id)

        # ---------------------------------------------------------
        # 1.1 Fetch Edges (if explicitly requested) -> Bubble up to Columns
        # ---------------------------------------------------------
        fetched_edges = []
        if known_edge_ids:
            fetched_edges = self.db.query(SchemaEdge).filter(SchemaEdge.id.in_(known_edge_ids)).all()
            for e in fetched_edges:
                known_column_ids.add(e.source_column_id)
                known_column_ids.add(e.target_column_id)

        # ---------------------------------------------------------
        # 2. Fetch Columns -> Bubble up to Tables
        # ---------------------------------------------------------
        fetched_columns = []
        if known_column_ids:
            fetched_columns = self.db.query(ColumnNode).filter(ColumnNode.id.in_(known_column_ids)).all()
            for c in fetched_columns:
                known_table_ids.add(c.table_id)

        # ---------------------------------------------------------
        # 3. Fetch Tables -> Bubble up to Datasources
        # ---------------------------------------------------------
        fetched_tables = []
        if known_table_ids:
            fetched_tables = self.db.query(TableNode).filter(TableNode.id.in_(known_table_ids)).all()
            for t in fetched_tables:
                known_ds_ids.add(t.datasource_id)





        # ---------------------------------------------------------
        # 4. Fetch Metrics/GSQL -> Bubble up to Datasources
        # ---------------------------------------------------------
        metrics = []
        if metric_ids:
            metrics = self.db.query(SemanticMetric).filter(SemanticMetric.id.in_(metric_ids)).all()
            for m in metrics:
                if m.datasource_id:
                    known_ds_ids.add(m.datasource_id)

        golden_sqls = []
        if golden_sql_ids:
            golden_sqls = self.db.query(GoldenSQL).filter(GoldenSQL.id.in_(golden_sql_ids)).all()
            for g in golden_sqls:
                known_ds_ids.add(g.datasource_id)

        # ---------------------------------------------------------
        # 5. Fetch Datasources
        # ---------------------------------------------------------
        if not known_ds_ids:
            return []
        datasources = self.db.query(Datasource).filter(Datasource.id.in_(known_ds_ids)).all()

        # ---------------------------------------------------------
        # 6. Fetch Edges (Sub-graph strategy)
        # ---------------------------------------------------------
        # ---------------------------------------------------------
        # 6. Fetch Edges (Sub-graph strategy)
        # ---------------------------------------------------------
        ds_edges = defaultdict(list)
        if known_edge_ids:
            edges = self.db.query(SchemaEdge).filter(
                 SchemaEdge.id.in_(known_edge_ids)
             ).options(
                 selectinload(SchemaEdge.source_column).selectinload(ColumnNode.table),
                 selectinload(SchemaEdge.target_column).selectinload(ColumnNode.table)
             ).all()

            for e in edges:
                try:
                    # Ensure both tables are in context (they should be due to step 1.1)
                    if e.target_column.table_id in known_table_ids and e.source_column.table_id in known_table_ids:
                        src_slug = f"{e.source_column.table.slug}.{e.source_column.slug}"
                        tgt_slug = f"{e.target_column.table.slug}.{e.target_column.slug}"
                        ds_id = e.source_column.table.datasource_id
                        
                        ds_edges[ds_id].append(EdgeSearchResult(
                            id=e.id,
                            source_column_id=e.source_column_id,
                            target_column_id=e.target_column_id,
                            source=src_slug,
                            target=tgt_slug,
                            relationship_type=e.relationship_type.value,
                            is_inferred=e.is_inferred,
                            description=e.description,
                            context_note=e.context_note,
                            created_at=e.created_at,
                            score=scores.get(e.id)
                        ))
                except:
                    pass

        # ---------------------------------------------------------
        # 7. Assemble Hierarchy Manually
        # ---------------------------------------------------------
        
        # Organize children by parent
        cols_by_table = defaultdict(list)
        rules_by_col = defaultdict(list)
        vals_by_col = defaultdict(list)

        for r in fetched_rules:
            rules_by_col[r.column_id].append(r)
        
        for v in fetched_values:
            vals_by_col[v.column_id].append(v)
            
        for c in fetched_columns:
            # Build ResolvedColumn
            rules = [ContextRuleSearchResult(
                     id=r.id,
                     column_id=r.column_id,
                     column_slug=c.slug,
                     table_slug=c.table.slug if c.table else "unknown",
                     slug=r.slug,
                     rule_text=r.rule_text,
                     created_at=r.created_at,
                     score=scores.get(r.id)
            ) for r in rules_by_col[c.id]]

            values = [LowCardinalityValueSearchResult(
                     id=v.id,
                     column_id=v.column_id,
                     column_slug=c.slug,
                     table_slug=c.table.slug if c.table else "unknown",
                     value_raw=v.value_raw,
                     value_label=v.value_label,
                     created_at=v.created_at,
                     score=scores.get(v.id)
            ) for v in vals_by_col[c.id]]

            resolved_col = ResolvedColumn(
                id=c.id,
                table_id=c.table_id,
                table_slug="unknown", 
                slug=c.slug,
                name=c.name,
                semantic_name=c.semantic_name,
                data_type=c.data_type,
                is_primary_key=c.is_primary_key,
                description=c.description,
                context_note=c.context_note,
                created_at=c.created_at,
                updated_at=c.updated_at,
                context_rules=rules,
                nominal_values=values,
                score=scores.get(c.id)
            )
            cols_by_table[c.table_id].append(resolved_col)

        ds_tables = defaultdict(list)
        for t in fetched_tables:
            t_cols = cols_by_table[t.id]
            for col in t_cols:
                col.table_slug = t.slug
                for r in col.context_rules: r.table_slug = t.slug
                for v in col.nominal_values: v.table_slug = t.slug

            ds_tables[t.datasource_id].append(ResolvedTable(
                id=t.id,
                datasource_id=t.datasource_id,
                slug=t.slug,
                physical_name=t.physical_name,
                semantic_name=t.semantic_name,
                description=t.description,
                ddl_context=t.ddl_context,
                created_at=t.created_at,
                updated_at=t.updated_at,
                columns=t_cols,
                score=scores.get(t.id)
            ))
            
        ds_metrics = defaultdict(list)
        for m in metrics:
            item = MetricSearchResult.model_validate(m)
            item.score = scores.get(m.id)
            ds_metrics[m.datasource_id].append(item)
            
        ds_gsql = defaultdict(list)
        for g in golden_sqls:
            ds_gsql[g.datasource_id].append(GoldenSQLResult(
                id=g.id,
                datasource_id=g.datasource_id,
                prompt=g.prompt_text,
                sql=g.sql_query,
                complexity=g.complexity_score,
                verified=g.verified,
                score=scores.get(g.id, 1.0),
                created_at=g.created_at,
                updated_at=g.updated_at
            ))

        graph = []
        for ds in datasources:
            graph.append(ResolvedDatasource(
                id=ds.id,
                slug=ds.slug,
                name=ds.name,
                description=ds.description,
                engine=ds.engine.value,
                context_signature=ds.context_signature,
                created_at=ds.created_at,
                updated_at=ds.updated_at,
                tables=ds_tables[ds.id],
                metrics=ds_metrics[ds.id],
                golden_sqls=ds_gsql[ds.id],
                edges=ds_edges[ds.id],
                score=scores.get(ds.id)
            ))
            
        return graph
