-- Add computed search_vector columns and GIN indexes

-- Datasources
ALTER TABLE datasources 
ADD COLUMN IF NOT EXISTS search_vector tsvector 
GENERATED ALWAYS AS (to_tsvector('english', description || ' ' || context_signature)) STORED;

CREATE INDEX IF NOT EXISTS idx_datasources_search_vector ON datasources USING GIN (search_vector);

-- Table Nodes
ALTER TABLE table_nodes 
ADD COLUMN IF NOT EXISTS search_vector tsvector 
GENERATED ALWAYS AS (to_tsvector('english', semantic_name || ' ' || description)) STORED;

CREATE INDEX IF NOT EXISTS idx_table_nodes_search_vector ON table_nodes USING GIN (search_vector);

-- Column Nodes
ALTER TABLE column_nodes 
ADD COLUMN IF NOT EXISTS search_vector tsvector 
GENERATED ALWAYS AS (to_tsvector('english', semantic_name || ' ' || description || ' ' || COALESCE(context_note, ''))) STORED;

CREATE INDEX IF NOT EXISTS idx_column_nodes_search_vector ON column_nodes USING GIN (search_vector);

-- Semantic Metrics
ALTER TABLE semantic_metrics 
ADD COLUMN IF NOT EXISTS search_vector tsvector 
GENERATED ALWAYS AS (to_tsvector('english', name || ' ' || description)) STORED;

CREATE INDEX IF NOT EXISTS idx_semantic_metrics_search_vector ON semantic_metrics USING GIN (search_vector);

-- Semantic Synonyms
ALTER TABLE semantic_synonyms 
ADD COLUMN IF NOT EXISTS search_vector tsvector 
GENERATED ALWAYS AS (to_tsvector('english', term)) STORED;

CREATE INDEX IF NOT EXISTS idx_semantic_synonyms_search_vector ON semantic_synonyms USING GIN (search_vector);

-- Column Context Rules
ALTER TABLE column_context_rules 
ADD COLUMN IF NOT EXISTS search_vector tsvector 
GENERATED ALWAYS AS (to_tsvector('english', rule_text)) STORED;

CREATE INDEX IF NOT EXISTS idx_column_context_rules_search_vector ON column_context_rules USING GIN (search_vector);

-- Low Cardinality Values
ALTER TABLE low_cardinality_values 
ADD COLUMN IF NOT EXISTS search_vector tsvector 
GENERATED ALWAYS AS (to_tsvector('english', value_label)) STORED;

CREATE INDEX IF NOT EXISTS idx_low_cardinality_values_search_vector ON low_cardinality_values USING GIN (search_vector);

-- Golden SQL
ALTER TABLE golden_sql 
ADD COLUMN IF NOT EXISTS search_vector tsvector 
GENERATED ALWAYS AS (to_tsvector('english', prompt_text)) STORED;

CREATE INDEX IF NOT EXISTS idx_golden_sql_search_vector ON golden_sql USING GIN (search_vector);
