-- Migration: Cambia tutti i search_vector da 'english' a 'simple'
-- per supportare meglio le ricerche multilingua (italiano, francese, tedesco, ecc.)
--
-- La configurazione 'simple' di PostgreSQL non applica stemming o stop words,
-- rendendola più universale per lingue diverse dall'inglese.
--
-- Nota: Le colonne COMPUTED non possono essere modificate direttamente,
-- quindi dobbiamo eliminare e ricreare ogni colonna.

-- ============================================================================
-- 1. DATASOURCES
-- ============================================================================
ALTER TABLE datasources DROP COLUMN IF EXISTS search_vector;
ALTER TABLE datasources 
ADD COLUMN search_vector TSVECTOR 
GENERATED ALWAYS AS (to_tsvector('simple', description || ' ' || context_signature)) STORED;
CREATE INDEX IF NOT EXISTS idx_datasources_search_vector 
ON datasources USING GIN (search_vector);

-- ============================================================================
-- 2. TABLE_NODES
-- ============================================================================
ALTER TABLE table_nodes DROP COLUMN IF EXISTS search_vector;
ALTER TABLE table_nodes 
ADD COLUMN search_vector TSVECTOR 
GENERATED ALWAYS AS (to_tsvector('simple', semantic_name || ' ' || description)) STORED;
CREATE INDEX IF NOT EXISTS idx_table_nodes_search_vector 
ON table_nodes USING GIN (search_vector);

-- ============================================================================
-- 3. COLUMN_NODES
-- ============================================================================
ALTER TABLE column_nodes DROP COLUMN IF EXISTS search_vector;
ALTER TABLE column_nodes 
ADD COLUMN search_vector TSVECTOR 
GENERATED ALWAYS AS (to_tsvector('simple', semantic_name || ' ' || description || ' ' || COALESCE(context_note, ''))) STORED;
CREATE INDEX IF NOT EXISTS idx_column_nodes_search_vector 
ON column_nodes USING GIN (search_vector);

-- ============================================================================
-- 4. SEMANTIC_METRICS
-- ============================================================================
ALTER TABLE semantic_metrics DROP COLUMN IF EXISTS search_vector;
ALTER TABLE semantic_metrics 
ADD COLUMN search_vector TSVECTOR 
GENERATED ALWAYS AS (to_tsvector('simple', name || ' ' || description)) STORED;
CREATE INDEX IF NOT EXISTS idx_semantic_metrics_search_vector 
ON semantic_metrics USING GIN (search_vector);

-- ============================================================================
-- 5. SEMANTIC_SYNONYMS
-- ============================================================================
ALTER TABLE semantic_synonyms DROP COLUMN IF EXISTS search_vector;
ALTER TABLE semantic_synonyms 
ADD COLUMN search_vector TSVECTOR 
GENERATED ALWAYS AS (to_tsvector('simple', term)) STORED;
CREATE INDEX IF NOT EXISTS idx_semantic_synonyms_search_vector 
ON semantic_synonyms USING GIN (search_vector);

-- ============================================================================
-- 6. COLUMN_CONTEXT_RULES
-- ============================================================================
ALTER TABLE column_context_rules DROP COLUMN IF EXISTS search_vector;
ALTER TABLE column_context_rules 
ADD COLUMN search_vector TSVECTOR 
GENERATED ALWAYS AS (to_tsvector('simple', rule_text)) STORED;
CREATE INDEX IF NOT EXISTS idx_column_context_rules_search_vector 
ON column_context_rules USING GIN (search_vector);

-- ============================================================================
-- 7. LOW_CARDINALITY_VALUES
-- ============================================================================
ALTER TABLE low_cardinality_values DROP COLUMN IF EXISTS search_vector;
ALTER TABLE low_cardinality_values 
ADD COLUMN search_vector TSVECTOR 
GENERATED ALWAYS AS (to_tsvector('simple', value_label)) STORED;
CREATE INDEX IF NOT EXISTS idx_low_cardinality_values_search_vector 
ON low_cardinality_values USING GIN (search_vector);

-- ============================================================================
-- 8. GOLDEN_SQL (già aggiornato in migration precedente, ma incluso per completezza)
-- ============================================================================
ALTER TABLE golden_sql DROP COLUMN IF EXISTS search_vector;
ALTER TABLE golden_sql 
ADD COLUMN search_vector TSVECTOR 
GENERATED ALWAYS AS (to_tsvector('simple', prompt_text)) STORED;
CREATE INDEX IF NOT EXISTS idx_golden_sql_search_vector 
ON golden_sql USING GIN (search_vector);
