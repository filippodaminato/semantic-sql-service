-- Migration: Indici Vectoriali HNSW per pgvector
-- HNSW (Hierarchical Navigable Small World) è l'algoritmo più performante
-- per ricerche di similarità vettoriale in pgvector
-- 
-- Configurazione:
-- - m = 16: Numero di connessioni bidirezionali per nodo (bilanciamento memoria/velocità)
-- - ef_construction = 64: Dimensione della lista candidati durante costruzione (qualità indice)
--
-- Nota: La creazione di questi indici può richiedere tempo su dataset grandi
-- Considerare di eseguirli durante maintenance window
-- Tutti gli indici sono idempotenti (IF NOT EXISTS)

-- Verifica che l'estensione pgvector sia installata
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================================
-- 1. DATASOURCES: Indice HNSW per embedding
-- ============================================================================
-- Usato in: Ricerche semantiche ibride su datasources
-- Operatore: vector_cosine_ops (cosine similarity - standard per embeddings)
CREATE INDEX IF NOT EXISTS idx_datasources_embedding_hnsw 
ON datasources USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- ============================================================================
-- 2. TABLE_NODES: Indice HNSW per embedding
-- ============================================================================
-- Usato in: Ricerche semantiche ibride su tabelle
CREATE INDEX IF NOT EXISTS idx_table_nodes_embedding_hnsw 
ON table_nodes USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- ============================================================================
-- 3. COLUMN_NODES: Indice HNSW per embedding
-- ============================================================================
-- Usato in: Ricerche semantiche ibride su colonne
CREATE INDEX IF NOT EXISTS idx_column_nodes_embedding_hnsw 
ON column_nodes USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- ============================================================================
-- 4. SEMANTIC_METRICS: Indice HNSW per embedding
-- ============================================================================
-- Usato in: Ricerche semantiche ibride su metriche
CREATE INDEX IF NOT EXISTS idx_semantic_metrics_embedding_hnsw 
ON semantic_metrics USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- ============================================================================
-- 5. SEMANTIC_SYNONYMS: Indice HNSW per embedding
-- ============================================================================
-- Usato in: Ricerche semantiche ibride su sinonimi
CREATE INDEX IF NOT EXISTS idx_semantic_synonyms_embedding_hnsw 
ON semantic_synonyms USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- ============================================================================
-- 6. COLUMN_CONTEXT_RULES: Indice HNSW per embedding
-- ============================================================================
-- Usato in: Ricerche semantiche ibride su regole di contesto
CREATE INDEX IF NOT EXISTS idx_column_context_rules_embedding_hnsw 
ON column_context_rules USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- ============================================================================
-- 7. GOLDEN_SQL: Indice HNSW per embedding
-- ============================================================================
-- Usato in: Ricerche semantiche ibride su golden SQL examples
CREATE INDEX IF NOT EXISTS idx_golden_sql_embedding_hnsw 
ON golden_sql USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- ============================================================================
-- Note per Performance Tuning
-- ============================================================================
-- Se le ricerche vettoriali sono ancora lente dopo questi indici:
-- 1. Aumentare m (es. 32) per migliore qualità ma più memoria
-- 2. Aumentare ef_construction (es. 128) per migliore qualità indice
-- 3. Considerare IVFFlat invece di HNSW per dataset molto grandi (>10M vettori)
--    Esempio IVFFlat: USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)
