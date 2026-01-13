-- Add embedding_hash column to all searchable tables

ALTER TABLE datasources ADD COLUMN IF NOT EXISTS embedding_hash VARCHAR(64);
ALTER TABLE table_nodes ADD COLUMN IF NOT EXISTS embedding_hash VARCHAR(64);
ALTER TABLE column_nodes ADD COLUMN IF NOT EXISTS embedding_hash VARCHAR(64);
ALTER TABLE semantic_metrics ADD COLUMN IF NOT EXISTS embedding_hash VARCHAR(64);
ALTER TABLE semantic_synonyms ADD COLUMN IF NOT EXISTS embedding_hash VARCHAR(64);
ALTER TABLE column_context_rules ADD COLUMN IF NOT EXISTS embedding_hash VARCHAR(64);
ALTER TABLE low_cardinality_values ADD COLUMN IF NOT EXISTS embedding_hash VARCHAR(64);
ALTER TABLE golden_sql ADD COLUMN IF NOT EXISTS embedding_hash VARCHAR(64);
