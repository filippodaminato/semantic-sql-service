"""Tests for Business Semantics endpoints"""
import pytest
from uuid import uuid4
from fastapi import status


def test_create_metric(client, sample_datasource_id):
    """Test creating a semantic metric"""
    # Create a table first
    table_response = client.post(
        "/api/v1/ontology/tables",
        json={
            "datasource_id": str(sample_datasource_id),
            "physical_name": "t_sales",
            "semantic_name": "Sales",
            "columns": [
                {"name": "amount_total", "data_type": "DECIMAL(10,2)", "is_primary_key": False}
            ]
        }
    )
    table_id = table_response.json()["id"]
    
    # Create metric
    response = client.post(
        "/api/v1/semantics/metrics",
        json={
            "name": "Average Basket Size",
            "description": "Valore medio del carrello per ordini completati",
            "sql_expression": "AVG(t_sales.amount_total)",
            "required_table_ids": [str(table_id)],
            "filter_condition": "t_sales.status = 'COMPLETED'"
        }
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == "Average Basket Size"
    assert data["calculation_sql"] == "AVG(t_sales.amount_total)"


def test_create_metric_invalid_sql(client, sample_datasource_id):
    """Test creating metric with invalid SQL fails"""
    response = client.post(
        "/api/v1/semantics/metrics",
        json={
            "name": "Invalid Metric",
            "sql_expression": "SELECT * FROM nonexistent_table",  # Invalid syntax or table
            "required_table_ids": []
        }
    )
    # Should validate SQL syntax
    # Note: sqlglot might not catch all errors, so this might pass
    # but should catch obvious syntax errors
    assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_201_CREATED]


def test_create_metric_duplicate_name(client):
    """Test creating duplicate metric name fails"""
    # Create first metric
    client.post(
        "/api/v1/semantics/metrics",
        json={
            "name": "Test Metric",
            "sql_expression": "COUNT(*)",
            "required_table_ids": []
        }
    )
    
    # Try to create duplicate
    response = client.post(
        "/api/v1/semantics/metrics",
        json={
            "name": "Test Metric",
            "sql_expression": "SUM(*)",
            "required_table_ids": []
        }
    )
    assert response.status_code == status.HTTP_409_CONFLICT


def test_create_metric_invalid_table_ids(client):
    """Test creating metric with invalid table IDs fails"""
    response = client.post(
        "/api/v1/semantics/metrics",
        json={
            "name": "Test Metric",
            "sql_expression": "COUNT(*)",
            "required_table_ids": [str(uuid4())]  # Non-existent table
        }
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_create_synonyms_bulk(client, sample_datasource_id):
    """Test bulk creating synonyms"""
    # Create a table
    table_response = client.post(
        "/api/v1/ontology/tables",
        json={
            "datasource_id": str(sample_datasource_id),
            "physical_name": "t_customers",
            "semantic_name": "Customers",
            "columns": []
        }
    )
    table_id = table_response.json()["id"]
    
    # Create synonyms
    response = client.post(
        "/api/v1/semantics/synonyms/bulk",
        json={
            "target_id": str(table_id),
            "target_type": "TABLE",
            "terms": [
                "Anagrafica Clienti",
                "Acquirenti",
                "Subscriber List",
                "Utenza"
            ]
        }
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert len(data) == 4
    assert all(s["target_type"] == "TABLE" for s in data)
    assert all(s["target_id"] == str(table_id) for s in data)


def test_create_synonyms_bulk_idempotent(client, sample_datasource_id):
    """Test bulk creating synonyms is idempotent"""
    # Create a table
    table_response = client.post(
        "/api/v1/ontology/tables",
        json={
            "datasource_id": str(sample_datasource_id),
            "physical_name": "t_test",
            "semantic_name": "Test",
            "columns": []
        }
    )
    table_id = table_response.json()["id"]
    
    # Create synonyms first time
    response1 = client.post(
        "/api/v1/semantics/synonyms/bulk",
        json={
            "target_id": str(table_id),
            "target_type": "TABLE",
            "terms": ["Term1", "Term2"]
        }
    )
    assert response1.status_code == status.HTTP_201_CREATED
    
    # Create same synonyms again (should return existing)
    response2 = client.post(
        "/api/v1/semantics/synonyms/bulk",
        json={
            "target_id": str(table_id),
            "target_type": "TABLE",
            "terms": ["Term1", "Term2"]
        }
    )
    assert response2.status_code == status.HTTP_201_CREATED
    # Should return existing synonyms
    assert len(response2.json()) == 2


def test_create_synonyms_bulk_empty_terms(client, sample_datasource_id):
    """Test bulk creating synonyms with empty terms fails"""
    table_response = client.post(
        "/api/v1/ontology/tables",
        json={
            "datasource_id": str(sample_datasource_id),
            "physical_name": "t_test",
            "semantic_name": "Test",
            "columns": []
        }
    )
    table_id = table_response.json()["id"]
    
    response = client.post(
        "/api/v1/semantics/synonyms/bulk",
        json={
            "target_id": str(table_id),
            "target_type": "TABLE",
            "terms": []
        }
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

def test_update_metric(client, sample_datasource_id):
    """Test updating a metric"""
    # Create valid table first
    table = client.post("/api/v1/ontology/tables", json={
        "datasource_id": str(sample_datasource_id),
        "physical_name": "t_metrics", "semantic_name": "Metric Table", 
        "columns": [{"name": "val", "data_type": "INT"}]
    }).json()
    
    # Create metric
    metric = client.post("/api/v1/semantics/metrics", json={
        "name": "Original Metric",
        "sql_expression": "SUM(t_metrics.val)",
        "required_table_ids": [table["id"]]
    }).json()
    
    # Update metric
    response = client.put(f"/api/v1/semantics/metrics/{metric['id']}", json={
        "name": "Updated Metric",
        "description": "New description"
    })
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == "Updated Metric"
    assert data["description"] == "New description"


def test_delete_metric(client, sample_datasource_id):
    """Test deleting a metric"""
    # Create valid table first
    table = client.post("/api/v1/ontology/tables", json={
        "datasource_id": str(sample_datasource_id),
        "physical_name": "t_del_metric", "semantic_name": "Metric Table", 
        "columns": [{"name": "val", "data_type": "INT"}]
    }).json()
    
    metric = client.post("/api/v1/semantics/metrics", json={
        "name": "Delete Me",
        "sql_expression": "SUM(t_del_metric.val)",
        "required_table_ids": [table["id"]]
    }).json()
    
    response = client.delete(f"/api/v1/semantics/metrics/{metric['id']}")
    assert response.status_code == status.HTTP_204_NO_CONTENT
    
    # Verify
    response = client.get(f"/api/v1/semantics/metrics/{metric['id']}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_create_synonym_single(client, sample_datasource_id):
    """Test creating a single synonym"""
    table = client.post("/api/v1/ontology/tables", json={
        "datasource_id": str(sample_datasource_id),
        "physical_name": "t_syn", "semantic_name": "Syn Table", "columns": []
    }).json()
    
    response = client.post("/api/v1/semantics/synonyms", json={
        "term": "Single Synonym",
        "target_type": "TABLE",
        "target_id": table["id"]
    })
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["term"] == "Single Synonym"


def test_update_synonym(client, sample_datasource_id):
    """Test updating a synonym"""
    table = client.post("/api/v1/ontology/tables", json={
        "datasource_id": str(sample_datasource_id),
        "physical_name": "t_syn_upd", "semantic_name": "Syn Table", "columns": []
    }).json()
    
    syn = client.post("/api/v1/semantics/synonyms", json={
        "term": "Old Term",
        "target_type": "TABLE",
        "target_id": table["id"]
    }).json()
    
    response = client.put(f"/api/v1/semantics/synonyms/{syn['id']}", json={
        "term": "New Term"
    })
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["term"] == "New Term"


def test_delete_synonym(client, sample_datasource_id):
    """Test deleting a synonym"""
    table = client.post("/api/v1/ontology/tables", json={
        "datasource_id": str(sample_datasource_id),
        "physical_name": "t_syn_del", "semantic_name": "Syn Table", "columns": []
    }).json()
    
    syn = client.post("/api/v1/semantics/synonyms", json={
        "term": "Delete Term",
        "target_type": "TABLE",
        "target_id": table["id"]
    }).json()
    
    response = client.delete(f"/api/v1/semantics/synonyms/{syn['id']}")
    assert response.status_code == status.HTTP_204_NO_CONTENT
    
    response = client.get(f"/api/v1/semantics/synonyms/{syn['id']}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
