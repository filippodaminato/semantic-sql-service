"""
Comprehensive tests for Admin Control Plane endpoints.
Tests individual endpoints and complete workflows.
"""
import pytest
from uuid import uuid4
from fastapi import status


# =============================================================================
# DATASOURCES TESTS
# =============================================================================

class TestDatasourcesCRUD:
    """Tests for /admin/datasources endpoints"""
    
    def test_list_datasources(self, client):
        """Test listing all datasources"""
        response = client.get("/api/v1/admin/datasources")
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), list)
    
    def test_create_datasource(self, client):
        """Test creating a datasource"""
        response = client.post("/api/v1/admin/datasources", json={
            "name": "Test DB",
            "engine": "postgres",
            "description": "Test database for unit tests"
        })
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Test DB"
        assert "id" in data
    
    def test_create_datasource_duplicate_name(self, client):
        """Test creating a datasource with duplicate name fails"""
        client.post("/api/v1/admin/datasources", json={
            "name": "Unique DB",
            "engine": "postgres"
        })
        response = client.post("/api/v1/admin/datasources", json={
            "name": "Unique DB",
            "engine": "postgres"
        })
        assert response.status_code == status.HTTP_409_CONFLICT
    
    def test_get_datasource(self, client, sample_datasource_id):
        """Test getting a single datasource"""
        response = client.get(f"/api/v1/admin/datasources/{sample_datasource_id}")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"] == str(sample_datasource_id)
    
    def test_get_datasource_not_found(self, client):
        """Test getting non-existent datasource"""
        response = client.get(f"/api/v1/admin/datasources/{uuid4()}")
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_update_datasource(self, client, sample_datasource_id):
        """Test updating a datasource"""
        response = client.put(f"/api/v1/admin/datasources/{sample_datasource_id}", json={
            "description": "Updated description"
        })
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["description"] == "Updated description"
    
    def test_delete_datasource(self, client):
        """Test deleting a datasource"""
        # Create one to delete
        create_resp = client.post("/api/v1/admin/datasources", json={
            "name": "To Delete",
            "engine": "postgres"
        })
        ds_id = create_resp.json()["id"]
        
        response = client.delete(f"/api/v1/admin/datasources/{ds_id}")
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify deleted
        get_resp = client.get(f"/api/v1/admin/datasources/{ds_id}")
        assert get_resp.status_code == status.HTTP_404_NOT_FOUND
    
    def test_refresh_index(self, client, sample_datasource_id):
        """Test refreshing datasource embeddings"""
        response = client.post(f"/api/v1/admin/datasources/{sample_datasource_id}/refresh-index")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "updated_count" in data
        assert "entities" in data


# =============================================================================
# TABLES & COLUMNS TESTS
# =============================================================================

class TestTablesCRUD:
    """Tests for /admin/tables endpoints"""
    
    def test_list_tables_by_datasource(self, client, sample_datasource_id):
        """Test listing tables for a datasource"""
        response = client.get(f"/api/v1/admin/datasources/{sample_datasource_id}/tables")
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), list)
    
    def test_create_table(self, client, sample_datasource_id):
        """Test creating a table with columns"""
        response = client.post("/api/v1/admin/tables", json={
            "datasource_id": str(sample_datasource_id),
            "physical_name": "t_users",
            "semantic_name": "Users",
            "description": "User accounts table",
            "columns": [
                {"name": "id", "data_type": "INT", "is_primary_key": True},
                {"name": "email", "data_type": "VARCHAR(255)"}
            ]
        })
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["physical_name"] == "t_users"
        assert len(data["columns"]) == 2
    
    def test_create_table_duplicate(self, client, sample_datasource_id):
        """Test creating duplicate table fails"""
        client.post("/api/v1/admin/tables", json={
            "datasource_id": str(sample_datasource_id),
            "physical_name": "t_dup",
            "semantic_name": "Duplicate"
        })
        response = client.post("/api/v1/admin/tables", json={
            "datasource_id": str(sample_datasource_id),
            "physical_name": "t_dup",
            "semantic_name": "Duplicate 2"
        })
        assert response.status_code == status.HTTP_409_CONFLICT
    
    def test_get_table(self, client, sample_datasource_id):
        """Test getting table details"""
        create_resp = client.post("/api/v1/admin/tables", json={
            "datasource_id": str(sample_datasource_id),
            "physical_name": "t_get_test",
            "semantic_name": "Get Test",
            "columns": [{"name": "col1", "data_type": "INT"}]
        })
        table_id = create_resp.json()["id"]
        
        response = client.get(f"/api/v1/admin/tables/{table_id}/full")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["physical_name"] == "t_get_test"
        assert len(data["columns"]) == 1
    
    def test_update_table(self, client, sample_datasource_id):
        """Test updating table"""
        create_resp = client.post("/api/v1/admin/tables", json={
            "datasource_id": str(sample_datasource_id),
            "physical_name": "t_update",
            "semantic_name": "Original Name"
        })
        table_id = create_resp.json()["id"]
        
        response = client.put(f"/api/v1/admin/tables/{table_id}", json={
            "semantic_name": "Updated Name",
            "physical_name": "t_updated_phys", # Test physical name update
            "slug": "t-updated-plus-slug",     # Test slug update
            "description": "New description"
        })
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["updated"] is True
        assert data["physical_name"] == "t_updated_phys"
        assert data["slug"] == "t-updated-plus-slug"
    
    def test_delete_table(self, client, sample_datasource_id):
        """Test deleting table"""
        create_resp = client.post("/api/v1/admin/tables", json={
            "datasource_id": str(sample_datasource_id),
            "physical_name": "t_delete_me",
            "semantic_name": "Delete Me"
        })
        table_id = create_resp.json()["id"]
        
        response = client.delete(f"/api/v1/admin/tables/{table_id}")
        assert response.status_code == status.HTTP_204_NO_CONTENT


class TestColumnsCRUD:
    """Tests for /admin/columns endpoints"""
    
    def test_update_column(self, client, sample_datasource_id):
        """Test updating a column"""
        table_resp = client.post("/api/v1/admin/tables", json={
            "datasource_id": str(sample_datasource_id),
            "physical_name": "t_col_update",
            "semantic_name": "Column Update Test",
            "columns": [{"name": "status", "data_type": "VARCHAR"}]
        })
        col_id = table_resp.json()["columns"][0]["id"]
        
        response = client.put(f"/api/v1/admin/columns/{col_id}", json={
            "semantic_name": "Order Status",
            "context_note": "Use 'active' or 'inactive'"
        })
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["updated"] is True


# =============================================================================
# RELATIONSHIPS TESTS
# =============================================================================

class TestRelationshipsCRUD:
    """Tests for /admin/relationships endpoints"""
    
    def test_create_relationship(self, client, sample_datasource_id):
        """Test creating a relationship between tables"""
        # Create parent table
        parent = client.post("/api/v1/admin/tables", json={
            "datasource_id": str(sample_datasource_id),
            "physical_name": "t_parent_rel",
            "semantic_name": "Parent",
            "columns": [{"name": "id", "data_type": "INT", "is_primary_key": True}]
        }).json()
        
        # Create child table
        child = client.post("/api/v1/admin/tables", json={
            "datasource_id": str(sample_datasource_id),
            "physical_name": "t_child_rel",
            "semantic_name": "Child",
            "columns": [
                {"name": "id", "data_type": "INT", "is_primary_key": True},
                {"name": "parent_id", "data_type": "INT"}
            ]
        }).json()
        
        response = client.post("/api/v1/admin/relationships", json={
            "source_column_id": child["columns"][1]["id"],  # parent_id
            "target_column_id": parent["columns"][0]["id"],  # id
            "relationship_type": "ONE_TO_MANY",
            "description": "Child belongs to Parent"
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["created"] is True
    
    def test_get_table_relationships(self, client, sample_datasource_id):
        """Test getting relationships for a table"""
        # Create tables with relationship
        t1 = client.post("/api/v1/admin/tables", json={
            "datasource_id": str(sample_datasource_id),
            "physical_name": "t_rel_view_1",
            "semantic_name": "T1",
            "columns": [{"name": "id", "data_type": "INT"}]
        }).json()
        
        t2 = client.post("/api/v1/admin/tables", json={
            "datasource_id": str(sample_datasource_id),
            "physical_name": "t_rel_view_2",
            "semantic_name": "T2",
            "columns": [{"name": "t1_id", "data_type": "INT"}]
        }).json()
        
        client.post("/api/v1/admin/relationships", json={
            "source_column_id": t2["columns"][0]["id"],
            "target_column_id": t1["columns"][0]["id"],
            "relationship_type": "ONE_TO_MANY"
        })
        
        response = client.get(f"/api/v1/admin/tables/{t1['id']}/relationships")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "outgoing" in data
        assert "incoming" in data
        assert len(data["incoming"]) >= 1
    
    def test_delete_relationship(self, client, sample_datasource_id):
        """Test deleting a relationship"""
        t1 = client.post("/api/v1/admin/tables", json={
            "datasource_id": str(sample_datasource_id),
            "physical_name": "t_del_rel_1",
            "semantic_name": "Del1",
            "columns": [{"name": "id", "data_type": "INT"}]
        }).json()
        
        t2 = client.post("/api/v1/admin/tables", json={
            "datasource_id": str(sample_datasource_id),
            "physical_name": "t_del_rel_2",
            "semantic_name": "Del2",
            "columns": [{"name": "fk", "data_type": "INT"}]
        }).json()
        
        rel = client.post("/api/v1/admin/relationships", json={
            "source_column_id": t2["columns"][0]["id"],
            "target_column_id": t1["columns"][0]["id"],
            "relationship_type": "ONE_TO_ONE"
        }).json()
        
        response = client.delete(f"/api/v1/admin/relationships/{rel['id']}")
        assert response.status_code == status.HTTP_204_NO_CONTENT


# =============================================================================
# METRICS TESTS
# =============================================================================

class TestMetricsCRUD:
    """Tests for /admin/metrics endpoints"""
    
    def test_list_metrics(self, client):
        """Test listing metrics"""
        response = client.get("/api/v1/admin/metrics")
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), list)
    
    def test_create_metric(self, client, sample_datasource_id):
        """Test creating a metric"""
        # Create table first
        table = client.post("/api/v1/admin/tables", json={
            "datasource_id": str(sample_datasource_id),
            "physical_name": "t_metric_test",
            "semantic_name": "Metric Test",
            "columns": [{"name": "amount", "data_type": "DECIMAL"}]
        }).json()
        
        response = client.post("/api/v1/admin/metrics", json={
            "name": "Total Revenue",
            "datasource_id": str(sample_datasource_id),
            "description": "Sum of all revenue",
            "sql_expression": "SELECT SUM(amount) FROM t_metric_test",
            "required_table_ids": [table["id"]]
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["created"] is True
    
    def test_create_metric_invalid_sql(self, client, sample_datasource_id):
        """Test creating metric with invalid SQL fails"""
        response = client.post("/api/v1/admin/metrics", json={
            "name": "Bad Metric",
            "datasource_id": str(sample_datasource_id),
            "sql_expression": "SELECT * FROM"  # Invalid SQL (incomplete)
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_validate_metric(self, client, sample_datasource_id):
        """Test validating a metric"""
        table = client.post("/api/v1/admin/tables", json={
            "datasource_id": str(sample_datasource_id),
            "physical_name": "t_validate_metric",
            "semantic_name": "Validate",
            "columns": [{"name": "val", "data_type": "INT"}]
        }).json()
        
        metric = client.post("/api/v1/admin/metrics", json={
            "name": "Validate Test",
            "datasource_id": str(sample_datasource_id),
            "sql_expression": "SELECT AVG(val) FROM t_validate_metric",
            "required_table_ids": [table["id"]]
        }).json()
        
        response = client.post(f"/api/v1/admin/metrics/{metric['id']}/validate")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["is_valid"] is True


    
    def test_update_metric(self, client, sample_datasource_id):
        """Test updating a metric"""
        # Create table first
        table = client.post("/api/v1/admin/tables", json={
            "datasource_id": str(sample_datasource_id),
            "physical_name": "t_metric_upd",
            "semantic_name": "Metric Update Test"
        }).json()
        
        # Create metric
        metric = client.post("/api/v1/admin/metrics", json={
            "name": "To Update",
            "datasource_id": str(sample_datasource_id),
            "sql_expression": "SELECT COUNT(*) FROM t_metric_upd",
            "required_table_ids": [table["id"]]
        }).json()
        
        # Update
        response = client.put(f"/api/v1/admin/metrics/{metric['id']}", json={
            "name": "Updated Metric",
            "slug": "updated-metric-slug",
            "sql_expression": "SELECT COUNT(*) + 1 FROM t_metric_upd"
        })
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["updated"] is True
        assert data["slug"] == "updated-metric-slug"
        assert data["name"] == "Updated Metric"


# =============================================================================
# SYNONYMS TESTS
# =============================================================================

class TestSynonymsCRUD:
    """Tests for /admin/synonyms endpoints"""
    
    def test_list_synonyms(self, client):
        """Test listing synonyms"""
        response = client.get("/api/v1/admin/synonyms")
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), list)
    
    def test_create_synonyms_bulk(self, client, sample_datasource_id):
        """Test bulk creating synonyms"""
        table = client.post("/api/v1/admin/tables", json={
            "datasource_id": str(sample_datasource_id),
            "physical_name": "t_syn_test",
            "semantic_name": "Synonym Test"
        }).json()
        
        response = client.post("/api/v1/admin/synonyms/bulk", json={
            "target_id": table["id"],
            "target_type": "TABLE",
            "terms": ["customer", "client", "buyer"]
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert len(response.json()) == 3
    
    def test_create_synonyms_slugs(self, client, sample_datasource_id):
        """Test friendlier synonym slugs"""
        table = client.post("/api/v1/admin/tables", json={
            "datasource_id": str(sample_datasource_id),
            "physical_name": "t_syn_slug",
            "semantic_name": "Synonym Slug Test"
        }).json()

        response = client.post("/api/v1/admin/synonyms/bulk", json={
            "target_id": table["id"],
            "target_type": "TABLE",
            "terms": ["FriendlyTerm"]
        })
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data[0]["slug"] == "friendlyterm" # Should be simple term
        
        # Test collision fallback
        response2 = client.post("/api/v1/admin/synonyms/bulk", json={
            "target_id": table["id"],
            "target_type": "TABLE",
            "terms": ["FriendlyTerm"] # Duplicate term, same target -> existed=True
        })
        assert response2.json()[0]["existed"] is True
    
    def test_delete_synonym(self, client, sample_datasource_id):
        """Test deleting a synonym"""
        table = client.post("/api/v1/admin/tables", json={
            "datasource_id": str(sample_datasource_id),
            "physical_name": "t_syn_del",
            "semantic_name": "Syn Del"
        }).json()
        
        syns = client.post("/api/v1/admin/synonyms/bulk", json={
            "target_id": table["id"],
            "target_type": "TABLE",
            "terms": ["to_delete"]
        }).json()
        
        response = client.delete(f"/api/v1/admin/synonyms/{syns[0]['id']}")
        assert response.status_code == status.HTTP_204_NO_CONTENT


# =============================================================================
# CONTEXT RULES TESTS
# =============================================================================

class TestContextRulesCRUD:
    """Tests for /admin/context-rules endpoints"""
    
    def test_create_context_rule(self, client, sample_datasource_id):
        """Test creating a context rule"""
        table = client.post("/api/v1/admin/tables", json={
            "datasource_id": str(sample_datasource_id),
            "physical_name": "t_rule_test",
            "semantic_name": "Rule Test",
            "columns": [{"name": "deleted_at", "data_type": "TIMESTAMP"}]
        }).json()
        col_id = table["columns"][0]["id"]
        
        response = client.post("/api/v1/admin/context-rules", json={
            "column_id": col_id,
            "rule_text": "NULL means record is active, NOT NULL means soft deleted"
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["created"] is True
    
    def test_get_column_rules(self, client, sample_datasource_id):
        """Test getting rules for a column"""
        table = client.post("/api/v1/admin/tables", json={
            "datasource_id": str(sample_datasource_id),
            "physical_name": "t_get_rules",
            "semantic_name": "Get Rules",
            "columns": [{"name": "status", "data_type": "VARCHAR"}]
        }).json()
        col_id = table["columns"][0]["id"]
        
        client.post("/api/v1/admin/context-rules", json={
            "column_id": col_id,
            "rule_text": "Valid values are: active, pending, closed"
        })
        
        response = client.get(f"/api/v1/admin/columns/{col_id}/rules")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) >= 1


# =============================================================================
# NOMINAL VALUES TESTS
# =============================================================================

class TestNominalValuesCRUD:
    """Tests for /admin/columns/{id}/values endpoints"""
    
    def test_get_column_values(self, client, sample_datasource_id):
        """Test getting values for a column"""
        table = client.post("/api/v1/admin/tables", json={
            "datasource_id": str(sample_datasource_id),
            "physical_name": "t_val_test",
            "semantic_name": "Val Test",
            "columns": [{"name": "region", "data_type": "VARCHAR"}]
        }).json()
        col_id = table["columns"][0]["id"]
        
        response = client.get(f"/api/v1/admin/columns/{col_id}/values")
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), list)
    
    def test_add_value_manual(self, client, sample_datasource_id):
        """Test manually adding a value mapping"""
        table = client.post("/api/v1/admin/tables", json={
            "datasource_id": str(sample_datasource_id),
            "physical_name": "t_manual_val",
            "semantic_name": "Manual Val",
            "columns": [{"name": "country", "data_type": "VARCHAR"}]
        }).json()
        col_id = table["columns"][0]["id"]
        
        response = client.post(f"/api/v1/admin/columns/{col_id}/values/manual", json={
            "raw": "IT",
            "label": "Italia"
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["created"] is True
    
    def test_sync_values_placeholder(self, client, sample_datasource_id):
        """Test sync values endpoint (placeholder)"""
        table = client.post("/api/v1/admin/tables", json={
            "datasource_id": str(sample_datasource_id),
            "physical_name": "t_sync_val",
            "semantic_name": "Sync Val",
            "columns": [{"name": "code", "data_type": "VARCHAR"}]
        }).json()
        col_id = table["columns"][0]["id"]
        
        response = client.post(f"/api/v1/admin/columns/{col_id}/values/sync")
        assert response.status_code == status.HTTP_200_OK
        assert "message" in response.json()


# =============================================================================
# GOLDEN SQL TESTS
# =============================================================================

class TestGoldenSQLCRUD:
    """Tests for /admin/golden-sql endpoints"""
    
    def test_list_golden_sql(self, client):
        """Test listing golden SQL"""
        response = client.get("/api/v1/admin/golden-sql")
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), list)
    
    def test_create_golden_sql(self, client, sample_datasource_id):
        """Test creating a golden SQL example"""
        response = client.post("/api/v1/admin/golden-sql", json={
            "datasource_id": str(sample_datasource_id),
            "prompt_text": "How many users are active?",
            "sql_query": "SELECT COUNT(*) FROM users WHERE status = 'active'",
            "complexity": 1,
            "verified": True
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["created"] is True
    
    def test_create_golden_sql_invalid_sql(self, client, sample_datasource_id):
        """Test creating golden SQL with invalid SQL fails"""
        response = client.post("/api/v1/admin/golden-sql", json={
            "datasource_id": str(sample_datasource_id),
            "prompt_text": "Test",
            "sql_query": "SELECT * FROM"
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_update_golden_sql(self, client, sample_datasource_id):
        """Test updating a golden SQL"""
        create_resp = client.post("/api/v1/admin/golden-sql", json={
            "datasource_id": str(sample_datasource_id),
            "prompt_text": "Original question",
            "sql_query": "SELECT 1"
        })
        golden_id = create_resp.json()["id"]
        
        response = client.put(f"/api/v1/admin/golden-sql/{golden_id}", json={
            "prompt_text": "Updated question",
            "verified": True
        })
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["updated"] is True
    
    def test_import_golden_sql(self, client, sample_datasource_id):
        """Test bulk importing golden SQL"""
        response = client.post("/api/v1/admin/golden-sql/import", json={
            "datasource_id": str(sample_datasource_id),
            "items": [
                {"prompt_text": "Question 1", "sql_query": "SELECT 1"},
                {"prompt_text": "Question 2", "sql_query": "SELECT 2"},
                {"question": "Question 3", "sql": "SELECT 3"}  # Alternative keys
            ]
        })
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["imported_count"] == 3
        assert data["error_count"] == 0


# =============================================================================
# GRAPH VISUALIZATION TESTS
# =============================================================================

class TestGraphVisualization:
    """Tests for /admin/graph/visualize endpoint"""
    
    def test_graph_visualize_empty(self, client):
        """Test graph visualization with no data"""
        response = client.get("/api/v1/admin/graph/visualize")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "nodes" in data
        assert "edges" in data
        assert "metadata" in data
    
    def test_graph_visualize_with_data(self, client, sample_datasource_id):
        """Test graph visualization with tables and relationships"""
        t1 = client.post("/api/v1/admin/tables", json={
            "datasource_id": str(sample_datasource_id),
            "physical_name": "t_graph_1",
            "semantic_name": "Graph 1",
            "columns": [{"name": "id", "data_type": "INT"}]
        }).json()
        
        t2 = client.post("/api/v1/admin/tables", json={
            "datasource_id": str(sample_datasource_id),
            "physical_name": "t_graph_2",
            "semantic_name": "Graph 2",
            "columns": [{"name": "fk", "data_type": "INT"}]
        }).json()
        
        client.post("/api/v1/admin/relationships", json={
            "source_column_id": t2["columns"][0]["id"],
            "target_column_id": t1["columns"][0]["id"],
            "relationship_type": "ONE_TO_MANY"
        })
        
        response = client.get("/api/v1/admin/graph/visualize")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["nodes"]) >= 2
        assert len(data["edges"]) >= 1
    
    def test_graph_filter_by_datasource(self, client, sample_datasource_id):
        """Test graph filtered by datasource"""
        response = client.get(f"/api/v1/admin/graph/visualize?datasource_id={sample_datasource_id}")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["metadata"]["filtered_by_datasource"] == str(sample_datasource_id)
    
    def test_graph_include_columns(self, client, sample_datasource_id):
        """Test graph with columns included"""
        client.post("/api/v1/admin/tables", json={
            "datasource_id": str(sample_datasource_id),
            "physical_name": "t_graph_cols",
            "semantic_name": "Graph Cols",
            "columns": [
                {"name": "col1", "data_type": "INT"},
                {"name": "col2", "data_type": "VARCHAR"}
            ]
        })
        
        response = client.get("/api/v1/admin/graph/visualize?include_columns=true")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        column_nodes = [n for n in data["nodes"] if n["type"] == "column"]
        assert len(column_nodes) >= 2


# =============================================================================
# WORKFLOW TESTS (End-to-End)
# =============================================================================

class TestWorkflowEndToEnd:
    """
    End-to-end workflow tests that verify complete user journeys.
    These tests simulate real-world usage patterns.
    """
    
    def test_complete_schema_setup_workflow(self, client):
        """
        Complete workflow: Create datasource → tables → columns → relationships → graph
        """
        # Step 1: Create datasource
        ds_resp = client.post("/api/v1/admin/datasources", json={
            "name": "E-Commerce DB",
            "engine": "postgres",
            "description": "Main e-commerce database"
        })
        assert ds_resp.status_code == status.HTTP_201_CREATED
        ds_id = ds_resp.json()["id"]
        
        # Step 2: Create Customers table
        customers = client.post("/api/v1/admin/tables", json={
            "datasource_id": ds_id,
            "physical_name": "customers",
            "semantic_name": "Customers",
            "description": "Customer master data",
            "columns": [
                {"name": "id", "data_type": "INT", "is_primary_key": True, "semantic_name": "Customer ID"},
                {"name": "name", "data_type": "VARCHAR(255)", "semantic_name": "Customer Name"},
                {"name": "email", "data_type": "VARCHAR(255)", "semantic_name": "Email Address"}
            ]
        })
        assert customers.status_code == status.HTTP_201_CREATED
        customers_data = customers.json()
        customers_id = customers_data["id"]
        customers_pk = customers_data["columns"][0]["id"]
        
        # Step 3: Create Orders table
        orders = client.post("/api/v1/admin/tables", json={
            "datasource_id": ds_id,
            "physical_name": "orders",
            "semantic_name": "Orders",
            "description": "Customer orders",
            "columns": [
                {"name": "id", "data_type": "INT", "is_primary_key": True},
                {"name": "customer_id", "data_type": "INT"},
                {"name": "total", "data_type": "DECIMAL(10,2)"},
                {"name": "status", "data_type": "VARCHAR(50)"}
            ]
        })
        assert orders.status_code == status.HTTP_201_CREATED
        orders_data = orders.json()
        orders_id = orders_data["id"]
        orders_customer_fk = orders_data["columns"][1]["id"]
        orders_status = orders_data["columns"][3]["id"]
        
        # Step 4: Create relationship
        rel_resp = client.post("/api/v1/admin/relationships", json={
            "source_column_id": orders_customer_fk,
            "target_column_id": customers_pk,
            "relationship_type": "ONE_TO_MANY",
            "description": "Customer who placed the order"
        })
        assert rel_resp.status_code == status.HTTP_201_CREATED
        
        # Step 5: Add context rule for status column
        rule_resp = client.post("/api/v1/admin/context-rules", json={
            "column_id": orders_status,
            "rule_text": "Valid statuses: pending, confirmed, shipped, delivered, cancelled"
        })
        assert rule_resp.status_code == status.HTTP_201_CREATED
        
        # Step 6: Add synonyms
        syn_resp = client.post("/api/v1/admin/synonyms/bulk", json={
            "target_id": customers_id,
            "target_type": "TABLE",
            "terms": ["client", "buyer", "account"]
        })
        assert syn_resp.status_code == status.HTTP_201_CREATED
        
        # Step 7: Verify graph shows everything
        graph = client.get(f"/api/v1/admin/graph/visualize?datasource_id={ds_id}")
        assert graph.status_code == status.HTTP_200_OK
        graph_data = graph.json()
        assert graph_data["metadata"]["total_tables"] >= 2
        assert graph_data["metadata"]["total_relationships"] >= 1
        
        # Step 8: Verify relationships view
        rels = client.get(f"/api/v1/admin/tables/{customers_id}/relationships")
        assert rels.status_code == status.HTTP_200_OK
        rels_data = rels.json()
        assert len(rels_data["incoming"]) >= 1
        
        # Step 9: Refresh index
        refresh = client.post(f"/api/v1/admin/datasources/{ds_id}/refresh-index")
        assert refresh.status_code == status.HTTP_200_OK
        assert refresh.json()["updated_count"] >= 6  # ds + 2 tables + 7 columns
    
    def test_golden_sql_learning_workflow(self, client, sample_datasource_id):
        """
        Workflow: Create tables → Add golden SQL examples → Query
        """
        # Step 1: Create tables
        client.post("/api/v1/admin/tables", json={
            "datasource_id": str(sample_datasource_id),
            "physical_name": "products",
            "semantic_name": "Products",
            "columns": [
                {"name": "id", "data_type": "INT"},
                {"name": "name", "data_type": "VARCHAR"},
                {"name": "price", "data_type": "DECIMAL"}
            ]
        })
        
        # Step 2: Add golden SQL examples
        examples = [
            ("List all products", "SELECT * FROM products"),
            ("What is the most expensive product?", "SELECT * FROM products ORDER BY price DESC LIMIT 1"),
            ("How many products do we have?", "SELECT COUNT(*) FROM products")
        ]
        
        for prompt, sql in examples:
            resp = client.post("/api/v1/admin/golden-sql", json={
                "datasource_id": str(sample_datasource_id),
                "prompt_text": prompt,
                "sql_query": sql,
                "verified": True
            })
            assert resp.status_code == status.HTTP_201_CREATED
        
        # Step 3: Verify all were created
        golden_list = client.get(f"/api/v1/admin/golden-sql?datasource_id={sample_datasource_id}")
        assert golden_list.status_code == status.HTTP_200_OK
        assert len(golden_list.json()) >= 3
    
    def test_metric_definition_workflow(self, client, sample_datasource_id):
        """
        Workflow: Create table → Define metric → Validate → Add synonyms
        """
        # Step 1: Create sales table
        table = client.post("/api/v1/admin/tables", json={
            "datasource_id": str(sample_datasource_id),
            "physical_name": "sales",
            "semantic_name": "Sales",
            "columns": [
                {"name": "id", "data_type": "INT"},
                {"name": "amount", "data_type": "DECIMAL"},
                {"name": "date", "data_type": "DATE"}
            ]
        }).json()
        
        # Step 2: Create metric
        metric = client.post("/api/v1/admin/metrics", json={
            "name": "Total Sales",
            "datasource_id": str(sample_datasource_id),
            "description": "Sum of all sales amounts",
            "sql_expression": "SELECT SUM(amount) FROM sales",
            "required_table_ids": [table["id"]]
        })
        assert metric.status_code == status.HTTP_201_CREATED
        metric_id = metric.json()["id"]
        
        # Step 3: Validate metric
        validate = client.post(f"/api/v1/admin/metrics/{metric_id}/validate")
        assert validate.status_code == status.HTTP_200_OK
        assert validate.json()["is_valid"] is True
        
        # Step 4: Add synonyms for the metric
        syns = client.post("/api/v1/admin/synonyms/bulk", json={
            "target_id": metric_id,
            "target_type": "METRIC",
            "terms": ["revenue", "total earnings", "income"]
        })
        assert syns.status_code == status.HTTP_201_CREATED
        
        # Step 5: List synonyms by type
        syn_list = client.get("/api/v1/admin/synonyms?target_type=METRIC")
        assert syn_list.status_code == status.HTTP_200_OK
        metric_syns = [s for s in syn_list.json() if s["target_id"] == metric_id]
        assert len(metric_syns) >= 3
    
    def test_nominal_values_workflow(self, client, sample_datasource_id):
        """
        Workflow: Create table with categorical column → Map values manually
        """
        # Step 1: Create table with country column
        table = client.post("/api/v1/admin/tables", json={
            "datasource_id": str(sample_datasource_id),
            "physical_name": "addresses",
            "semantic_name": "Addresses",
            "columns": [
                {"name": "id", "data_type": "INT"},
                {"name": "country_code", "data_type": "VARCHAR(2)"}
            ]
        }).json()
        col_id = table["columns"][1]["id"]
        
        # Step 2: Add value mappings
        mappings = [
            ("IT", "Italia"),
            ("US", "United States"),
            ("DE", "Germany"),
            ("FR", "France")
        ]
        
        for raw, label in mappings:
            resp = client.post(f"/api/v1/admin/columns/{col_id}/values/manual", json={
                "raw": raw,
                "label": label
            })
            assert resp.status_code == status.HTTP_201_CREATED
        
        # Step 3: Verify values
        values = client.get(f"/api/v1/admin/columns/{col_id}/values")
        assert values.status_code == status.HTTP_200_OK
        assert len(values.json()) >= 4
        
        # Step 4: Update a value
        update = client.post(f"/api/v1/admin/columns/{col_id}/values/manual", json={
            "raw": "IT",
            "label": "Italy"  # Changed from Italia
        })
        assert update.status_code == status.HTTP_201_CREATED
        assert update.json()["updated"] is True
