-- Migration: Indici per Foreign Keys
-- PostgreSQL non crea automaticamente indici su foreign keys, ma sono essenziali
-- per le performance delle JOIN e dei filtri
-- Tutti gli indici sono idempotenti (IF NOT EXISTS)

-- ============================================================================
-- 1. TABLE_NODES: Indice su datasource_id
-- ============================================================================
-- Usato in: Filtri per datasource, JOIN con datasources
-- Pattern query: WHERE datasource_id = ?, JOIN datasources ON ...
CREATE INDEX IF NOT EXISTS idx_table_nodes_datasource_id 
ON table_nodes (datasource_id);

-- ============================================================================
-- 2. COLUMN_NODES: Indice su table_id
-- ============================================================================
-- Usato in: Filtri per table, JOIN con table_nodes
-- Pattern query: WHERE table_id = ?, JOIN table_nodes ON ...
CREATE INDEX IF NOT EXISTS idx_column_nodes_table_id 
ON column_nodes (table_id);

-- ============================================================================
-- 3. SCHEMA_EDGES: Indici su source_column_id e target_column_id
-- ============================================================================
-- Usato in: JOIN multipli per ricerca edges, query su relazioni
-- Pattern query: JOIN column_nodes ON source_column_id = ..., JOIN column_nodes ON target_column_id = ...
CREATE INDEX IF NOT EXISTS idx_schema_edges_source_column 
ON schema_edges (source_column_id);

CREATE INDEX IF NOT EXISTS idx_schema_edges_target_column 
ON schema_edges (target_column_id);

-- Indice composito per query che filtrano per entrambe le colonne
CREATE INDEX IF NOT EXISTS idx_schema_edges_columns 
ON schema_edges (source_column_id, target_column_id);

-- ============================================================================
-- 4. SEMANTIC_METRICS: Indice su datasource_id
-- ============================================================================
-- Usato in: Filtri per datasource nelle ricerche metriche
-- Pattern query: WHERE datasource_id = ?
CREATE INDEX IF NOT EXISTS idx_semantic_metrics_datasource_id 
ON semantic_metrics (datasource_id);

-- ============================================================================
-- 5. GOLDEN_SQL: Indice su datasource_id
-- ============================================================================
-- Usato in: Filtri per datasource nelle ricerche golden SQL
-- Pattern query: WHERE datasource_id = ?
CREATE INDEX IF NOT EXISTS idx_golden_sql_datasource_id 
ON golden_sql (datasource_id);

-- ============================================================================
-- 6. COLUMN_CONTEXT_RULES: Indice su column_id
-- ============================================================================
-- Usato in: Filtri per column, JOIN con column_nodes
-- Pattern query: WHERE column_id = ?, JOIN column_nodes ON ...
CREATE INDEX IF NOT EXISTS idx_column_context_rules_column_id 
ON column_context_rules (column_id);

-- ============================================================================
-- 7. LOW_CARDINALITY_VALUES: Indice su column_id
-- ============================================================================
-- Usato in: Filtri per column, JOIN con column_nodes
-- Pattern query: WHERE column_id = ?, JOIN column_nodes ON ...
CREATE INDEX IF NOT EXISTS idx_low_cardinality_values_column_id 
ON low_cardinality_values (column_id);
