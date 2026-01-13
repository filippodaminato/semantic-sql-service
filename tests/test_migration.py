"""Tests for database migration"""
import pytest
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def test_migration_applies_successfully(db_session):
    """Test that the migration can be applied without errors."""
    # This test verifies that all migration operations complete successfully
    # The migration is applied via Alembic, so we test the result
    
    inspector = inspect(db_session.bind)
    
    # Verify extension is created
    result = db_session.execute(text("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"))
    assert result.scalar() is True, "pgvector extension should be installed"
    
    # Verify key indexes exist
    indexes = inspector.get_indexes('table_nodes')
    index_names = [idx['name'] for idx in indexes]
    assert 'idx_table_nodes_datasource_id' in index_names, "Foreign key index should exist"
    assert 'idx_table_nodes_datasource_slug' in index_names, "Composite index should exist"
    
    indexes = inspector.get_indexes('column_nodes')
    index_names = [idx['name'] for idx in indexes]
    assert 'idx_column_nodes_table_id' in index_names, "Foreign key index should exist"
    assert 'idx_column_nodes_table_slug' in index_names, "Composite index should exist"
    
    # Verify unique constraints exist
    indexes = inspector.get_indexes('table_nodes')
    unique_indexes = [idx['name'] for idx in indexes if idx.get('unique', False)]
    assert 'idx_table_nodes_datasource_physical_name_unique' in unique_indexes, "Unique constraint should exist"
    
    indexes = inspector.get_indexes('column_nodes')
    unique_indexes = [idx['name'] for idx in indexes if idx.get('unique', False)]
    assert 'idx_column_nodes_table_name_unique' in unique_indexes, "Unique constraint should exist"
    
    # Verify materialized view exists
    result = db_session.execute(text("""
        SELECT EXISTS(
            SELECT 1 FROM pg_matviews 
            WHERE matviewname = 'mv_schema_edges_expanded'
        )
    """))
    assert result.scalar() is True, "Materialized view should exist"
    
    # Verify refresh function exists
    result = db_session.execute(text("""
        SELECT EXISTS(
            SELECT 1 FROM pg_proc 
            WHERE proname = 'refresh_schema_edges_view'
        )
    """))
    assert result.scalar() is True, "Refresh function should exist"


def test_vector_indexes_exist(db_session):
    """Test that HNSW vector indexes are created."""
    inspector = inspect(db_session.bind)
    
    # Check for vector indexes on tables with embeddings
    tables_with_embeddings = [
        'datasources',
        'table_nodes',
        'column_nodes',
        'semantic_metrics',
        'semantic_synonyms',
        'column_context_rules',
        'golden_sql'
    ]
    
    for table_name in tables_with_embeddings:
        indexes = inspector.get_indexes(table_name)
        index_names = [idx['name'] for idx in indexes]
        expected_index = f'idx_{table_name}_embedding_hnsw'
        assert expected_index in index_names, f"HNSW index should exist on {table_name}"


def test_partial_indexes_exist(db_session):
    """Test that partial indexes are created."""
    inspector = inspect(db_session.bind)
    
    # Check golden_sql verified index
    indexes = inspector.get_indexes('golden_sql')
    index_names = [idx['name'] for idx in indexes]
    assert 'idx_golden_sql_verified' in index_names, "Partial index for verified golden_sql should exist"
    
    # Check primary keys index
    indexes = inspector.get_indexes('column_nodes')
    index_names = [idx['name'] for idx in indexes]
    assert 'idx_column_nodes_primary_keys' in index_names, "Partial index for primary keys should exist"


def test_temporal_indexes_exist(db_session):
    """Test that temporal indexes for log tables are created."""
    inspector = inspect(db_session.bind)
    
    # Check generation_traces indexes
    indexes = inspector.get_indexes('generation_traces')
    index_names = [idx['name'] for idx in indexes]
    assert 'idx_generation_traces_created_at' in index_names, "Temporal index should exist"
    
    # Check ambiguity_logs indexes
    indexes = inspector.get_indexes('ambiguity_logs')
    index_names = [idx['name'] for idx in indexes]
    assert 'idx_ambiguity_logs_created_at' in index_names, "Temporal index should exist"


def test_materialized_view_functional(db_session):
    """Test that materialized view is functional."""
    # Verify view can be queried
    result = db_session.execute(text("SELECT COUNT(*) FROM mv_schema_edges_expanded"))
    count = result.scalar()
    assert count is not None, "Materialized view should be queryable"
    
    # Verify view has expected columns
    result = db_session.execute(text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'mv_schema_edges_expanded'
        ORDER BY column_name
    """))
    columns = [row[0] for row in result]
    assert 'edge_id' in columns, "View should have edge_id column"
    assert 'source_table_slug' in columns, "View should have source_table_slug column"
    assert 'target_table_slug' in columns, "View should have target_table_slug column"


def test_not_null_constraint_applied(db_session):
    """Test that NOT NULL constraint on semantic_metrics.datasource_id is applied."""
    from sqlalchemy import MetaData, Table
    from sqlalchemy.schema import CreateTable
    
    metadata = MetaData()
    table = Table('semantic_metrics', metadata, autoload_with=db_session.bind)
    
    datasource_id_col = table.c.datasource_id
    assert not datasource_id_col.nullable, "datasource_id should be NOT NULL"
