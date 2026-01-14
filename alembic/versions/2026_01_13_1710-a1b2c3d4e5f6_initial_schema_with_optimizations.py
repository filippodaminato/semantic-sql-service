"""initial_schema_with_optimizations

Initial schema creation with all database performance optimizations for MCP Agent Retrieval API.
Includes indexes, constraints, materialized views, and vector search optimizations.

This migration consolidates all database optimizations into a single, professional Alembic migration.

Revision ID: a1b2c3d4e5f6
Revises: 
Create Date: 2026-01-13 17:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Apply all database performance optimizations.
    
    This migration includes:
    1. PostgreSQL extensions (pgvector)
    2. Foreign key indexes for efficient JOINs
    3. Composite indexes for frequent query patterns
    4. HNSW vector indexes for semantic search
    5. Partial indexes for filtered queries
    6. Unique constraints to prevent duplicates
    7. Materialized view for complex edge queries
    8. Temporal indexes for log tables
    9. NOT NULL constraints
    10. Query planner statistics update
    """
    
    # ========================================================================
    # 1. EXTENSIONS
    # ========================================================================
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    
    # ========================================================================
    # 2. FOREIGN KEY INDEXES
    # ========================================================================
    # PostgreSQL doesn't automatically index foreign keys, but they're
    # essential for JOIN performance
    
    op.create_index(
        'idx_table_nodes_datasource_id',
        'table_nodes',
        ['datasource_id'],
        unique=False
    )
    
    op.create_index(
        'idx_column_nodes_table_id',
        'column_nodes',
        ['table_id'],
        unique=False
    )
    
    op.create_index(
        'idx_schema_edges_source_column',
        'schema_edges',
        ['source_column_id'],
        unique=False
    )
    
    op.create_index(
        'idx_schema_edges_target_column',
        'schema_edges',
        ['target_column_id'],
        unique=False
    )
    
    op.create_index(
        'idx_schema_edges_columns',
        'schema_edges',
        ['source_column_id', 'target_column_id'],
        unique=False
    )
    
    op.create_index(
        'idx_semantic_metrics_datasource_id',
        'semantic_metrics',
        ['datasource_id'],
        unique=False
    )
    
    op.create_index(
        'idx_golden_sql_datasource_id',
        'golden_sql',
        ['datasource_id'],
        unique=False
    )
    
    op.create_index(
        'idx_column_context_rules_column_id',
        'column_context_rules',
        ['column_id'],
        unique=False
    )
    
    op.create_index(
        'idx_low_cardinality_values_column_id',
        'low_cardinality_values',
        ['column_id'],
        unique=False
    )
    
    # ========================================================================
    # 3. COMPOSITE INDEXES FOR FREQUENT QUERIES
    # ========================================================================
    
    op.create_index(
        'idx_table_nodes_datasource_slug',
        'table_nodes',
        ['datasource_id', 'slug'],
        unique=False
    )
    
    op.create_index(
        'idx_column_nodes_table_slug',
        'column_nodes',
        ['table_id', 'slug'],
        unique=False
    )
    
    op.create_index(
        'idx_golden_sql_datasource_created',
        'golden_sql',
        ['datasource_id', sa.text('created_at DESC')],
        unique=False
    )
    
    op.create_index(
        'idx_semantic_metrics_datasource_name',
        'semantic_metrics',
        ['datasource_id', 'name'],
        unique=False
    )
    
    # ========================================================================
    # 4. HNSW VECTOR INDEXES
    # ========================================================================
    # HNSW indexes for fast vector similarity search
    # Note: Requires pgvector extension (already created above)
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_datasources_embedding_hnsw 
        ON datasources USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_table_nodes_embedding_hnsw 
        ON table_nodes USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_column_nodes_embedding_hnsw 
        ON column_nodes USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_semantic_metrics_embedding_hnsw 
        ON semantic_metrics USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_semantic_synonyms_embedding_hnsw 
        ON semantic_synonyms USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_column_context_rules_embedding_hnsw 
        ON column_context_rules USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_golden_sql_embedding_hnsw 
        ON golden_sql USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)
    
    # ========================================================================
    # 5. PARTIAL INDEXES
    # ========================================================================
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_golden_sql_verified 
        ON golden_sql (datasource_id, complexity_score, created_at DESC) 
        WHERE verified = true
    """)
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_column_nodes_primary_keys 
        ON column_nodes (table_id, is_primary_key) 
        WHERE is_primary_key = true
    """)
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_schema_edges_inferred 
        ON schema_edges (source_column_id, target_column_id) 
        WHERE is_inferred = true
    """)
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_schema_edges_physical 
        ON schema_edges (source_column_id, target_column_id) 
        WHERE is_inferred = false
    """)

    # --- ADDED: SchemaEdge Vector Search Optimizations ---
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_schema_edges_embedding_hnsw 
        ON schema_edges USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_schema_edges_search_vector 
        ON schema_edges USING GIN (search_vector)
    """)
    
    # --- ADDED: LowCardinalityValue Search Optimization (updated for raw value search) ---
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_low_cardinality_values_search_vector 
        ON low_cardinality_values USING GIN (search_vector)
    """)
    
    # Convert required_tables from JSON to JSONB to support GIN index
    # This is safe for a fresh migration (no data to migrate)
    op.execute("""
        ALTER TABLE semantic_metrics 
        ALTER COLUMN required_tables TYPE jsonb USING required_tables::jsonb
    """)
    
    # Now create GIN index on JSONB column
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_semantic_metrics_with_tables 
        ON semantic_metrics USING GIN (required_tables jsonb_path_ops) 
        WHERE required_tables IS NOT NULL
    """)
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_golden_sql_complexity_2 
        ON golden_sql (datasource_id, created_at DESC) 
        WHERE complexity_score = 2 AND verified = true
    """)
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_golden_sql_complexity_3 
        ON golden_sql (datasource_id, created_at DESC) 
        WHERE complexity_score = 3 AND verified = true
    """)
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_golden_sql_complexity_4 
        ON golden_sql (datasource_id, created_at DESC) 
        WHERE complexity_score = 4 AND verified = true
    """)
    
    # ========================================================================
    # 6. UNIQUE CONSTRAINTS
    # ========================================================================
    # Note: These may fail if duplicates exist. Check first!
    
    op.create_index(
        'idx_table_nodes_datasource_physical_name_unique',
        'table_nodes',
        ['datasource_id', 'physical_name'],
        unique=True
    )
    
    op.create_index(
        'idx_column_nodes_table_name_unique',
        'column_nodes',
        ['table_id', 'name'],
        unique=True
    )
    
    op.create_index(
        'idx_semantic_synonyms_term_target_unique',
        'semantic_synonyms',
        ['term', 'target_type', 'target_id'],
        unique=True
    )
    
    op.create_index(
        'idx_low_cardinality_values_column_value_unique',
        'low_cardinality_values',
        ['column_id', 'value_raw'],
        unique=True
    )
    
    op.create_index(
        'idx_schema_edges_columns_unique',
        'schema_edges',
        ['source_column_id', 'target_column_id'],
        unique=True
    )
    
    # ========================================================================
    # 7. MATERIALIZED VIEW FOR SCHEMA EDGES
    # ========================================================================
    
    op.execute("""
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
            sc.id AS source_column_id_full,
            sc.name AS source_column_name,
            sc.slug AS source_column_slug,
            sc.semantic_name AS source_column_semantic_name,
            st.id AS source_table_id,
            st.physical_name AS source_table_physical_name,
            st.slug AS source_table_slug,
            st.semantic_name AS source_table_semantic_name,
            st.datasource_id AS source_datasource_id,
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
        JOIN table_nodes tt ON tc.table_id = tt.id
    """)
    
    # Indexes on materialized view
    op.create_index(
        'idx_mv_edges_edge_id',
        'mv_schema_edges_expanded',
        ['edge_id'],
        unique=True
    )
    
    op.create_index(
        'idx_mv_edges_source_datasource',
        'mv_schema_edges_expanded',
        ['source_datasource_id'],
        unique=False
    )
    
    op.create_index(
        'idx_mv_edges_target_datasource',
        'mv_schema_edges_expanded',
        ['target_datasource_id'],
        unique=False
    )
    
    op.create_index(
        'idx_mv_edges_source_table_slug',
        'mv_schema_edges_expanded',
        ['source_table_slug'],
        unique=False
    )
    
    op.create_index(
        'idx_mv_edges_target_table_slug',
        'mv_schema_edges_expanded',
        ['target_table_slug'],
        unique=False
    )
    
    op.create_index(
        'idx_mv_edges_table_slugs',
        'mv_schema_edges_expanded',
        ['source_table_slug', 'target_table_slug'],
        unique=False
    )
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_mv_edges_description_fts 
        ON mv_schema_edges_expanded USING GIN (to_tsvector('simple', edge_description))
        WHERE edge_description IS NOT NULL
    """)
    
    # Function for concurrent refresh
    op.execute("""
        CREATE OR REPLACE FUNCTION refresh_schema_edges_view()
        RETURNS void AS $$
        BEGIN
            REFRESH MATERIALIZED VIEW CONCURRENTLY mv_schema_edges_expanded;
        END;
        $$ LANGUAGE plpgsql
    """)
    
    # Initial refresh
    op.execute("REFRESH MATERIALIZED VIEW mv_schema_edges_expanded")
    
    # ========================================================================
    # 8. TEMPORAL INDEXES FOR LOG TABLES
    # ========================================================================
    
    op.create_index(
        'idx_generation_traces_created_at',
        'generation_traces',
        [sa.text('created_at DESC')],
        unique=False
    )
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_generation_traces_feedback_created 
        ON generation_traces (user_feedback, created_at DESC) 
        WHERE user_feedback IS NOT NULL
    """)
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_generation_traces_errors_created 
        ON generation_traces (created_at DESC) 
        WHERE error_message IS NOT NULL
    """)
    
    op.create_index(
        'idx_ambiguity_logs_created_at',
        'ambiguity_logs',
        [sa.text('created_at DESC')],
        unique=False
    )
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_ambiguity_logs_resolved_created 
        ON ambiguity_logs (created_at DESC) 
        WHERE user_resolution IS NOT NULL
    """)
    
    # ========================================================================
    # 9. NOT NULL CONSTRAINTS
    # ========================================================================
    # Ensure semantic_metrics.datasource_id is NOT NULL
    # This was in the deleted migration 355dafac593b
    
    # First, delete any metrics with NULL datasource_id (orphaned metrics)
    op.execute("""
        DELETE FROM semantic_metrics 
        WHERE datasource_id IS NULL
    """)
    
    # Then add NOT NULL constraint
    op.alter_column(
        'semantic_metrics',
        'datasource_id',
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
        existing_nullable=True
    )
    
    # ========================================================================
    # 10. UPDATE STATISTICS
    # ========================================================================
    # Update query planner statistics for optimal query plans
    
    op.execute("ANALYZE datasources")
    op.execute("ANALYZE table_nodes")
    op.execute("ANALYZE column_nodes")
    op.execute("ANALYZE schema_edges")
    op.execute("ANALYZE semantic_metrics")
    op.execute("ANALYZE semantic_synonyms")
    op.execute("ANALYZE column_context_rules")
    op.execute("ANALYZE low_cardinality_values")
    op.execute("ANALYZE golden_sql")


def downgrade() -> None:
    """
    Revert all performance optimizations.
    
    WARNING: This will remove all indexes, constraints, and materialized views.
    This may significantly impact query performance.
    """
    
    # Drop materialized view and function
    op.execute("DROP FUNCTION IF EXISTS refresh_schema_edges_view()")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_schema_edges_expanded")
    
    # Drop temporal indexes
    op.drop_index('idx_ambiguity_logs_created_at', table_name='ambiguity_logs')
    op.execute("DROP INDEX IF EXISTS idx_ambiguity_logs_resolved_created")
    op.execute("DROP INDEX IF EXISTS idx_generation_traces_errors_created")
    op.execute("DROP INDEX IF EXISTS idx_generation_traces_feedback_created")
    op.drop_index('idx_generation_traces_created_at', table_name='generation_traces')
    
    # Revert NOT NULL constraint
    op.alter_column(
        'semantic_metrics',
        'datasource_id',
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
        existing_nullable=False
    )
    
    # Drop unique constraints
    op.drop_index('idx_schema_edges_columns_unique', table_name='schema_edges')
    op.drop_index('idx_low_cardinality_values_column_value_unique', table_name='low_cardinality_values')
    op.drop_index('idx_semantic_synonyms_term_target_unique', table_name='semantic_synonyms')
    op.drop_index('idx_column_nodes_table_name_unique', table_name='column_nodes')
    op.drop_index('idx_table_nodes_datasource_physical_name_unique', table_name='table_nodes')
    
    # Drop partial indexes
    op.execute("DROP INDEX IF EXISTS idx_golden_sql_complexity_4")
    op.execute("DROP INDEX IF EXISTS idx_golden_sql_complexity_3")
    op.execute("DROP INDEX IF EXISTS idx_golden_sql_complexity_2")
    op.execute("DROP INDEX IF EXISTS idx_semantic_metrics_with_tables")
    op.execute("DROP INDEX IF EXISTS idx_schema_edges_physical")
    
    # Revert JSONB back to JSON (if needed)
    op.execute("""
        ALTER TABLE semantic_metrics 
        ALTER COLUMN required_tables TYPE json USING required_tables::json
    """)
    op.execute("DROP INDEX IF EXISTS idx_schema_edges_inferred")
    op.execute("DROP INDEX IF EXISTS idx_column_nodes_primary_keys")
    op.execute("DROP INDEX IF EXISTS idx_golden_sql_verified")
    
    # Drop HNSW vector indexes
    op.execute("DROP INDEX IF EXISTS idx_golden_sql_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS idx_column_context_rules_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS idx_semantic_synonyms_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS idx_semantic_metrics_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS idx_column_nodes_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS idx_table_nodes_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS idx_datasources_embedding_hnsw")
    
    # Drop composite indexes
    op.drop_index('idx_semantic_metrics_datasource_name', table_name='semantic_metrics')
    op.drop_index('idx_golden_sql_datasource_created', table_name='golden_sql')
    op.drop_index('idx_column_nodes_table_slug', table_name='column_nodes')
    op.drop_index('idx_table_nodes_datasource_slug', table_name='table_nodes')
    
    # Drop SchemaEdge and LCV Search Optimizations
    op.execute("DROP INDEX IF EXISTS idx_schema_edges_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS ix_schema_edges_search_vector")
    op.execute("DROP INDEX IF EXISTS ix_low_cardinality_values_search_vector")

    # Drop foreign key indexes
    op.drop_index('idx_low_cardinality_values_column_id', table_name='low_cardinality_values')
    op.drop_index('idx_column_context_rules_column_id', table_name='column_context_rules')
    op.drop_index('idx_golden_sql_datasource_id', table_name='golden_sql')
    op.drop_index('idx_semantic_metrics_datasource_id', table_name='semantic_metrics')
    op.drop_index('idx_schema_edges_columns', table_name='schema_edges')
    op.drop_index('idx_schema_edges_target_column', table_name='schema_edges')
    op.drop_index('idx_schema_edges_source_column', table_name='schema_edges')
    op.drop_index('idx_column_nodes_table_id', table_name='column_nodes')
    op.drop_index('idx_table_nodes_datasource_id', table_name='table_nodes')
    
    # Drop extension (optional - may be used by other parts of the system)
    # op.execute("DROP EXTENSION IF EXISTS vector")
