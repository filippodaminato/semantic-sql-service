-- 1. Add columns (nullable first)
ALTER TABLE table_nodes ADD COLUMN IF NOT EXISTS slug VARCHAR(255);
ALTER TABLE column_nodes ADD COLUMN IF NOT EXISTS slug VARCHAR(255);
ALTER TABLE semantic_metrics ADD COLUMN IF NOT EXISTS slug VARCHAR(255);
ALTER TABLE semantic_synonyms ADD COLUMN IF NOT EXISTS slug VARCHAR(255);
ALTER TABLE column_context_rules ADD COLUMN IF NOT EXISTS slug VARCHAR(255);
ALTER TABLE low_cardinality_values ADD COLUMN IF NOT EXISTS slug VARCHAR(255);
ALTER TABLE golden_sql ADD COLUMN IF NOT EXISTS slug VARCHAR(255);

-- 2. Truncate tables to allow setting NOT NULL / Unique without conflicts
TRUNCATE TABLE golden_sql CASCADE;
TRUNCATE TABLE low_cardinality_values CASCADE;
TRUNCATE TABLE column_context_rules CASCADE;
TRUNCATE TABLE semantic_synonyms CASCADE;
TRUNCATE TABLE semantic_metrics CASCADE;
TRUNCATE TABLE schema_edges CASCADE;
TRUNCATE TABLE column_nodes CASCADE;
TRUNCATE TABLE table_nodes CASCADE;
TRUNCATE TABLE datasources CASCADE;

-- 3. Add Constraints
-- Table Nodes
CREATE UNIQUE INDEX IF NOT EXISTS idx_table_nodes_slug ON table_nodes (slug);
ALTER TABLE table_nodes ALTER COLUMN slug SET NOT NULL;

-- Column Nodes
CREATE UNIQUE INDEX IF NOT EXISTS idx_column_nodes_slug ON column_nodes (slug);
ALTER TABLE column_nodes ALTER COLUMN slug SET NOT NULL;

-- Metrics
CREATE UNIQUE INDEX IF NOT EXISTS idx_semantic_metrics_slug ON semantic_metrics (slug);
ALTER TABLE semantic_metrics ALTER COLUMN slug SET NOT NULL;

-- Synonyms
CREATE UNIQUE INDEX IF NOT EXISTS idx_semantic_synonyms_slug ON semantic_synonyms (slug);
ALTER TABLE semantic_synonyms ALTER COLUMN slug SET NOT NULL;

-- Rules
CREATE UNIQUE INDEX IF NOT EXISTS idx_column_context_rules_slug ON column_context_rules (slug);
ALTER TABLE column_context_rules ALTER COLUMN slug SET NOT NULL;

-- Values
CREATE UNIQUE INDEX IF NOT EXISTS idx_low_cardinality_values_slug ON low_cardinality_values (slug);
ALTER TABLE low_cardinality_values ALTER COLUMN slug SET NOT NULL;

-- Golden SQL
CREATE UNIQUE INDEX IF NOT EXISTS idx_golden_sql_slug ON golden_sql (slug);
ALTER TABLE golden_sql ALTER COLUMN slug SET NOT NULL;
