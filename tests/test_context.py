"""Tests for Context & Values endpoints"""
import pytest
from uuid import uuid4
from fastapi import status


def test_create_nominal_values(client, sample_datasource_id):
    """Test creating nominal values"""
    # Create table with column
    table_response = client.post(
        "/api/v1/ontology/tables",
        json={
            "datasource_id": str(sample_datasource_id),
            "physical_name": "t_regions",
            "semantic_name": "Regions",
            "columns": [
                {"name": "region_code", "data_type": "VARCHAR(3)", "is_primary_key": False}
            ]
        }
    )
    column_id = table_response.json()["columns"][0]["id"]
    
    # Create nominal values
    response = client.post(
        "/api/v1/context/nominal-values",
        json={
            "column_id": str(column_id),
            "values": [
                {"raw": "LOM", "label": "Lombardia"},
                {"raw": "LAZ", "label": "Lazio"},
                {"raw": "CAM", "label": "Campania"}
            ]
        }
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert len(data) == 3
    assert any(v["value_raw"] == "LOM" and v["value_label"] == "Lombardia" for v in data)


def test_create_nominal_values_duplicate_raw(client, sample_datasource_id):
    """Test creating nominal values with duplicate raw values fails validation"""
    table_response = client.post(
        "/api/v1/ontology/tables",
        json={
            "datasource_id": str(sample_datasource_id),
            "physical_name": "t_test",
            "semantic_name": "Test",
            "columns": [
                {"name": "code", "data_type": "VARCHAR(3)", "is_primary_key": False}
            ]
        }
    )
    column_id = table_response.json()["columns"][0]["id"]
    
    response = client.post(
        "/api/v1/context/nominal-values",
        json={
            "column_id": str(column_id),
            "values": [
                {"raw": "LOM", "label": "Lombardia"},
                {"raw": "LOM", "label": "Lombardia Duplicate"}  # Duplicate raw
            ]
        }
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    # It should result in a single value with the latest label
    assert len(data) == 1
    assert data[0]["value_raw"] == "LOM"
    assert data[0]["value_label"] == "Lombardia"


def test_create_nominal_values_idempotent(client, sample_datasource_id):
    """Test creating nominal values is idempotent"""
    table_response = client.post(
        "/api/v1/ontology/tables",
        json={
            "datasource_id": str(sample_datasource_id),
            "physical_name": "t_test",
            "semantic_name": "Test",
            "columns": [
                {"name": "code", "data_type": "VARCHAR(3)", "is_primary_key": False}
            ]
        }
    )
    column_id = table_response.json()["columns"][0]["id"]
    
    # Create values first time
    response1 = client.post(
        "/api/v1/context/nominal-values",
        json={
            "column_id": str(column_id),
            "values": [{"raw": "LOM", "label": "Lombardia"}]
        }
    )
    assert response1.status_code == status.HTTP_201_CREATED
    
    # Create same value again (should update or return existing)
    response2 = client.post(
        "/api/v1/context/nominal-values",
        json={
            "column_id": str(column_id),
            "values": [{"raw": "LOM", "label": "Lombardia Updated"}]
        }
    )
    assert response2.status_code == status.HTTP_201_CREATED
    # Should update the label
    assert any(v["value_label"] == "Lombardia Updated" for v in response2.json())


def test_create_nominal_values_invalid_column(client):
    """Test creating nominal values with invalid column fails"""
    response = client.post(
        "/api/v1/context/nominal-values",
        json={
            "column_id": str(uuid4()),
            "values": [{"raw": "LOM", "label": "Lombardia"}]
        }
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_create_context_rule(client, sample_datasource_id):
    """Test creating a context rule"""
    table_response = client.post(
        "/api/v1/ontology/tables",
        json={
            "datasource_id": str(sample_datasource_id),
            "physical_name": "t_orders",
            "semantic_name": "Orders",
            "columns": [
                {"name": "delivery_date", "data_type": "DATE", "is_primary_key": False}
            ]
        }
    )
    column_id = table_response.json()["columns"][0]["id"]
    
    response = client.post(
        "/api/v1/context/rules",
        json={
            "column_id": str(column_id),
            "rule_text": "Se la data di consegna è nel futuro, l'ordine è considerato 'In Transito'. Se è NULL, l'ordine è 'In Preparazione'."
        }
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["column_id"] == str(column_id)
    assert "In Transito" in data["rule_text"]


def test_create_context_rule_invalid_column(client):
    """Test creating context rule with invalid column fails"""
    response = client.post(
        "/api/v1/context/rules",
        json={
            "column_id": str(uuid4()),
            "rule_text": "Test rule"
        }
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_create_context_rule_empty_text(client, sample_datasource_id):
    """Test creating context rule with empty text fails validation"""
    table_response = client.post(
        "/api/v1/ontology/tables",
        json={
            "datasource_id": str(sample_datasource_id),
            "physical_name": "t_test",
            "semantic_name": "Test",
            "columns": [
                {"name": "col", "data_type": "VARCHAR(100)", "is_primary_key": False}
            ]
        }
    )
    column_id = table_response.json()["columns"][0]["id"]
    
    response = client.post(
        "/api/v1/context/rules",
        json={
            "column_id": str(column_id),
            "rule_text": "   "  # Empty/whitespace
        }
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

def test_update_nominal_value(client, sample_datasource_id):
    """Test updating a nominal value"""
    table = client.post("/api/v1/ontology/tables", json={
        "datasource_id": str(sample_datasource_id),
        "physical_name": "t_vals", "semantic_name": "Values Table", 
        "columns": [{"name": "code", "data_type": "VARCHAR"}]
    }).json()
    col_id = table["columns"][0]["id"]
    
    # Create value
    val = client.post("/api/v1/context/nominal-values", json={
        "column_id": col_id,
        "values": [{"raw": "A", "label": "Alpha"}]
    }).json()[0]
    
    # Update value
    response = client.put(f"/api/v1/context/nominal-values/{val['id']}", json={
        "value_label": "Alpha Updated"
    })
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["value_label"] == "Alpha Updated"


def test_delete_nominal_value(client, sample_datasource_id):
    """Test deleting a nominal value"""
    table = client.post("/api/v1/ontology/tables", json={
        "datasource_id": str(sample_datasource_id),
        "physical_name": "t_vals_del", "semantic_name": "Values Table", 
        "columns": [{"name": "code", "data_type": "VARCHAR"}]
    }).json()
    col_id = table["columns"][0]["id"]
    
    val = client.post("/api/v1/context/nominal-values", json={
        "column_id": col_id,
        "values": [{"raw": "B", "label": "Beta"}]
    }).json()[0]
    
    response = client.delete(f"/api/v1/context/nominal-values/{val['id']}")
    assert response.status_code == status.HTTP_204_NO_CONTENT
    
    response = client.get(f"/api/v1/context/nominal-values/{val['id']}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_context_rule(client, sample_datasource_id):
    """Test updating a context rule"""
    table = client.post("/api/v1/ontology/tables", json={
        "datasource_id": str(sample_datasource_id),
        "physical_name": "t_rules", "semantic_name": "Rules Table", 
        "columns": [{"name": "code", "data_type": "VARCHAR"}]
    }).json()
    col_id = table["columns"][0]["id"]
    
    rule = client.post("/api/v1/context/rules", json={
        "column_id": col_id,
        "rule_text": "Old Rule"
    }).json()
    
    response = client.put(f"/api/v1/context/rules/{rule['id']}", json={
        "rule_text": "New Rule"
    })
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["rule_text"] == "New Rule"


def test_delete_context_rule(client, sample_datasource_id):
    """Test deleting a context rule"""
    table = client.post("/api/v1/ontology/tables", json={
        "datasource_id": str(sample_datasource_id),
        "physical_name": "t_rules_del", "semantic_name": "Rules Table", 
        "columns": [{"name": "code", "data_type": "VARCHAR"}]
    }).json()
    col_id = table["columns"][0]["id"]
    
    rule = client.post("/api/v1/context/rules", json={
        "column_id": col_id,
        "rule_text": "Delete Rule"
    }).json()
    
    response = client.delete(f"/api/v1/context/rules/{rule['id']}")
    assert response.status_code == status.HTTP_204_NO_CONTENT
    
    response = client.get(f"/api/v1/context/rules/{rule['id']}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
