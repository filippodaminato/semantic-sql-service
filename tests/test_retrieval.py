"""
Comprehensive tests for the Retrieval API endpoints.

Tests all 6 endpoints:
1. POST /search (Omni-Search)
2. POST /graph/expand (Graph Resolver)
3. POST /values/validate (Value Validator)
4. POST /schema/inspect (Schema Inspector)
5. POST /golden-sql/search (Wisdom Archive)
6. POST /concepts/explain (Semantic Explainer)
"""
import pytest
import uuid
from fastapi import status
from unittest import mock
from sqlalchemy.orm import Session

from src.db.models import (
    Datasource, TableNode, ColumnNode, SchemaEdge, SemanticMetric,
    LowCardinalityValue, SemanticSynonym, GoldenSQL, ColumnContextRule,
    SQLEngineType, RelationshipType, SynonymTargetType
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def sample_full_datasource(db_session):
    """
    Create a fully populated datasource with tables, columns, edges, etc.
    This provides a realistic test scenario.
    
    Structure:
    - Datasource: test_dwh
      - Table: products (id, name, category_id)
      - Table: categories (id, category_name)
      - Table: sales_log (id, prod_id, region_id, amount, sale_date)
      - Table: regions (id, region_name, region_code)
      
    Edges:
      - products.id -> sales_log.prod_id
      - categories.id -> products.category_id
      - regions.id -> sales_log.region_id
    """
    # Create datasource
    ds = Datasource(
        id=uuid.uuid4(),
        name="Test Data Warehouse",
        slug="test-dwh",
        description="Test DWH for unit tests",
        engine=SQLEngineType.POSTGRES,
        embedding=[0.1] * 1536
    )
    db_session.add(ds)
    db_session.flush()
    
    # Create tables
    products = TableNode(
        id=uuid.uuid4(),
        datasource_id=ds.id,
        physical_name="products",
        semantic_name="Products",
        description="Product catalog",
        ddl_context="CREATE TABLE products (id INT PRIMARY KEY, name VARCHAR, category_id INT);",
        embedding=[0.2] * 1536
    )
    
    categories = TableNode(
        id=uuid.uuid4(),
        datasource_id=ds.id,
        physical_name="categories",
        semantic_name="Categories",
        description="Product categories",
        ddl_context="CREATE TABLE categories (id INT PRIMARY KEY, category_name VARCHAR);",
        embedding=[0.3] * 1536
    )
    
    sales_log = TableNode(
        id=uuid.uuid4(),
        datasource_id=ds.id,
        physical_name="sales_log",
        semantic_name="Sales Log",
        description="Sales transactions log",
        ddl_context="CREATE TABLE sales_log (id INT, prod_id INT, region_id INT, amount DECIMAL);",
        embedding=[0.4] * 1536
    )
    
    regions = TableNode(
        id=uuid.uuid4(),
        datasource_id=ds.id,
        physical_name="regions",
        semantic_name="Regions",
        description="Geographic regions",
        embedding=[0.5] * 1536
    )
    
    db_session.add_all([products, categories, sales_log, regions])
    db_session.flush()
    
    # Create columns - Products
    prod_id = ColumnNode(
        id=uuid.uuid4(),
        table_id=products.id,
        name="id",
        semantic_name="Product ID",
        data_type="INT",
        is_primary_key=True,
        embedding=[0.1] * 1536
    )
    prod_name = ColumnNode(
        id=uuid.uuid4(),
        table_id=products.id,
        name="name",
        semantic_name="Product Name",
        data_type="VARCHAR",
        description="Name of the product",
        embedding=[0.11] * 1536
    )
    prod_cat_id = ColumnNode(
        id=uuid.uuid4(),
        table_id=products.id,
        name="category_id",
        data_type="INT",
        embedding=[0.12] * 1536
    )
    
    # Create columns - Categories
    cat_id = ColumnNode(
        id=uuid.uuid4(),
        table_id=categories.id,
        name="id",
        data_type="INT",
        is_primary_key=True,
        embedding=[0.2] * 1536
    )
    cat_name = ColumnNode(
        id=uuid.uuid4(),
        table_id=categories.id,
        name="category_name",
        data_type="VARCHAR",
        embedding=[0.21] * 1536
    )
    
    # Create columns - Sales Log
    sale_id = ColumnNode(
        id=uuid.uuid4(),
        table_id=sales_log.id,
        name="id",
        data_type="INT",
        is_primary_key=True,
        embedding=[0.3] * 1536
    )
    sale_prod_id = ColumnNode(
        id=uuid.uuid4(),
        table_id=sales_log.id,
        name="prod_id",
        data_type="INT",
        embedding=[0.31] * 1536
    )
    sale_region_id = ColumnNode(
        id=uuid.uuid4(),
        table_id=sales_log.id,
        name="region_id",
        data_type="INT",
        embedding=[0.32] * 1536
    )
    sale_amount = ColumnNode(
        id=uuid.uuid4(),
        table_id=sales_log.id,
        name="amount",
        semantic_name="Sale Amount",
        data_type="DECIMAL",
        context_note="Amount in EUR",
        embedding=[0.33] * 1536
    )
    sale_date = ColumnNode(
        id=uuid.uuid4(),
        table_id=sales_log.id,
        name="sale_date",
        data_type="DATE",
        context_note="Format: YYYY-MM-DD",
        embedding=[0.34] * 1536
    )
    
    # Create columns - Regions
    reg_id = ColumnNode(
        id=uuid.uuid4(),
        table_id=regions.id,
        name="id",
        data_type="INT",
        is_primary_key=True,
        embedding=[0.4] * 1536
    )
    reg_name = ColumnNode(
        id=uuid.uuid4(),
        table_id=regions.id,
        name="region_name",
        data_type="VARCHAR",
        embedding=[0.41] * 1536
    )
    reg_code = ColumnNode(
        id=uuid.uuid4(),
        table_id=regions.id,
        name="region_code",
        data_type="VARCHAR(3)",
        description="3-letter region code",
        embedding=[0.42] * 1536
    )
    
    db_session.add_all([
        prod_id, prod_name, prod_cat_id,
        cat_id, cat_name,
        sale_id, sale_prod_id, sale_region_id, sale_amount, sale_date,
        reg_id, reg_name, reg_code
    ])
    db_session.flush()
    
    # Create edges (relationships)
    # products.id -> sales_log.prod_id
    edge1 = SchemaEdge(
        source_column_id=prod_id.id,
        target_column_id=sale_prod_id.id,
        relationship_type=RelationshipType.ONE_TO_MANY
    )
    # categories.id -> products.category_id
    edge2 = SchemaEdge(
        source_column_id=cat_id.id,
        target_column_id=prod_cat_id.id,
        relationship_type=RelationshipType.ONE_TO_MANY
    )
    # regions.id -> sales_log.region_id
    edge3 = SchemaEdge(
        source_column_id=reg_id.id,
        target_column_id=sale_region_id.id,
        relationship_type=RelationshipType.ONE_TO_MANY
    )
    
    db_session.add_all([edge1, edge2, edge3])
    db_session.flush()
    
    # Create context rule (critical rule)
    rule = ColumnContextRule(
        column_id=sale_amount.id,
        rule_text="SEMPRE convertire in EUR se diversa valuta",
        embedding=[0.5] * 1536
    )
    db_session.add(rule)
    
    # Create low cardinality values
    lcv1 = LowCardinalityValue(
        column_id=reg_code.id,
        value_raw="LOM",
        value_label="Lombardia",
        embedding=[0.6] * 1536
    )
    lcv2 = LowCardinalityValue(
        column_id=reg_code.id,
        value_raw="PIE",
        value_label="Piemonte",
        embedding=[0.61] * 1536
    )
    lcv3 = LowCardinalityValue(
        column_id=reg_code.id,
        value_raw="TOS",
        value_label="Toscana",
        embedding=[0.62] * 1536
    )
    db_session.add_all([lcv1, lcv2, lcv3])
    
    # Create metrics
    metric = SemanticMetric(
        name="Total Revenue",
        description="Sum of all sales amounts",
        calculation_sql="SUM(sales_log.amount)",
        required_tables=[str(sales_log.id)],
        embedding=[0.7] * 1536
    )
    db_session.add(metric)
    
    # Create golden SQL
    golden = GoldenSQL(
        datasource_id=ds.id,
        prompt_text="Quanto hanno venduto in Lombardia?",
        sql_query="SELECT SUM(amount) FROM sales_log s JOIN regions r ON s.region_id = r.id WHERE r.region_code = 'LOM'",
        complexity_score=3,
        verified=True,
        embedding=[0.8] * 1536
    )
    db_session.add(golden)
    
    # Flush metric and golden to get IDs
    db_session.flush()
    
    # Create synonym (needs metric.id)
    synonym = SemanticSynonym(
        term="Fatturato",
        target_type=SynonymTargetType.METRIC,
        target_id=metric.id
    )
    db_session.add(synonym)
    
    db_session.commit()
    
    return {
        "datasource": ds,
        "tables": {
            "products": products,
            "categories": categories,
            "sales_log": sales_log,
            "regions": regions
        },
        "columns": {
            "prod_id": prod_id,
            "reg_code": reg_code,
            "sale_amount": sale_amount
        },
        "metric": metric,
        "golden": golden,
        "synonym": synonym
    }


# =============================================================================
# 1. OMNI-SEARCH TESTS
# =============================================================================

class TestOmniSearch:
    """Tests for POST /api/v1/retrieval/search"""
    
    def test_semantic_search_returns_tables(self, client, sample_full_datasource):
        """Test semantic search finds tables by description."""
        response = client.post(
            "/api/v1/retrieval/search",
            json={
                "query": "product catalog",
                "limit": 10
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "hits" in data
        assert "total" in data
        
        # Should find tables
        table_hits = [h for h in data["hits"] if h["type"] == "TABLE"]
        assert len(table_hits) > 0
    
    def test_semantic_search_with_datasource_filter(self, client, sample_full_datasource):
        """Test search scoped to specific datasource."""
        response = client.post(
            "/api/v1/retrieval/search",
            json={
                "query": "sales",
                "filters": {
                    "datasource_slug": "test-dwh"
                },
                "limit": 5
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # All table hits should belong to the filtered datasource
        table_hits = [h for h in data["hits"] if h["type"] == "TABLE"]
        for hit in table_hits:
            assert hit["datasource_id"] == str(sample_full_datasource["datasource"].id)
    
    def test_drilldown_from_datasource_to_tables(self, client, sample_full_datasource):
        """Test drill-down: Datasource -> Tables."""
        ds_id = sample_full_datasource["datasource"].id
        
        response = client.post(
            "/api/v1/retrieval/search",
            json={
                "filters": {
                    "parent_id": str(ds_id)
                },
                "limit": 10
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # All hits should be tables
        assert len(data["hits"]) == 4  # products, categories, sales_log, regions
        for hit in data["hits"]:
            assert hit["type"] == "TABLE"
    
    def test_drilldown_from_table_to_columns(self, client, sample_full_datasource):
        """Test drill-down: Table -> Columns."""
        table_id = sample_full_datasource["tables"]["products"].id
        
        response = client.post(
            "/api/v1/retrieval/search",
            json={
                "filters": {
                    "parent_id": str(table_id)
                },
                "limit": 10
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # All hits should be columns
        assert len(data["hits"]) == 3  # id, name, category_id
        for hit in data["hits"]:
            assert hit["type"] == "COLUMN"
            assert "data_type" in hit
            assert "is_pk" in hit
    
    def test_search_returns_critical_rules_on_tables(self, client, sample_full_datasource):
        """Test that TABLE hits include critical_rules."""
        response = client.post(
            "/api/v1/retrieval/search",
            json={
                "query": "sales transactions",
                "filters": {"entity_types": ["TABLE"]},
                "limit": 10
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Find sales_log table
        sales_table = next(
            (h for h in data["hits"] if h["physical_name"] == "sales_log"), 
            None
        )
        if sales_table:
            assert "critical_rules" in sales_table
    
    def test_search_requires_query_or_parent_id(self, client, sample_full_datasource):
        """Test that search fails if neither query nor parent_id is provided."""
        response = client.post(
            "/api/v1/retrieval/search",
            json={"limit": 10}
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_search_entity_type_filter(self, client, sample_full_datasource):
        """Test filtering by entity type."""
        response = client.post(
            "/api/v1/retrieval/search",
            json={
                "query": "revenue",
                "filters": {"entity_types": ["METRIC"]},
                "limit": 10
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # All hits should be metrics
        for hit in data["hits"]:
            assert hit["type"] == "METRIC"


# =============================================================================
# 2. GRAPH RESOLVER TESTS
# =============================================================================

class TestGraphResolver:
    """Tests for POST /api/v1/retrieval/graph/expand"""
    
    def test_expand_finds_direct_path(self, client, sample_full_datasource):
        """Test finding path between directly connected tables."""
        response = client.post(
            "/api/v1/retrieval/graph/expand",
            json={
                "datasource_slug": "test-dwh",
                "anchor_entities": ["products", "sales_log"]
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["path_found"] is True
        assert len(data["relationships"]) >= 1
        
        # Should have a relationship from products to sales_log
        rels = data["relationships"]
        assert any(
            r["source_table"] == "products" or r["target_table"] == "products" 
            for r in rels
        )
    
    def test_expand_finds_bridge_tables(self, client, sample_full_datasource):
        """Test that bridge tables are identified."""
        # products -> sales_log <- regions
        # Asking for products and regions should return sales_log as bridge
        response = client.post(
            "/api/v1/retrieval/graph/expand",
            json={
                "datasource_slug": "test-dwh",
                "anchor_entities": ["products", "regions"]
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["path_found"] is True
        # sales_log should be a bridge table
        assert "sales_log" in data["bridge_tables"]
    
    def test_expand_returns_join_conditions(self, client, sample_full_datasource):
        """Test that join conditions are included in relationships."""
        response = client.post(
            "/api/v1/retrieval/graph/expand",
            json={
                "datasource_slug": "test-dwh",
                "anchor_entities": ["products", "sales_log"]
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        for rel in data["relationships"]:
            assert "join_condition" in rel
            assert "=" in rel["join_condition"]  # Should be a valid condition
    
    def test_expand_requires_at_least_two_anchors(self, client, sample_full_datasource):
        """Test that at least 2 anchors are required."""
        response = client.post(
            "/api/v1/retrieval/graph/expand",
            json={
                "datasource_slug": "test-dwh",
                "anchor_entities": ["products"]
            }
        )
        
        # Should fail validation
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_expand_invalid_datasource(self, client, sample_full_datasource):
        """Test error for non-existent datasource."""
        response = client.post(
            "/api/v1/retrieval/graph/expand",
            json={
                "datasource_slug": "nonexistent-db",
                "anchor_entities": ["products", "sales_log"]
            }
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# 3. VALUE VALIDATOR TESTS
# =============================================================================

class TestValueValidator:
    """Tests for POST /api/v1/retrieval/values/validate"""
    
    def test_validate_exact_match(self, client, sample_full_datasource):
        """Test exact match validation."""
        response = client.post(
            "/api/v1/retrieval/values/validate",
            json={
                "datasource_slug": "test-dwh",
                "target": {"table": "regions", "column": "region_code"},
                "proposed_values": ["Lombardia"]
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["valid"] is True
        assert data["mappings"]["Lombardia"] == "LOM"
    
    def test_validate_unresolved_values(self, client, sample_full_datasource):
        """Test handling of values that cannot be resolved."""
        with mock.patch(
            "src.services.embedding_service.embedding_service.generate_embedding"
        ) as mock_embed:
            # Return very different embedding for unknown value
            mock_embed.return_value = [0.0] * 1536
            
            response = client.post(
                "/api/v1/retrieval/values/validate",
                json={
                    "datasource_slug": "test-dwh",
                    "target": {"table": "regions", "column": "region_code"},
                    "proposed_values": ["NonExistentRegion"]
                }
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["valid"] is False
        assert "NonExistentRegion" in data["unresolved"]
    
    def test_validate_mixed_values(self, client, sample_full_datasource):
        """Test mix of valid and invalid values."""
        with mock.patch(
            "src.services.embedding_service.embedding_service.generate_embedding"
        ) as mock_embed:
            def side_effect(text):
                if text == "Unknown":
                    return [0.0] * 1536
                return [0.6] * 1536  # Similar to Lombardia
            mock_embed.side_effect = side_effect
            
            response = client.post(
                "/api/v1/retrieval/values/validate",
                json={
                    "datasource_slug": "test-dwh",
                    "target": {"table": "regions", "column": "region_code"},
                    "proposed_values": ["Lombardia", "Unknown"]
                }
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["valid"] is False
        assert "Lombardia" in data["mappings"]
        assert "Unknown" in data["unresolved"]
    
    def test_validate_column_not_found(self, client, sample_full_datasource):
        """Test error for non-existent column."""
        response = client.post(
            "/api/v1/retrieval/values/validate",
            json={
                "datasource_slug": "test-dwh",
                "target": {"table": "regions", "column": "nonexistent"},
                "proposed_values": ["value"]
            }
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# 4. SCHEMA INSPECTOR TESTS
# =============================================================================

class TestSchemaInspector:
    """Tests for POST /api/v1/retrieval/schema/inspect"""
    
    def test_inspect_returns_ddl(self, client, sample_full_datasource):
        """Test that DDL is returned for requested tables."""
        response = client.post(
            "/api/v1/retrieval/schema/inspect",
            json={
                "datasource_slug": "test-dwh",
                "table_names": ["products"],
                "include_samples": False
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert len(data["schemas"]) == 1
        schema = data["schemas"][0]
        assert schema["table_name"] == "products"
        assert "CREATE TABLE" in schema["ddl"]
    
    def test_inspect_returns_column_metadata(self, client, sample_full_datasource):
        """Test that column metadata is returned."""
        response = client.post(
            "/api/v1/retrieval/schema/inspect",
            json={
                "datasource_slug": "test-dwh",
                "table_names": ["products"],
                "include_samples": False
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        schema = data["schemas"][0]
        assert len(schema["columns_metadata"]) == 3
        
        # Check primary key is identified
        pk_col = next(
            (c for c in schema["columns_metadata"] if c["name"] == "id"), 
            None
        )
        assert pk_col is not None
        assert pk_col["is_primary_key"] is True
    
    def test_inspect_multiple_tables(self, client, sample_full_datasource):
        """Test inspecting multiple tables at once."""
        response = client.post(
            "/api/v1/retrieval/schema/inspect",
            json={
                "datasource_slug": "test-dwh",
                "table_names": ["products", "sales_log", "regions"],
                "include_samples": False
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert len(data["schemas"]) == 3
    
    def test_inspect_with_samples(self, client, sample_full_datasource):
        """Test including sample values."""
        response = client.post(
            "/api/v1/retrieval/schema/inspect",
            json={
                "datasource_slug": "test-dwh",
                "table_names": ["regions"],
                "include_samples": True
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # region_code column should have sample values
        schema = data["schemas"][0]
        code_col = next(
            (c for c in schema["columns_metadata"] if c["name"] == "region_code"), 
            None
        )
        if code_col:
            # We added 3 LowCardinalityValues for region_code
            assert len(code_col["sample_values"]) > 0
    
    def test_inspect_returns_global_rules(self, client, sample_full_datasource):
        """Test that context rules are aggregated."""
        response = client.post(
            "/api/v1/retrieval/schema/inspect",
            json={
                "datasource_slug": "test-dwh",
                "table_names": ["sales_log"],
                "include_samples": False
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        schema = data["schemas"][0]
        # We added a rule for the amount column
        assert len(schema["global_rules"]) >= 1
        assert any("EUR" in r for r in schema["global_rules"])


# =============================================================================
# 5. WISDOM ARCHIVE TESTS
# =============================================================================

class TestWisdomArchive:
    """Tests for POST /api/v1/retrieval/golden-sql/search"""
    
    def test_search_golden_sql(self, client, sample_full_datasource):
        """Test searching for golden SQL examples."""
        response = client.post(
            "/api/v1/retrieval/golden-sql/search",
            json={
                "query": "vendite Lombardia",
                "datasource_slug": "test-dwh",
                "limit": 3
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "matches" in data
        assert len(data["matches"]) >= 1
        
        match = data["matches"][0]
        assert "question" in match
        assert "sql" in match
        assert "score" in match
        assert match["score"] >= 0 and match["score"] <= 1
    
    def test_search_golden_sql_returns_complexity(self, client, sample_full_datasource):
        """Test that complexity is included in response."""
        response = client.post(
            "/api/v1/retrieval/golden-sql/search",
            json={
                "query": "vendite",
                "datasource_slug": "test-dwh",
                "limit": 1
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        if data["matches"]:
            assert "complexity" in data["matches"][0]
    
    def test_search_golden_sql_invalid_datasource(self, client, sample_full_datasource):
        """Test error for non-existent datasource."""
        response = client.post(
            "/api/v1/retrieval/golden-sql/search",
            json={
                "query": "vendite",
                "datasource_slug": "nonexistent-db",
                "limit": 3
            }
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# 6. SEMANTIC EXPLAINER TESTS
# =============================================================================

class TestSemanticExplainer:
    """Tests for POST /api/v1/retrieval/concepts/explain"""
    
    def test_explain_metric(self, client, sample_full_datasource):
        """Test explaining a metric."""
        response = client.post(
            "/api/v1/retrieval/concepts/explain",
            json={
                "concepts": ["Total Revenue"],
                "datasource_slug": "test-dwh"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert len(data["metrics"]) == 1
        metric = data["metrics"][0]
        assert metric["name"] == "Total Revenue"
        assert "SUM" in metric["sql_template"]
    
    def test_explain_synonym(self, client, sample_full_datasource):
        """Test explaining a synonym."""
        response = client.post(
            "/api/v1/retrieval/concepts/explain",
            json={
                "concepts": ["Fatturato"],
                "datasource_slug": "test-dwh"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert len(data["synonyms"]) == 1
        synonym = data["synonyms"][0]
        assert synonym["term"] == "Fatturato"
        assert synonym["target_type"] == "METRIC"
    
    def test_explain_unresolved_concept(self, client, sample_full_datasource):
        """Test handling of unknown concepts."""
        response = client.post(
            "/api/v1/retrieval/concepts/explain",
            json={
                "concepts": ["NonExistentConcept"],
                "datasource_slug": "test-dwh"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "NonExistentConcept" in data["unresolved"]
    
    def test_explain_multiple_concepts(self, client, sample_full_datasource):
        """Test explaining multiple concepts at once."""
        response = client.post(
            "/api/v1/retrieval/concepts/explain",
            json={
                "concepts": ["Total Revenue", "Fatturato", "Unknown"],
                "datasource_slug": "test-dwh"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert len(data["metrics"]) >= 1
        assert len(data["synonyms"]) >= 1
        assert "Unknown" in data["unresolved"]


# =============================================================================
# ADMIN ENDPOINT TESTS
# =============================================================================

class TestAdminSyncEmbeddings:
    """Tests for POST /api/v1/retrieval/admin/sync-embeddings"""
    
    def test_sync_embeddings(self, client, db_session):
        """Test embedding sync updates entities without embeddings."""
        # Create entity without embedding hash
        ds = Datasource(
            name="Sync Test",
            slug="sync-test",
            description="Test sync",
            engine=SQLEngineType.POSTGRES
        )
        db_session.add(ds)
        db_session.commit()
        
        assert ds.embedding is None
        assert ds.embedding_hash is None
        
        response = client.post("/api/v1/retrieval/admin/sync-embeddings")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"
        assert data["updated_entities"] >= 1
        
        db_session.refresh(ds)
        assert ds.embedding is not None
        assert ds.embedding_hash is not None

    def test_sync_embeddings_with_all_entity_types(self, client, db_session):
        """Test embedding sync with tables, columns, and metrics."""
        # Create datasource
        ds = Datasource(
            name="Full Sync Test",
            slug="full-sync-test",
            description="Full sync test",
            engine=SQLEngineType.POSTGRES
        )
        db_session.add(ds)
        db_session.flush()
        
        # Create table
        table = TableNode(
            datasource_id=ds.id,
            physical_name="sync_table",
            semantic_name="Sync Table",
            description="Table for sync test"
        )
        db_session.add(table)
        db_session.flush()
        
        # Create column with description and context_note
        col = ColumnNode(
            table_id=table.id,
            name="sync_col",
            semantic_name="Sync Column",
            data_type="VARCHAR",
            description="Column description",
            context_note="Column context note"
        )
        db_session.add(col)
        
        # Create metric with description
        metric = SemanticMetric(
            name="Sync Metric",
            description="Metric description",
            calculation_sql="SUM(amount)"
        )
        db_session.add(metric)
        db_session.commit()
        
        response = client.post("/api/v1/retrieval/admin/sync-embeddings")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["updated_entities"] >= 4  # ds, table, col, metric

    def test_sync_embeddings_clears_empty_content(self, client, db_session):
        """Test that sync clears embeddings when content is empty."""
        # Create datasource with embedding but empty content
        ds = Datasource(
            name="Empty Test",
            slug="empty-test",
            description="",  # Empty
            context_signature="",  # Empty
            engine=SQLEngineType.POSTGRES,
            embedding=[0.1] * 1536,
            embedding_hash="old_hash"
        )
        db_session.add(ds)
        db_session.commit()
        
        response = client.post("/api/v1/retrieval/admin/sync-embeddings")
        
        assert response.status_code == status.HTTP_200_OK
        
        db_session.refresh(ds)
        # Embedding should be cleared for empty content
        assert ds.embedding is None
        assert ds.embedding_hash is None


# =============================================================================
# ADDITIONAL EDGE CASE TESTS FOR 100% COVERAGE
# =============================================================================

class TestOmniSearchEdgeCases:
    """Additional edge case tests for search endpoint."""
    
    def test_drilldown_with_invalid_parent_id(self, client, sample_full_datasource):
        """Test drill-down with non-existent parent ID returns 404."""
        fake_uuid = str(uuid.uuid4())
        
        response = client.post(
            "/api/v1/retrieval/search",
            json={
                "filters": {
                    "parent_id": fake_uuid
                },
                "limit": 10
            }
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()


class TestGraphResolverEdgeCases:
    """Additional edge case tests for graph expand endpoint."""
    
    def test_expand_with_uuid_anchors(self, client, sample_full_datasource):
        """Test expand using UUIDs instead of table names."""
        products_id = str(sample_full_datasource["tables"]["products"].id)
        sales_id = str(sample_full_datasource["tables"]["sales_log"].id)
        
        response = client.post(
            "/api/v1/retrieval/graph/expand",
            json={
                "datasource_slug": "test-dwh",
                "anchor_entities": [products_id, sales_id]
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["path_found"] is True
    
    def test_expand_with_invalid_uuid_anchor(self, client, sample_full_datasource):
        """Test expand with UUID that doesn't exist in datasource."""
        fake_uuid = str(uuid.uuid4())
        
        response = client.post(
            "/api/v1/retrieval/graph/expand",
            json={
                "datasource_slug": "test-dwh",
                "anchor_entities": ["products", fake_uuid]
            }
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_expand_with_invalid_name_anchor(self, client, sample_full_datasource):
        """Test expand with table name that doesn't exist."""
        response = client.post(
            "/api/v1/retrieval/graph/expand",
            json={
                "datasource_slug": "test-dwh",
                "anchor_entities": ["products", "nonexistent_table"]
            }
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_expand_with_multiple_anchors(self, client, sample_full_datasource):
        """Test expand with more than 2 anchor entities."""
        response = client.post(
            "/api/v1/retrieval/graph/expand",
            json={
                "datasource_slug": "test-dwh",
                "anchor_entities": ["products", "sales_log", "regions"]
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["path_found"] is True
        assert len(data["relationships"]) >= 2
    
    def test_expand_with_same_table_twice(self, client, sample_full_datasource):
        """Test expand with same table specified twice results in <2 distinct anchors."""
        response = client.post(
            "/api/v1/retrieval/graph/expand",
            json={
                "datasource_slug": "test-dwh",
                "anchor_entities": ["products", "products"]
            }
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "2 distinct" in response.json()["detail"]


class TestValueValidatorEdgeCases:
    """Additional edge case tests for value validation endpoint."""
    
    def test_validate_with_no_vector_match(self, client, db_session):
        """Test validation when no embeddings exist for column values."""
        # Create minimal setup without embeddings
        ds = Datasource(
            name="No Embed DB",
            slug="no-embed-db",
            engine=SQLEngineType.POSTGRES
        )
        db_session.add(ds)
        db_session.flush()
        
        table = TableNode(
            datasource_id=ds.id,
            physical_name="no_embed_table",
            semantic_name="No Embed Table"
        )
        db_session.add(table)
        db_session.flush()
        
        col = ColumnNode(
            table_id=table.id,
            name="status",
            data_type="VARCHAR"
        )
        db_session.add(col)
        db_session.flush()
        
        # Add value WITHOUT embedding
        lcv = LowCardinalityValue(
            column_id=col.id,
            value_raw="ACTIVE",
            value_label="Active",
            embedding=None  # No embedding
        )
        db_session.add(lcv)
        db_session.commit()
        
        with mock.patch(
            "src.services.embedding_service.embedding_service.generate_embedding"
        ) as mock_embed:
            mock_embed.return_value = [0.5] * 1536
            
            response = client.post(
                "/api/v1/retrieval/values/validate",
                json={
                    "datasource_slug": "no-embed-db",
                    "target": {"table": "no_embed_table", "column": "status"},
                    "proposed_values": ["UnknownValue"]
                }
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["valid"] is False
        assert "UnknownValue" in data["unresolved"]


class TestSemanticExplainerEdgeCases:
    """Additional edge case tests for concepts explain endpoint."""
    
    def test_explain_table_synonym(self, client, db_session, sample_full_datasource):
        """Test explaining a synonym that points to a TABLE."""
        products_table = sample_full_datasource["tables"]["products"]
        
        # Create table synonym
        table_syn = SemanticSynonym(
            term="Catalogo Prodotti",
            target_type=SynonymTargetType.TABLE,
            target_id=products_table.id
        )
        db_session.add(table_syn)
        db_session.commit()
        
        response = client.post(
            "/api/v1/retrieval/concepts/explain",
            json={
                "concepts": ["Catalogo Prodotti"],
                "datasource_slug": "test-dwh"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert len(data["synonyms"]) >= 1
        syn = next((s for s in data["synonyms"] if s["term"] == "Catalogo Prodotti"), None)
        assert syn is not None
        assert "Table:" in syn["resolved_to"]
    
    def test_explain_column_synonym(self, client, db_session, sample_full_datasource):
        """Test explaining a synonym that points to a COLUMN."""
        prod_id_col = sample_full_datasource["columns"]["prod_id"]
        
        # Create column synonym
        col_syn = SemanticSynonym(
            term="Codice Prodotto",
            target_type=SynonymTargetType.COLUMN,
            target_id=prod_id_col.id
        )
        db_session.add(col_syn)
        db_session.commit()
        
        response = client.post(
            "/api/v1/retrieval/concepts/explain",
            json={
                "concepts": ["Codice Prodotto"],
                "datasource_slug": "test-dwh"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        syn = next((s for s in data["synonyms"] if s["term"] == "Codice Prodotto"), None)
        assert syn is not None
        assert "Column:" in syn["resolved_to"]
    
    def test_explain_metric_synonym(self, client, db_session, sample_full_datasource):
        """Test explaining a synonym that points to a METRIC (should resolve name)."""
        metric = sample_full_datasource["metric"]
        
        # Create metric synonym
        metric_syn = SemanticSynonym(
            term="Ricavi Totali",
            target_type=SynonymTargetType.METRIC,
            target_id=metric.id
        )
        db_session.add(metric_syn)
        db_session.commit()
        
        response = client.post(
            "/api/v1/retrieval/concepts/explain",
            json={
                "concepts": ["Ricavi Totali"],
                "datasource_slug": "test-dwh"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        syn = next((s for s in data["synonyms"] if s["term"] == "Ricavi Totali"), None)
        assert syn is not None
        assert "Metric:" in syn["resolved_to"]
    
    def test_explain_without_datasource_slug(self, client, sample_full_datasource):
        """Test explaining concepts without specifying datasource."""
        response = client.post(
            "/api/v1/retrieval/concepts/explain",
            json={
                "concepts": ["Total Revenue"]
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Should still find the metric
        assert len(data["metrics"]) >= 1


class TestSchemaInspectorEdgeCases:
    """Additional edge case tests for schema inspect endpoint."""
    
    def test_inspect_table_without_ddl_generates_one(self, client, db_session):
        """Test that DDL is generated if not stored."""
        ds = Datasource(
            name="No DDL DB",
            slug="no-ddl-db",
            engine=SQLEngineType.POSTGRES
        )
        db_session.add(ds)
        db_session.flush()
        
        table = TableNode(
            datasource_id=ds.id,
            physical_name="no_ddl_table",
            semantic_name="No DDL Table",
            ddl_context=None  # No stored DDL
        )
        db_session.add(table)
        db_session.flush()
        
        col = ColumnNode(
            table_id=table.id,
            name="id",
            data_type="INT",
            is_primary_key=True
        )
        db_session.add(col)
        db_session.commit()
        
        response = client.post(
            "/api/v1/retrieval/schema/inspect",
            json={
                "datasource_slug": "no-ddl-db",
                "table_names": ["no_ddl_table"],
                "include_samples": False
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        schema = data["schemas"][0]
        assert "CREATE TABLE" in schema["ddl"]
        assert "PRIMARY KEY" in schema["ddl"]
    
    def test_inspect_skips_unknown_tables(self, client, sample_full_datasource):
        """Test that unknown table names are silently skipped."""
        response = client.post(
            "/api/v1/retrieval/schema/inspect",
            json={
                "datasource_slug": "test-dwh",
                "table_names": ["products", "nonexistent_table"],
                "include_samples": False
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Only products should be returned
        assert len(data["schemas"]) == 1
        assert data["schemas"][0]["table_name"] == "products"

