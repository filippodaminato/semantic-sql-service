-- Migration: Indici Parziali per Query Frequenti
-- Indici parziali includono solo un subset delle righe (definito da WHERE clause)
-- Sono più piccoli e veloci degli indici completi quando si filtrano per valori specifici
-- Tutti gli indici sono idempotenti (IF NOT EXISTS)

-- ============================================================================
-- 1. GOLDEN_SQL: Indice parziale per golden SQL verificati
-- ============================================================================
-- Ottimizza query che filtrano solo per golden_sql verificati (verified = true)
-- Pattern query: WHERE datasource_id = ? AND verified = true ORDER BY complexity_score, created_at
CREATE INDEX IF NOT EXISTS idx_golden_sql_verified 
ON golden_sql (datasource_id, complexity_score, created_at DESC) 
WHERE verified = true;

-- ============================================================================
-- 2. COLUMN_NODES: Indice parziale per primary keys
-- ============================================================================
-- Ottimizza query che cercano primary keys di una tabella
-- Pattern query: WHERE table_id = ? AND is_primary_key = true
CREATE INDEX IF NOT EXISTS idx_column_nodes_primary_keys 
ON column_nodes (table_id, is_primary_key) 
WHERE is_primary_key = true;

-- ============================================================================
-- 3. SCHEMA_EDGES: Indice parziale per relazioni inferite
-- ============================================================================
-- Ottimizza query che distinguono tra relazioni fisiche e inferite
-- Pattern query: WHERE is_inferred = true/false
CREATE INDEX IF NOT EXISTS idx_schema_edges_inferred 
ON schema_edges (source_column_id, target_column_id) 
WHERE is_inferred = true;

CREATE INDEX IF NOT EXISTS idx_schema_edges_physical 
ON schema_edges (source_column_id, target_column_id) 
WHERE is_inferred = false;

-- ============================================================================
-- 4. SEMANTIC_METRICS: Indice parziale per metriche con required_tables
-- ============================================================================
-- Ottimizza query che filtrano metriche che richiedono tabelle specifiche
-- Pattern query: WHERE required_tables IS NOT NULL AND required_tables @> ?
-- Nota: Questo indice supporta query JSONB su required_tables
CREATE INDEX IF NOT EXISTS idx_semantic_metrics_with_tables 
ON semantic_metrics USING GIN (required_tables) 
WHERE required_tables IS NOT NULL;

-- ============================================================================
-- 5. GOLDEN_SQL: Indice parziale per complessità specifica
-- ============================================================================
-- Ottimizza query che filtrano per complessità specifica (es. complexity = 3)
-- Pattern query: WHERE datasource_id = ? AND complexity_score = 3 AND verified = true
-- Creiamo indici per le complessità più comuni (2, 3, 4)
CREATE INDEX IF NOT EXISTS idx_golden_sql_complexity_2 
ON golden_sql (datasource_id, created_at DESC) 
WHERE complexity_score = 2 AND verified = true;

CREATE INDEX IF NOT EXISTS idx_golden_sql_complexity_3 
ON golden_sql (datasource_id, created_at DESC) 
WHERE complexity_score = 3 AND verified = true;

CREATE INDEX IF NOT EXISTS idx_golden_sql_complexity_4 
ON golden_sql (datasource_id, created_at DESC) 
WHERE complexity_score = 4 AND verified = true;

-- ============================================================================
-- Note per Performance
-- ============================================================================
-- Gli indici parziali sono più efficienti quando:
-- 1. La condizione WHERE esclude una grande percentuale delle righe (>50%)
-- 2. Le query filtrano sempre per quella condizione
-- 3. L'indice è significativamente più piccolo dell'indice completo
--
-- Monitorare l'utilizzo con:
-- SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
-- FROM pg_stat_user_indexes
-- WHERE indexname LIKE 'idx_%_verified' OR indexname LIKE 'idx_%_primary_keys';
