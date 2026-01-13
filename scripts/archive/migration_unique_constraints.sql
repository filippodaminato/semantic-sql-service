-- Migration: Constraint Unici Mancanti
-- Aggiunge constraint unici per prevenire duplicati e garantire integrità dei dati
-- Tutti i constraint sono idempotenti (IF NOT EXISTS dove possibile)

-- ============================================================================
-- 1. TABLE_NODES: Unique constraint su (datasource_id, physical_name)
-- ============================================================================
-- Previene tabelle duplicate con lo stesso nome nello stesso datasource
-- Nota: Potrebbe fallire se esistono già duplicati. Verificare prima con:
-- SELECT datasource_id, physical_name, COUNT(*) 
-- FROM table_nodes 
-- GROUP BY datasource_id, physical_name 
-- HAVING COUNT(*) > 1;
CREATE UNIQUE INDEX IF NOT EXISTS idx_table_nodes_datasource_physical_name_unique 
ON table_nodes (datasource_id, physical_name);

-- ============================================================================
-- 2. COLUMN_NODES: Unique constraint su (table_id, name)
-- ============================================================================
-- Previene colonne duplicate con lo stesso nome nella stessa tabella
-- Nota: Potrebbe fallire se esistono già duplicati. Verificare prima con:
-- SELECT table_id, name, COUNT(*) 
-- FROM column_nodes 
-- GROUP BY table_id, name 
-- HAVING COUNT(*) > 1;
CREATE UNIQUE INDEX IF NOT EXISTS idx_column_nodes_table_name_unique 
ON column_nodes (table_id, name);

-- ============================================================================
-- 3. SEMANTIC_SYNONYMS: Unique constraint su (term, target_type, target_id)
-- ============================================================================
-- Previene sinonimi duplicati che mappano lo stesso termine allo stesso target
-- Nota: Potrebbe fallire se esistono già duplicati. Verificare prima con:
-- SELECT term, target_type, target_id, COUNT(*) 
-- FROM semantic_synonyms 
-- GROUP BY term, target_type, target_id 
-- HAVING COUNT(*) > 1;
CREATE UNIQUE INDEX IF NOT EXISTS idx_semantic_synonyms_term_target_unique 
ON semantic_synonyms (term, target_type, target_id);

-- ============================================================================
-- 4. LOW_CARDINALITY_VALUES: Unique constraint su (column_id, value_raw)
-- ============================================================================
-- Previene valori duplicati per la stessa colonna
-- Nota: Potrebbe fallire se esistono già duplicati. Verificare prima con:
-- SELECT column_id, value_raw, COUNT(*) 
-- FROM low_cardinality_values 
-- GROUP BY column_id, value_raw 
-- HAVING COUNT(*) > 1;
CREATE UNIQUE INDEX IF NOT EXISTS idx_low_cardinality_values_column_value_unique 
ON low_cardinality_values (column_id, value_raw);

-- ============================================================================
-- 5. SCHEMA_EDGES: Unique constraint su (source_column_id, target_column_id)
-- ============================================================================
-- Previene edge duplicati tra le stesse colonne
-- Nota: Potrebbe fallire se esistono già duplicati. Verificare prima con:
-- SELECT source_column_id, target_column_id, COUNT(*) 
-- FROM schema_edges 
-- GROUP BY source_column_id, target_column_id 
-- HAVING COUNT(*) > 1;
CREATE UNIQUE INDEX IF NOT EXISTS idx_schema_edges_columns_unique 
ON schema_edges (source_column_id, target_column_id);

-- ============================================================================
-- Note per Risoluzione Duplicati
-- ============================================================================
-- Se le migration falliscono per duplicati esistenti:
-- 1. Identificare i duplicati con le query sopra
-- 2. Decidere quale record mantenere (es. più recente, più completo)
-- 3. Eliminare i duplicati prima di eseguire la migration
-- 4. Esempio script di pulizia:
--    DELETE FROM table_nodes t1
--    USING table_nodes t2
--    WHERE t1.id < t2.id 
--      AND t1.datasource_id = t2.datasource_id 
--      AND t1.physical_name = t2.physical_name;
