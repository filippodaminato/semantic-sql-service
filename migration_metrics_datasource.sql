-- Add datasource_id to semantic_metrics
ALTER TABLE semantic_metrics ADD COLUMN IF NOT EXISTS datasource_id UUID;

-- Add foreign key constraint
ALTER TABLE semantic_metrics 
ADD CONSTRAINT fk_semantic_metrics_datasource 
FOREIGN KEY (datasource_id) REFERENCES datasources(id) ON DELETE CASCADE;

-- Create index for performance
CREATE INDEX IF NOT EXISTS idx_semantic_metrics_datasource_id ON semantic_metrics(datasource_id);
