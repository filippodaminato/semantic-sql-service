"""Tests for Learning endpoints"""
import pytest
from uuid import uuid4
from fastapi import status


def test_create_golden_sql(client, sample_datasource_id):
    """Test creating golden SQL example"""
    response = client.post(
        "/api/v1/learning/golden-sql",
        json={
            "datasource_id": str(sample_datasource_id),
            "prompt_text": "Quanti clienti abbiamo in Lombardia?",
            "sql_query": "SELECT count(*) FROM customers WHERE region = 'LOM'",
            "complexity": 1,
            "verified": True
        }
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["prompt_text"] == "Quanti clienti abbiamo in Lombardia?"
    assert "customers" in data["sql_query"]
    assert data["complexity_score"] == 1
    assert data["verified"] is True


def test_create_golden_sql_invalid_datasource(client):
    """Test creating golden SQL with invalid datasource fails"""
    response = client.post(
        "/api/v1/learning/golden-sql",
        json={
            "datasource_id": str(uuid4()),
            "prompt_text": "Test query",
            "sql_query": "SELECT * FROM test",
            "complexity": 1
        }
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_create_golden_sql_invalid_sql(client, sample_datasource_id):
    """Test creating golden SQL with invalid SQL syntax"""
    # Try with obviously invalid SQL
    response = client.post(
        "/api/v1/learning/golden-sql",
        json={
            "datasource_id": str(sample_datasource_id),
            "prompt_text": "Test query",
            "sql_query": "SELECT FROM WHERE",  # Invalid syntax
            "complexity": 1
        }
    )
    # Should fail validation
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_create_golden_sql_complexity_range(client, sample_datasource_id):
    """Test creating golden SQL with different complexity scores"""
    for complexity in [1, 3, 5]:
        response = client.post(
            "/api/v1/learning/golden-sql",
            json={
                "datasource_id": str(sample_datasource_id),
                "prompt_text": f"Test query complexity {complexity}",
                "sql_query": "SELECT count(*) FROM test",
                "complexity": complexity
            }
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["complexity_score"] == complexity


def test_create_golden_sql_complexity_out_of_range(client, sample_datasource_id):
    """Test creating golden SQL with complexity out of range fails validation"""
    # Test complexity < 1
    response = client.post(
        "/api/v1/learning/golden-sql",
        json={
            "datasource_id": str(sample_datasource_id),
            "prompt_text": "Test query",
            "sql_query": "SELECT count(*) FROM test",
            "complexity": 0
        }
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    # Test complexity > 5
    response = client.post(
        "/api/v1/learning/golden-sql",
        json={
            "datasource_id": str(sample_datasource_id),
            "prompt_text": "Test query",
            "sql_query": "SELECT count(*) FROM test",
            "complexity": 6
        }
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_create_golden_sql_empty_prompt(client, sample_datasource_id):
    """Test creating golden SQL with empty prompt fails validation"""
    response = client.post(
        "/api/v1/learning/golden-sql",
        json={
            "datasource_id": str(sample_datasource_id),
            "prompt_text": "   ",
            "sql_query": "SELECT count(*) FROM test",
            "complexity": 1
        }
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

def test_update_golden_sql(client, sample_datasource_id):
    """Test updating a golden SQL example"""
    golden = client.post("/api/v1/learning/golden-sql", json={
        "datasource_id": str(sample_datasource_id),
        "prompt_text": "Old Prompt",
        "sql_query": "SELECT 1",
        "complexity": 1
    }).json()
    
    response = client.put(f"/api/v1/learning/golden-sql/{golden['id']}", json={
        "prompt_text": "New Prompt",
        "complexity": 2
    })
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["prompt_text"] == "New Prompt"
    assert data["complexity_score"] == 2


def test_delete_golden_sql(client, sample_datasource_id):
    """Test deleting a golden SQL example"""
    golden = client.post("/api/v1/learning/golden-sql", json={
        "datasource_id": str(sample_datasource_id),
        "prompt_text": "Delete Me",
        "sql_query": "SELECT 1",
        "complexity": 1
    }).json()
    
    response = client.delete(f"/api/v1/learning/golden-sql/{golden['id']}")
    assert response.status_code == status.HTTP_204_NO_CONTENT
    
    response = client.get(f"/api/v1/learning/golden-sql/{golden['id']}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_ambiguity_log_crud(client):
    """Test CRUD operations for Ambiguity Log"""
    # Create
    response = client.post("/api/v1/learning/ambiguity-logs", json={
        "user_query": "Ambiguous query",
        "detected_ambiguity": {"options": ["A", "B"]},
        "user_resolution": "A"
    })
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    log_id = data["id"]
    assert data["user_query"] == "Ambiguous query"
    
    # Read
    response = client.get(f"/api/v1/learning/ambiguity-logs/{log_id}")
    assert response.status_code == status.HTTP_200_OK
    
    # Update
    response = client.put(f"/api/v1/learning/ambiguity-logs/{log_id}", json={
        "user_resolution": "B"
    })
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["user_resolution"] == "B"
    
    # Delete
    response = client.delete(f"/api/v1/learning/ambiguity-logs/{log_id}")
    assert response.status_code == status.HTTP_204_NO_CONTENT
    
    response = client.get(f"/api/v1/learning/ambiguity-logs/{log_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_generation_trace_crud(client):
    """Test CRUD operations for Generation Trace"""
    # Create
    response = client.post("/api/v1/learning/generation-traces", json={
        "user_prompt": "Generate SQL",
        "generated_sql": "SELECT *",
        "user_feedback": 1
    })
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    trace_id = data["id"]
    assert data["user_prompt"] == "Generate SQL"
    
    # Read
    response = client.get(f"/api/v1/learning/generation-traces/{trace_id}")
    assert response.status_code == status.HTTP_200_OK
    
    # Update
    response = client.put(f"/api/v1/learning/generation-traces/{trace_id}", json={
        "user_feedback": -1,
        "error_message": "Bad SQL"
    })
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["user_feedback"] == -1
    assert response.json()["error_message"] == "Bad SQL"
    
    # Delete
    response = client.delete(f"/api/v1/learning/generation-traces/{trace_id}")
    assert response.status_code == status.HTTP_204_NO_CONTENT
    
    response = client.get(f"/api/v1/learning/generation-traces/{trace_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
