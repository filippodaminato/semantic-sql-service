-- Migration: Indici Compositi per Query Frequenti
-- Ottimizza le query che filtrano per combinazioni di colonne frequentemente usate insieme
-- Tutti gli indici sono idempotenti (IF NOT EXISTS)

-- ============================================================================
-- 1. TABLE_NODES: Indice composito per risoluzione slug con datasource
-- ============================================================================
-- Usato in: _resolve_table_id() quando datasource_id è fornito
-- Pattern query: WHERE datasource_id = ? AND slug = ?
CREATE INDEX IF NOT EXISTS idx_table_nodes_datasource_slug 
ON table_nodes (datasource_id, slug);

-- ============================================================================
-- 2. COLUMN_NODES: Indice composito per risoluzione slug con table
-- ============================================================================
-- Usato in: _resolve_column_id()
-- Pattern query: WHERE table_id = ? AND slug = ?
CREATE INDEX IF NOT EXISTS idx_column_nodes_table_slug 
ON column_nodes (table_id, slug);

-- ============================================================================
-- 3. GOLDEN_SQL: Indice composito per ordinamento cronologico per datasource
-- ============================================================================
-- Usato per: Query che ordinano golden_sql per datasource e data creazione
-- Pattern query: WHERE datasource_id = ? ORDER BY created_at DESC
CREATE INDEX IF NOT EXISTS idx_golden_sql_datasource_created 
ON golden_sql (datasource_id, created_at DESC);

-- ============================================================================
-- 4. SEMANTIC_METRICS: Indice composito per ricerca metriche per datasource
-- ============================================================================
-- Usato per: Query che filtrano metriche per datasource e cercano per nome
-- Pattern query: WHERE datasource_id = ? AND name ILIKE ?
CREATE INDEX IF NOT EXISTS idx_semantic_metrics_datasource_name 
ON semantic_metrics (datasource_id, name);

-- ============================================================================
-- 5. COLUMN_NODES: Indice composito per ricerca colonne per table e tipo
-- ============================================================================
-- Usato per: Query che filtrano colonne per table e verificano se è primary key
-- Pattern query: WHERE table_id = ? AND is_primary_key = ?
CREATE INDEX IF NOT EXISTS idx_column_nodes_table_primary_key 
ON column_nodes (table_id, is_primary_key) 
WHERE is_primary_key = true;

-- ============================================================================
-- 6. GOLDEN_SQL: Indice composito per complessità e verifica
-- ============================================================================
-- Usato per: Query che filtrano golden_sql per datasource, complessità e verifica
-- Pattern query: WHERE datasource_id = ? AND complexity_score = ? AND verified = true
CREATE INDEX IF NOT EXISTS idx_golden_sql_datasource_complexity_verified 
ON golden_sql (datasource_id, complexity_score, verified) 
WHERE verified = true;
