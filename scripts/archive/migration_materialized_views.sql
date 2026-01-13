-- Migration: Materialized View per Schema Edges
-- Pre-calcola JOIN complessi per migliorare performance di search_edges
-- La view può essere refreshata concorrentemente senza bloccare letture
-- Tutte le operazioni sono idempotenti (DROP IF EXISTS, CREATE OR REPLACE)

-- ============================================================================
-- 1. MATERIALIZED VIEW: Schema Edges Expanded
-- ============================================================================
-- Pre-calcola JOIN tra schema_edges, column_nodes e table_nodes
-- Include informazioni su source e target table per query veloci
DROP MATERIALIZED VIEW IF EXISTS mv_schema_edges_expanded;

CREATE MATERIALIZED VIEW mv_schema_edges_expanded AS
SELECT 
    se.id AS edge_id,
    se.source_column_id,
    se.target_column_id,
    se.relationship_type,
    se.is_inferred,
    se.description AS edge_description,
    se.context_note AS edge_context_note,
    se.created_at AS edge_created_at,
    
    -- Source column and table info
    sc.id AS source_column_id_full,
    sc.name AS source_column_name,
    sc.slug AS source_column_slug,
    sc.semantic_name AS source_column_semantic_name,
    st.id AS source_table_id,
    st.physical_name AS source_table_physical_name,
    st.slug AS source_table_slug,
    st.semantic_name AS source_table_semantic_name,
    st.datasource_id AS source_datasource_id,
    
    -- Target column and table info
    tc.id AS target_column_id_full,
    tc.name AS target_column_name,
    tc.slug AS target_column_slug,
    tc.semantic_name AS target_column_semantic_name,
    tt.id AS target_table_id,
    tt.physical_name AS target_table_physical_name,
    tt.slug AS target_table_slug,
    tt.semantic_name AS target_table_semantic_name,
    tt.datasource_id AS target_datasource_id
    
FROM schema_edges se
JOIN column_nodes sc ON se.source_column_id = sc.id
JOIN table_nodes st ON sc.table_id = st.id
JOIN column_nodes tc ON se.target_column_id = tc.id
JOIN table_nodes tt ON tc.table_id = tt.id;

-- ============================================================================
-- 2. Indici sulla Materialized View
-- ============================================================================
-- Indici per le query più comuni su search_edges

-- Indice per filtro per datasource (source)
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_edges_edge_id 
ON mv_schema_edges_expanded (edge_id);

-- Indice per filtro per datasource (source)
CREATE INDEX IF NOT EXISTS idx_mv_edges_source_datasource 
ON mv_schema_edges_expanded (source_datasource_id);

-- Indice per filtro per datasource (target)
CREATE INDEX IF NOT EXISTS idx_mv_edges_target_datasource 
ON mv_schema_edges_expanded (target_datasource_id);

-- Indice per filtro per table slug (source o target)
CREATE INDEX IF NOT EXISTS idx_mv_edges_source_table_slug 
ON mv_schema_edges_expanded (source_table_slug);

CREATE INDEX IF NOT EXISTS idx_mv_edges_target_table_slug 
ON mv_schema_edges_expanded (target_table_slug);

-- Indice composito per query che filtrano per entrambe le tabelle
CREATE INDEX IF NOT EXISTS idx_mv_edges_table_slugs 
ON mv_schema_edges_expanded (source_table_slug, target_table_slug);

-- Indice per full-text search su description
CREATE INDEX IF NOT EXISTS idx_mv_edges_description_fts 
ON mv_schema_edges_expanded USING GIN (to_tsvector('simple', edge_description))
WHERE edge_description IS NOT NULL;

-- ============================================================================
-- 3. Funzione per Refresh Concorrente
-- ============================================================================
-- Crea una funzione helper per refresh concorrente della view
-- Il refresh concorrente non blocca le letture ma richiede indici unici
CREATE OR REPLACE FUNCTION refresh_schema_edges_view()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_schema_edges_expanded;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 4. Trigger per Auto-Refresh (Opzionale)
-- ============================================================================
-- Opzione 1: Refresh manuale (consigliato per controllo)
-- Eseguire: SELECT refresh_schema_edges_view();
--
-- Opzione 2: Auto-refresh su modifiche (più complesso, richiede trigger)
-- Nota: I trigger su materialized views sono limitati, meglio refresh manuale
-- o scheduled job (cron, pg_cron extension)

-- ============================================================================
-- Note per Utilizzo
-- ============================================================================
-- 1. Refresh iniziale dopo creazione:
--    REFRESH MATERIALIZED VIEW mv_schema_edges_expanded;
--
-- 2. Refresh concorrente (non blocca letture, richiede indici unici):
--    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_schema_edges_expanded;
--
-- 3. La view va refreshata quando:
--    - Vengono aggiunti/modificati schema_edges
--    - Vengono modificati column_nodes o table_nodes collegati
--
-- 4. Per integrare nella API, modificare search_edges() in retrieval.py
--    per usare la materialized view invece di JOIN multipli

-- ============================================================================
-- 5. Query di Esempio per Verifica
-- ============================================================================
-- Verificare che la view contenga tutti gli edges:
-- SELECT COUNT(*) FROM schema_edges;
-- SELECT COUNT(*) FROM mv_schema_edges_expanded;
-- (Dovrebbero essere uguali dopo refresh)
