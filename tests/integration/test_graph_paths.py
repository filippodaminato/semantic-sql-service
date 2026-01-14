
import pytest
from fastapi import status
from uuid import uuid4
from src.db.models import (
    Datasource, TableNode, ColumnNode, SchemaEdge, RelationshipType
)

PREFIX = "/api/v1/discovery"

@pytest.fixture
def graph_seed(db_session, sample_datasource):
    """Seed data for graph path testing"""
    ds = sample_datasource
    
    # Create 4 tables: A -> B -> C, and D (isolated)
    t_a = TableNode(id=uuid4(), datasource_id=ds.id, physical_name="table_a", slug="table_a", semantic_name="Table A")
    t_b = TableNode(id=uuid4(), datasource_id=ds.id, physical_name="table_b", slug="table_b", semantic_name="Table B")
    t_c = TableNode(id=uuid4(), datasource_id=ds.id, physical_name="table_c", slug="table_c", semantic_name="Table C")
    t_d = TableNode(id=uuid4(), datasource_id=ds.id, physical_name="table_d", slug="table_d", semantic_name="Table D")
    
    db_session.add_all([t_a, t_b, t_c, t_d])
    db_session.flush()
    
    # Columns
    c_a_id = ColumnNode(id=uuid4(), table_id=t_a.id, name="id", slug="a_id", data_type="INT")
    c_b_id = ColumnNode(id=uuid4(), table_id=t_b.id, name="id", slug="b_id", data_type="INT")
    c_b_fk_a = ColumnNode(id=uuid4(), table_id=t_b.id, name="a_id", slug="b_fk_a", data_type="INT")
    c_c_id = ColumnNode(id=uuid4(), table_id=t_c.id, name="id", slug="c_id", data_type="INT")
    c_c_fk_b = ColumnNode(id=uuid4(), table_id=t_c.id, name="b_id", slug="c_fk_b", data_type="INT")
    
    db_session.add_all([c_a_id, c_b_id, c_b_fk_a, c_c_id, c_c_fk_b])
    db_session.flush()
    
    # Edges
    # A -> B (B.a_id references A.id)
    edge_ab = SchemaEdge(
        id=uuid4(),
        source_column_id=c_a_id.id,
        target_column_id=c_b_fk_a.id,
        relationship_type=RelationshipType.ONE_TO_MANY,
        description="B ref A"
    )
    
    # B -> C (C.b_id references B.id)
    edge_bc = SchemaEdge(
        id=uuid4(),
        source_column_id=c_b_id.id,
        target_column_id=c_c_fk_b.id,
        relationship_type=RelationshipType.ONE_TO_MANY,
        description="C ref B"
    )
    
    db_session.add_all([edge_ab, edge_bc])
    db_session.commit()
    
    return {"ds": ds, "tables": {"A": t_a, "B": t_b, "C": t_c, "D": t_d}}

def test_path_direct(client, graph_seed):
    """Test finding direct path"""
    # Path B -> A (using edge_ab reversed or forward depending on traversal logic)
    # Our impl adds edges bidirectionally.
    # Edge was B(fk)->A(pk).
    # Path B->A: should find 1 path of length 1.
    
    resp = client.post(f"{PREFIX}/paths", json={
        "source_table_slug": "table_b",
        "target_table_slug": "table_a",
        "max_depth": 3
    })
    
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["source_table"] == "table_b"
    assert data["target_table"] == "table_a"
    assert len(data["paths"]) >= 1
    
    # Verify path content
    path = data["paths"][0]
    assert len(path) == 1
    edge = path[0]
    assert edge["source"]["table_slug"] == "table_b"
    assert edge["target"]["table_slug"] == "table_a"

def test_path_multihop(client, graph_seed):
    """Test finding multi-hop path C -> B -> A"""
    resp = client.post(f"{PREFIX}/paths", json={
        "source_table_slug": "table_c",
        "target_table_slug": "table_a",
        "max_depth": 3
    })
    
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert len(data["paths"]) >= 1
    
    # Should be length 2
    path = data["paths"][0]
    assert len(path) == 2
    
    # First hop C->B
    assert path[0]["source"]["table_slug"] == "table_c"
    assert path[0]["target"]["table_slug"] == "table_b"
    
    # Second hop B->A
    assert path[1]["source"]["table_slug"] == "table_b"
    assert path[1]["target"]["table_slug"] == "table_a"

def test_no_path(client, graph_seed):
    """Test no path exists (A -> D)"""
    resp = client.post(f"{PREFIX}/paths", json={
        "source_table_slug": "table_a",
        "target_table_slug": "table_d",
        "max_depth": 3
    })
    
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert len(data["paths"]) == 0
    assert data["total_paths"] == 0

def test_invalid_slugs(client, graph_seed):
    """Test 404 on invalid table slugs"""
    resp = client.post(f"{PREFIX}/paths", json={
        "source_table_slug": "nonexistent",
        "target_table_slug": "table_a"
    })
    assert resp.status_code == status.HTTP_404_NOT_FOUND

def test_max_depth_exceeded(client, graph_seed):
    """Test max depth constraint"""
    # C -> A needs 2 hops. If max_depth=1, should find 0 paths.
    resp = client.post(f"{PREFIX}/paths", json={
        "source_table_slug": "table_c",
        "target_table_slug": "table_a",
        "max_depth": 1
    })
    
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert len(data["paths"]) == 0
