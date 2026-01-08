from fastapi import status
from sqlalchemy.orm import Session
from src.db.models import (
    Datasource, TableNode, ColumnNode, SemanticMetric,
    LowCardinalityValue, SemanticSynonym, GoldenSQL, SQLEngineType
)
import uuid
import unittest


def test_unified_search(client, db_session):
    # Setup data
    ds = Datasource(
        name="Sales DB", 
        slug="sales-db", 
        engine=SQLEngineType.POSTGRES, 
        embedding=[0.1]*1536
    )
    db_session.add(ds)
    db_session.flush()
    
    table = TableNode(
        datasource_id=ds.id,
        physical_name="t_orders",
        semantic_name="Orders",
        description="List of all customer orders",
        embedding=[0.1]*1536
    )
    db_session.add(table)
    
    metric = SemanticMetric(
        name="Total Revenue",
        calculation_sql="SUM(amount)",
        description="Total revenue from orders",
        embedding=[0.1]*1536
    )
    db_session.add(metric)
    db_session.commit()
    
    # Test
    response = client.post(
        "/api/v1/retrieval/search",
        json={"query": "revenue orders", "limit": 10}
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) >= 2
    types = {item["type"] for item in data}
    assert "TABLE" in types
    assert "METRIC" in types
    assert "DATASOURCE" in types

def test_validate_values(client, db_session):
    # Setup
    ds = Datasource(name="Geo DB", slug="geo-db", engine=SQLEngineType.POSTGRES)
    db_session.add(ds)
    db_session.flush()
    
    table = TableNode(datasource_id=ds.id, physical_name="locations", semantic_name="Locations")
    db_session.add(table)
    db_session.flush()
    
    col = ColumnNode(table_id=table.id, name="region", data_type="VARCHAR")
    db_session.add(col)
    db_session.flush()
    
    # Create vectors
    vec_lombardia = [1.0] + [0.0] * 1535
    vec_non_existing = [0.0, 1.0] + [0.0] * 1534
    
    val1 = LowCardinalityValue(column_id=col.id, value_raw="LOM", value_label="Lombardia", embedding=vec_lombardia)
    db_session.add(val1)
    db_session.commit()
    
    # Mock embedding with different values to avoid collision
    with unittest.mock.patch("src.services.embedding_service.embedding_service.generate_embedding") as mock_gen:
        def side_effect(text):
            if text == "NonExisting":
                return vec_non_existing
            return vec_lombardia
        mock_gen.side_effect = side_effect
        
        # Test valid
        response = client.post(
            "/api/v1/retrieval/values/validate",
            json={
                "table_name": "locations", 
                "column_name": "region",
                "values": ["Lombardia", "NonExisting"]
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_valid"] is False
        assert data["resolved_values"]["Lombardia"] == "LOM"
        assert data["resolved_values"]["NonExisting"] is None

def test_resolve_synonym(client, db_session):
    syn = SemanticSynonym(
        term="ACV", 
        target_type="METRIC", 
        target_id=uuid.uuid4()
    )
    db_session.add(syn)
    db_session.commit()
    
    response = client.post(
        "/api/v1/retrieval/synonyms/resolve",
        json={"term": "acv"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 1
    assert data[0]["term"] == "ACV"

def test_explain_metric(client, db_session):
    metric = SemanticMetric(
        name="Churn Rate",
        calculation_sql="churn / total",
        required_tables=[]
    )
    db_session.add(metric)
    db_session.commit()
    
    response = client.post(
        "/api/v1/retrieval/metrics/explain",
        json={"metric_name": "Churn Rate"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["sql_formula"] == "churn / total"

def test_admin_sync_embeddings(client, db_session):
    # Setup entity with missing hash
    ds = Datasource(
        name="Sync Test", 
        slug="sync-test",
        description="To be embedded",
        engine=SQLEngineType.POSTGRES
    )
    db_session.add(ds)
    db_session.commit()
    
    assert ds.embedding is None
    assert ds.embedding_hash is None
    
    response = client.post("/api/v1/retrieval/admin/sync-embeddings")
    assert response.status_code == status.HTTP_200_OK
    
    db_session.refresh(ds)
    assert ds.embedding is not None
    assert ds.embedding_hash is not None
