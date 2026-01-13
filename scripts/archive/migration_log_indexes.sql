-- Migration: Indici Temporali per Tabelle di Log
-- Le tabelle GenerationTrace e AmbiguityLog cresceranno nel tempo
-- Indici temporali ottimizzano query che filtrano per data/ora
-- Tutti gli indici sono idempotenti (IF NOT EXISTS)

-- ============================================================================
-- 1. GENERATION_TRACES: Indice su created_at
-- ============================================================================
-- Ottimizza query che filtrano per data creazione (query recenti, range di date)
-- Pattern query: WHERE created_at >= ? ORDER BY created_at DESC
CREATE INDEX IF NOT EXISTS idx_generation_traces_created_at 
ON generation_traces (created_at DESC);

-- Indice composito per query che filtrano per feedback e data
-- Pattern query: WHERE user_feedback IS NOT NULL ORDER BY created_at DESC
CREATE INDEX IF NOT EXISTS idx_generation_traces_feedback_created 
ON generation_traces (user_feedback, created_at DESC) 
WHERE user_feedback IS NOT NULL;

-- Indice per query che filtrano per errori
-- Pattern query: WHERE error_message IS NOT NULL ORDER BY created_at DESC
CREATE INDEX IF NOT EXISTS idx_generation_traces_errors_created 
ON generation_traces (created_at DESC) 
WHERE error_message IS NOT NULL;

-- ============================================================================
-- 2. AMBIGUITY_LOGS: Indice su created_at
-- ============================================================================
-- Ottimizza query che filtrano per data creazione
-- Pattern query: WHERE created_at >= ? ORDER BY created_at DESC
CREATE INDEX IF NOT EXISTS idx_ambiguity_logs_created_at 
ON ambiguity_logs (created_at DESC);

-- Indice per query che filtrano per log con risoluzione
-- Pattern query: WHERE user_resolution IS NOT NULL ORDER BY created_at DESC
CREATE INDEX IF NOT EXISTS idx_ambiguity_logs_resolved_created 
ON ambiguity_logs (created_at DESC) 
WHERE user_resolution IS NOT NULL;

-- ============================================================================
-- 3. Indici per Partitioning Futuro (Preparazione)
-- ============================================================================
-- Se le tabelle crescono molto (>10M righe), considerare partitioning per data
-- Questi indici supportano future strategie di partitioning

-- Per generation_traces: partitioning mensile
-- Esempio futuro: PARTITION BY RANGE (created_at)

-- Per ambiguity_logs: partitioning mensile
-- Esempio futuro: PARTITION BY RANGE (created_at)

-- ============================================================================
-- 4. Politica di Retention (Raccomandazione)
-- ============================================================================
-- Considerare di implementare retention policy per evitare crescita infinita:
--
-- Esempio per generation_traces (mantieni ultimi 90 giorni):
-- DELETE FROM generation_traces 
-- WHERE created_at < NOW() - INTERVAL '90 days';
--
-- Esempio per ambiguity_logs (mantieni ultimi 180 giorni):
-- DELETE FROM ambiguity_logs 
-- WHERE created_at < NOW() - INTERVAL '180 days';
--
-- Implementare come:
-- 1. Scheduled job (cron, pg_cron extension)
-- 2. Trigger periodico
-- 3. Task asincrono nell'applicazione

-- ============================================================================
-- 5. Query di Monitoraggio
-- ============================================================================
-- Monitorare la crescita delle tabelle:
-- SELECT 
--     schemaname,
--     tablename,
--     pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
--     n_live_tup AS row_count
-- FROM pg_stat_user_tables
-- WHERE tablename IN ('generation_traces', 'ambiguity_logs')
-- ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
