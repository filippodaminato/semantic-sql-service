"""Tests for Physical Ontology endpoints"""
import pytest
from uuid import uuid4
from fastapi import status


def test_create_datasource(client):
    """Test creating a datasource"""
    response = client.post(
        "/api/v1/ontology/datasources",
        json={
            "name": "Test Datasource",
            "engine": "postgres",
            "description": "A test datasource",
            "context_signature": "sales, orders"
        }
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == "Test Datasource"
    assert data["slug"] == "test-datasource"  # Auto-generated
    assert data["engine"] == "postgres"
    assert data["description"] == "A test datasource"
    assert data["context_signature"] == "sales, orders"
    assert "id" in data


def test_create_datasource_duplicate(client, sample_datasource):
    """Test creating duplicate datasource fails"""
    response = client.post(
        "/api/v1/ontology/datasources",
        json={
            "name": "test_datasource",  # Same name
            "engine": "postgres"
        }
    )
    assert response.status_code == status.HTTP_409_CONFLICT
    
    # Test duplicate slug
    response = client.post(
        "/api/v1/ontology/datasources",
        json={
            "name": "Test Datasource New",
            "slug": "test_datasource_slug",  # Same slug (from conftest)
            "engine": "postgres"
        }
    )
    assert response.status_code == status.HTTP_409_CONFLICT


def test_create_table_deep(client, sample_datasource_id):
    """Test deep create table with columns"""
    response = client.post(
        "/api/v1/ontology/tables",
        json={
            "datasource_id": str(sample_datasource_id),
            "physical_name": "t_sales_2024",
            "semantic_name": "Sales Transactions",
            "description": "Tabella principale contenente tutte le transazioni e-commerce confermate.",
            "ddl_context": "CREATE TABLE t_sales_2024 (id INT, amount DECIMAL(10,2))",
            "columns": [
                {
                    "name": "amount_total",
                    "data_type": "DECIMAL(10,2)",
                    "is_primary_key": False,
                    "context_note": "Include IVA. Se null, transazione fallita."
                },
                {
                    "name": "cust_id",
                    "data_type": "INT",
                    "is_primary_key": False,
                    "description": "Foreign key verso tabella Clienti"
                }
            ]
        }
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["physical_name"] == "t_sales_2024"
    assert data["semantic_name"] == "Sales Transactions"
    assert len(data["columns"]) == 2
    assert data["columns"][0]["name"] == "amount_total"


def test_create_table_duplicate_physical_name(client, sample_datasource_id):
    """Test creating table with duplicate physical_name fails"""
    # Create first table
    client.post(
        "/api/v1/ontology/tables",
        json={
            "datasource_id": str(sample_datasource_id),
            "physical_name": "t_sales_2024",
            "semantic_name": "Sales Transactions",
            "columns": []
        }
    )
    
    # Try to create duplicate
    response = client.post(
        "/api/v1/ontology/tables",
        json={
            "datasource_id": str(sample_datasource_id),
            "physical_name": "t_sales_2024",
            "semantic_name": "Different Name",
            "columns": []
        }
    )
    assert response.status_code == status.HTTP_409_CONFLICT


def test_create_table_invalid_datasource(client):
    """Test creating table with invalid datasource_id fails"""
    response = client.post(
        "/api/v1/ontology/tables",
        json={
            "datasource_id": str(uuid4()),
            "physical_name": "t_sales_2024",
            "semantic_name": "Sales Transactions",
            "columns": []
        }
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_create_table_with_spaces_in_physical_name(client, sample_datasource_id):
    """Test creating table with spaces in physical_name fails validation"""
    response = client.post(
        "/api/v1/ontology/tables",
        json={
            "datasource_id": str(sample_datasource_id),
            "physical_name": "t sales 2024",  # Contains spaces
            "semantic_name": "Sales Transactions",
            "columns": []
        }
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_update_column(client, sample_datasource_id):
    """Test updating a column"""
    # Create table with column
    table_response = client.post(
        "/api/v1/ontology/tables",
        json={
            "datasource_id": str(sample_datasource_id),
            "physical_name": "t_test",
            "semantic_name": "Test Table",
            "columns": [
                {
                    "name": "test_col",
                    "data_type": "VARCHAR(100)",
                    "is_primary_key": False
                }
            ]
        }
    )
    column_id = table_response.json()["columns"][0]["id"]
    
    # Update column
    response = client.patch(
        f"/api/v1/ontology/columns/{column_id}",
        json={
            "semantic_name": "Test Column Updated",
            "context_note": "Updated context note",
            "is_primary_key": True
        }
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["semantic_name"] == "Test Column Updated"
    assert data["context_note"] == "Updated context note"
    assert data["is_primary_key"] is True


def test_update_column_not_found(client):
    """Test updating non-existent column fails"""
    response = client.patch(
        f"/api/v1/ontology/columns/{uuid4()}",
        json={"semantic_name": "New Name"}
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_create_relationship(client, sample_datasource_id):
    """Test creating a relationship"""
    # Create table with columns
    table_response = client.post(
        "/api/v1/ontology/tables",
        json={
            "datasource_id": str(sample_datasource_id),
            "physical_name": "t_orders",
            "semantic_name": "Orders",
            "columns": [
                {"name": "id", "data_type": "INT", "is_primary_key": True},
                {"name": "customer_id", "data_type": "INT", "is_primary_key": False}
            ]
        }
    )
    
    # Create second table
    table2_response = client.post(
        "/api/v1/ontology/tables",
        json={
            "datasource_id": str(sample_datasource_id),
            "physical_name": "t_customers",
            "semantic_name": "Customers",
            "columns": [
                {"name": "id", "data_type": "INT", "is_primary_key": True}
            ]
        }
    )
    
    source_col_id = table_response.json()["columns"][1]["id"]  # customer_id
    target_col_id = table2_response.json()["columns"][0]["id"]  # id
    
    # Create relationship
    response = client.post(
        "/api/v1/ontology/relationships",
        json={
            "source_column_id": str(source_col_id),
            "target_column_id": str(target_col_id),
            "relationship_type": "ONE_TO_MANY",
            "is_inferred": False
        }
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["relationship_type"] == "ONE_TO_MANY"


def test_create_relationship_same_column(client, sample_datasource_id):
    """Test creating relationship with same source and target fails"""
    # Create table with column
    table_response = client.post(
        "/api/v1/ontology/tables",
        json={
            "datasource_id": str(sample_datasource_id),
            "physical_name": "t_test",
            "semantic_name": "Test",
            "columns": [
                {"name": "id", "data_type": "INT", "is_primary_key": True}
            ]
        }
    )
    col_id = table_response.json()["columns"][0]["id"]
    
    # Try to create relationship with same column
    response = client.post(
        "/api/v1/ontology/relationships",
        json={
            "source_column_id": str(col_id),
            "target_column_id": str(col_id),
            "relationship_type": "ONE_TO_ONE",
            "is_inferred": False
        }
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_create_relationship_idempotent(client, sample_datasource_id):
    """Test creating duplicate relationship is idempotent"""
    # Create table with columns
    table_response = client.post(
        "/api/v1/ontology/tables",
        json={
            "datasource_id": str(sample_datasource_id),
            "physical_name": "t_orders",
            "semantic_name": "Orders",
            "columns": [
                {"name": "id", "data_type": "INT", "is_primary_key": True},
                {"name": "customer_id", "data_type": "INT", "is_primary_key": False}
            ]
        }
    )
    
    table2_response = client.post(
        "/api/v1/ontology/tables",
        json={
            "datasource_id": str(sample_datasource_id),
            "physical_name": "t_customers",
            "semantic_name": "Customers",
            "columns": [
                {"name": "id", "data_type": "INT", "is_primary_key": True}
            ]
        }
    )
    
    source_col_id = table_response.json()["columns"][1]["id"]
    target_col_id = table2_response.json()["columns"][0]["id"]
    
    # Create relationship first time
    response1 = client.post(
        "/api/v1/ontology/relationships",
        json={
            "source_column_id": str(source_col_id),
            "target_column_id": str(target_col_id),
            "relationship_type": "ONE_TO_MANY",
            "is_inferred": False
        }
    )
    assert response1.status_code == status.HTTP_201_CREATED
    first_id = response1.json()["id"]
    
    # Create same relationship again (should return existing)
    response2 = client.post(
        "/api/v1/ontology/relationships",
        json={
            "source_column_id": str(source_col_id),
            "target_column_id": str(target_col_id),
            "relationship_type": "ONE_TO_MANY",
            "is_inferred": False
        }
    )
    assert response2.status_code == status.HTTP_201_CREATED
    assert response2.json()["id"] == first_id  # Same ID (idempotent)

def test_update_datasource(client, sample_datasource_id):
    """Test updating a datasource"""
    response = client.put(
        f"/api/v1/ontology/datasources/{sample_datasource_id}",
        json={
            "name": "test_datasource_updated",
            "engine": "bigquery"
        }
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == "test_datasource_updated"
    assert data["engine"] == "bigquery"


def test_delete_datasource(client, sample_datasource_id):
    """Test deleting a datasource"""
    response = client.delete(f"/api/v1/ontology/datasources/{sample_datasource_id}")
    assert response.status_code == status.HTTP_204_NO_CONTENT
    
    # Verify deletion
    response = client.get(f"/api/v1/ontology/datasources/{sample_datasource_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_table(client, sample_datasource_id):
    """Test updating a table"""
    # Create table
    create_response = client.post(
        "/api/v1/ontology/tables",
        json={
            "datasource_id": str(sample_datasource_id),
            "physical_name": "t_update_test",
            "semantic_name": "Before Update",
            "columns": []
        }
    )
    table_id = create_response.json()["id"]
    
    # Update table
    response = client.put(
        f"/api/v1/ontology/tables/{table_id}",
        json={
            "semantic_name": "After Update",
            "description": "Updated description"
        }
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["semantic_name"] == "After Update"
    assert data["description"] == "Updated description"


def test_delete_table(client, sample_datasource_id):
    """Test deleting a table"""
    # Create table
    create_response = client.post(
        "/api/v1/ontology/tables",
        json={
            "datasource_id": str(sample_datasource_id),
            "physical_name": "t_delete_test",
            "semantic_name": "To Delete",
            "columns": []
        }
    )
    table_id = create_response.json()["id"]
    
    # Delete table
    response = client.delete(f"/api/v1/ontology/tables/{table_id}")
    assert response.status_code == status.HTTP_204_NO_CONTENT
    
    # Verify deletion
    response = client.get(f"/api/v1/ontology/tables/{table_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_column(client, sample_datasource_id):
    """Test deleting a column"""
    # Create table with column
    table_response = client.post(
        "/api/v1/ontology/tables",
        json={
            "datasource_id": str(sample_datasource_id),
            "physical_name": "t_col_delete",
            "semantic_name": "Col Delete Test",
            "columns": [
                {"name": "col_to_delete", "data_type": "INT", "is_primary_key": False}
            ]
        }
    )
    column_id = table_response.json()["columns"][0]["id"]
    
    # Delete column
    response = client.delete(f"/api/v1/ontology/columns/{column_id}")
    assert response.status_code == status.HTTP_204_NO_CONTENT
    
    # Verify deletion
    response = client.get(f"/api/v1/ontology/columns/{column_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_relationship(client, sample_datasource_id):
    """Test updating a relationship"""
    # Setup tables and cols
    table1 = client.post("/api/v1/ontology/tables", json={
        "datasource_id": str(sample_datasource_id),
        "physical_name": "t1", "semantic_name": "T1", "columns": [{"name": "id", "data_type": "INT"}]
    }).json()
    table2 = client.post("/api/v1/ontology/tables", json={
        "datasource_id": str(sample_datasource_id),
        "physical_name": "t2", "semantic_name": "T2", "columns": [{"name": "t1_id", "data_type": "INT"}]
    }).json()
    
    c1 = table1["columns"][0]["id"]
    c2 = table2["columns"][0]["id"]
    
    # Create rel
    rel_response = client.post("/api/v1/ontology/relationships", json={
        "source_column_id": c1, "target_column_id": c2,
        "relationship_type": "ONE_TO_MANY", "is_inferred": False
    })
    rel_id = rel_response.json()["id"]
    
    # Update rel
    response = client.put(f"/api/v1/ontology/relationships/{rel_id}", json={
        "relationship_type": "ONE_TO_ONE",
        "is_inferred": True
    })
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["relationship_type"] == "ONE_TO_ONE"
    assert data["is_inferred"] is True


def test_delete_relationship(client, sample_datasource_id):
    """Test deleting a relationship"""
    # Setup tables and cols
    table1 = client.post("/api/v1/ontology/tables", json={
        "datasource_id": str(sample_datasource_id),
        "physical_name": "t3", "semantic_name": "T3", "columns": [{"name": "id", "data_type": "INT"}]
    }).json()
    table2 = client.post("/api/v1/ontology/tables", json={
        "datasource_id": str(sample_datasource_id),
        "physical_name": "t4", "semantic_name": "T4", "columns": [{"name": "t3_id", "data_type": "INT"}]
    }).json()
    
    c1 = table1["columns"][0]["id"]
    c2 = table2["columns"][0]["id"]
    
    # Create rel
    rel_response = client.post("/api/v1/ontology/relationships", json={
        "source_column_id": c1, "target_column_id": c2,
        "relationship_type": "ONE_TO_MANY"
    })
    rel_id = rel_response.json()["id"]
    
    # Delete rel
    response = client.delete(f"/api/v1/ontology/relationships/{rel_id}")
    assert response.status_code == status.HTTP_204_NO_CONTENT
    
    # Verify deletion
    response = client.get(f"/api/v1/ontology/relationships/{rel_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# EDGE CASE TESTS FOR 100% COVERAGE
# =============================================================================

def test_get_all_datasources(client, sample_datasource):
    """Test getting all datasources"""
    response = client.get("/api/v1/ontology/datasources")
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 1


def test_get_datasource_not_found(client):
    """Test getting a datasource that doesn't exist"""
    response = client.get(f"/api/v1/ontology/datasources/{uuid4()}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_datasource_not_found(client):
    """Test updating a datasource that doesn't exist"""
    response = client.put(f"/api/v1/ontology/datasources/{uuid4()}", json={
        "name": "New Name"
    })
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_datasource_description(client, sample_datasource_id):
    """Test updating datasource description and context_signature"""
    response = client.put(f"/api/v1/ontology/datasources/{sample_datasource_id}", json={
        "description": "New description",
        "context_signature": "new, context, signature"
    })
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["description"] == "New description"
    assert response.json()["context_signature"] == "new, context, signature"


def test_delete_datasource_not_found(client):
    """Test deleting a datasource that doesn't exist"""
    response = client.delete(f"/api/v1/ontology/datasources/{uuid4()}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_get_all_tables(client, sample_datasource_id):
    """Test getting all tables"""
    client.post("/api/v1/ontology/tables", json={
        "datasource_id": str(sample_datasource_id),
        "physical_name": "t_list_test",
        "semantic_name": "List Test",
        "columns": []
    })
    
    response = client.get("/api/v1/ontology/tables")
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list)


def test_get_table_not_found(client):
    """Test getting a table that doesn't exist"""
    response = client.get(f"/api/v1/ontology/tables/{uuid4()}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_table_not_found(client):
    """Test updating a table that doesn't exist"""
    response = client.put(f"/api/v1/ontology/tables/{uuid4()}", json={
        "semantic_name": "New Name"
    })
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_table_ddl_context(client, sample_datasource_id):
    """Test updating table ddl_context (physical_name is not updatable)"""
    table = client.post("/api/v1/ontology/tables", json={
        "datasource_id": str(sample_datasource_id),
        "physical_name": "t_upd_ddl",
        "semantic_name": "Update DDL",
        "columns": []
    }).json()
    
    response = client.put(f"/api/v1/ontology/tables/{table['id']}", json={
        "ddl_context": "CREATE TABLE t_upd_ddl (id INT PRIMARY KEY)"
    })
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["ddl_context"] == "CREATE TABLE t_upd_ddl (id INT PRIMARY KEY)"


def test_delete_table_not_found(client):
    """Test deleting a table that doesn't exist"""
    response = client.delete(f"/api/v1/ontology/tables/{uuid4()}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_get_column(client, sample_datasource_id):
    """Test getting a specific column"""
    table = client.post("/api/v1/ontology/tables", json={
        "datasource_id": str(sample_datasource_id),
        "physical_name": "t_col_get",
        "semantic_name": "Col Get",
        "columns": [{"name": "col_test", "data_type": "INT"}]
    }).json()
    col_id = table["columns"][0]["id"]
    
    response = client.get(f"/api/v1/ontology/columns/{col_id}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["name"] == "col_test"


def test_get_column_not_found(client):
    """Test getting a column that doesn't exist"""
    response = client.get(f"/api/v1/ontology/columns/{uuid4()}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_column_description_and_data_type(client, sample_datasource_id):
    """Test updating column description and data_type"""
    table = client.post("/api/v1/ontology/tables", json={
        "datasource_id": str(sample_datasource_id),
        "physical_name": "t_col_upd",
        "semantic_name": "Col Update",
        "columns": [{"name": "col_test", "data_type": "VARCHAR"}]
    }).json()
    col_id = table["columns"][0]["id"]
    
    response = client.patch(f"/api/v1/ontology/columns/{col_id}", json={
        "description": "New Description",
        "data_type": "VARCHAR(100)"
    })
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["description"] == "New Description"
    assert response.json()["data_type"] == "VARCHAR(100)"


def test_delete_column_not_found(client):
    """Test deleting a column that doesn't exist"""
    response = client.delete(f"/api/v1/ontology/columns/{uuid4()}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_get_all_relationships(client, sample_datasource_id):
    """Test getting all relationships"""
    response = client.get("/api/v1/ontology/relationships")
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list)


def test_get_relationship_not_found(client):
    """Test getting a relationship that doesn't exist"""
    response = client.get(f"/api/v1/ontology/relationships/{uuid4()}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_relationship_not_found(client):
    """Test updating a relationship that doesn't exist"""
    response = client.put(f"/api/v1/ontology/relationships/{uuid4()}", json={
        "relationship_type": "ONE_TO_ONE"
    })
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_relationship_not_found(client):
    """Test deleting a relationship that doesn't exist"""
    response = client.delete(f"/api/v1/ontology/relationships/{uuid4()}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_create_relationship_invalid_source_column(client, sample_datasource_id):
    """Test creating relationship with invalid source column"""
    table = client.post("/api/v1/ontology/tables", json={
        "datasource_id": str(sample_datasource_id),
        "physical_name": "t_rel_test",
        "semantic_name": "Rel Test",
        "columns": [{"name": "id", "data_type": "INT"}]
    }).json()
    col_id = table["columns"][0]["id"]
    
    response = client.post("/api/v1/ontology/relationships", json={
        "source_column_id": str(uuid4()),  # Invalid
        "target_column_id": col_id,
        "relationship_type": "ONE_TO_MANY"
    })
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_create_relationship_invalid_target_column(client, sample_datasource_id):
    """Test creating relationship with invalid target column"""
    table = client.post("/api/v1/ontology/tables", json={
        "datasource_id": str(sample_datasource_id),
        "physical_name": "t_rel_test2",
        "semantic_name": "Rel Test 2",
        "columns": [{"name": "id", "data_type": "INT"}]
    }).json()
    col_id = table["columns"][0]["id"]
    
    response = client.post("/api/v1/ontology/relationships", json={
        "source_column_id": col_id,
        "target_column_id": str(uuid4()),  # Invalid
        "relationship_type": "ONE_TO_MANY"
    })
    assert response.status_code == status.HTTP_404_NOT_FOUND

