ALTER TABLE semantic_synonyms ADD COLUMN IF NOT EXISTS embedding vector(1536);
ALTER TABLE semantic_synonyms ADD COLUMN IF NOT EXISTS embedding_hash VARCHAR(64);
