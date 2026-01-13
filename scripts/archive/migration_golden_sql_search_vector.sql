-- Migration: Cambia search_vector di golden_sql da 'english' a 'simple'
-- per supportare meglio le ricerche in italiano e altre lingue

-- Nota: Le colonne COMPUTED non possono essere modificate direttamente,
-- quindi dobbiamo:
-- 1. Eliminare la colonna esistente
-- 2. Ricrearla con la nuova configurazione

-- Step 1: Elimina la colonna search_vector esistente
ALTER TABLE golden_sql DROP COLUMN IF EXISTS search_vector;

-- Step 2: Ricrea la colonna con configurazione 'simple'
ALTER TABLE golden_sql 
ADD COLUMN search_vector TSVECTOR 
GENERATED ALWAYS AS (to_tsvector('simple', prompt_text)) STORED;

-- Step 3: Ricrea l'indice GIN per la ricerca full-text
CREATE INDEX IF NOT EXISTS idx_golden_sql_search_vector 
ON golden_sql USING GIN (search_vector);
