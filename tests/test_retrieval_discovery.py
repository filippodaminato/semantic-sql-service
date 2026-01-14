import pytest
from uuid import uuid4
from src.db.models import (
    Datasource, TableNode, ColumnNode, SchemaEdge, SemanticMetric, 
    SemanticSynonym, ColumnContextRule, LowCardinalityValue, GoldenSQL,
    SQLEngineType, RelationshipType, SynonymTargetType
)

# =============================================================================
# FIXTURES (Data Seeding)
# =============================================================================

@pytest.fixture
def discovery_seed(db_session, sample_datasource):
    """Seed data for discovery tests."""
    # 1. Datasource (from fixture)
    ds = sample_datasource
    
    # 2. Table
    table = TableNode(
        id=uuid4(),
        datasource_id=ds.id,
        physical_name="t_orders",
        slug="orders_table",
        semantic_name="Orders",
        description="Main orders table"
    )
    db_session.add(table)
    
    table2 = TableNode(
        id=uuid4(),
        datasource_id=ds.id,
        physical_name="t_users",
        slug="users_table",
        semantic_name="Users",
        description="Users table"
    )
    db_session.add(table2)
    db_session.flush()

    # 3. Column
    col1 = ColumnNode(
        id=uuid4(),
        table_id=table.id,
        name="ord_id",
        slug="order_id_col",
        semantic_name="Order ID",
        data_type="INT",
        description="Unique identifier"
    )
    col2 = ColumnNode(
        id=uuid4(),
        table_id=table.id,
        name="user_ref",
        slug="user_ref_col",
        semantic_name="User Reference",
        data_type="INT"
    )
    col3 = ColumnNode(
        id=uuid4(),
        table_id=table2.id, # Users table
        name="user_id",
        slug="user_id_col",
        semantic_name="User ID",
        data_type="INT",
        is_primary_key=True
    )
    db_session.add_all([col1, col2, col3])
    db_session.flush()

    # 4. Metric
    metric = SemanticMetric(
        id=uuid4(),
        datasource_id=ds.id,
        name="Total Orders",
        slug="total_orders_metric",
        description="Count of all orders",
        calculation_sql="SELECT COUNT(*) FROM t_orders",
        required_tables=[str(table.id)] # Store as UUID string
    )
    db_session.add(metric)

    # 5. Synonym
    synonym = SemanticSynonym(
        id=uuid4(),
        term="clients",
        slug="synonym_clients",
        target_type=SynonymTargetType.TABLE,
        target_id=table2.id
    )
    db_session.add(synonym)

    # 6. Golden SQL
    golden = GoldenSQL(
        id=uuid4(),
        datasource_id=ds.id,
        slug="golden_active_users",
        prompt_text="How many active users?",
        sql_query="SELECT COUNT(*) FROM t_users WHERE active=1"
    )
    db_session.add(golden)

    # 7. Context Rule
    rule = ColumnContextRule(
        id=uuid4(),
        column_id=col1.id,
        slug="rule_no_deleted_orders",
        rule_text="Ignore deleted orders (deleted_at IS NOT NULL)"
    )
    db_session.add(rule)

    # 8. Low Cardinality Value
    lcv = LowCardinalityValue(
        id=uuid4(),
        column_id=col2.id,
        slug="lcv_vip_user",
        value_raw="VIP",
        value_label="Very Important Person"
    )
    db_session.add(lcv)
    
    # 9. Edge
    edge = SchemaEdge(
        id=uuid4(),
        source_column_id=col2.id,
        target_column_id=col3.id,
        relationship_type=RelationshipType.ONE_TO_MANY,
        description="Order belongs to User"
    )
    db_session.add(edge)
    
    db_session.commit()
    
    return {
        "ds": ds,
        "table": table,
        "table2": table2,
        "col1": col1,
        "col2": col2,
        "col3": col3
    }

# =============================================================================
# TESTS
# =============================================================================

PREFIX = "/api/v1/discovery"

def test_search_datasources(client, discovery_seed):
    resp = client.post(f"{PREFIX}/datasources", json={"query": "test_datasource"})
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "limit" in data
    assert len(data["items"]) >= 1
    assert data["items"][0]["slug"] == "test_datasource_slug"

def test_search_tables(client, discovery_seed):
    resp = client.post(f"{PREFIX}/tables", json={
        "query": "Orders", 
        "datasource_slug": discovery_seed['ds'].slug
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert len(data["items"]) >= 1
    assert data["items"][0]["slug"] == "orders_table"

def test_search_columns(client, discovery_seed):
    # Test specific table filter
    resp = client.post(f"{PREFIX}/columns", json={
        "query": "Order ID", 
        "datasource_slug": discovery_seed['ds'].slug,
        "table_slug": "orders_table"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert len(data["items"]) >= 1
    assert data["items"][0]["slug"] == "order_id_col"
    
    # Test datasource filter (deep filter)
    resp2 = client.post(f"{PREFIX}/columns", json={
        "query": "User ID",
        "datasource_slug": discovery_seed['ds'].slug
    })
    # Should find user_id_col from users_table
    assert resp2.status_code == 200
    data2 = resp2.json()
    slugs = [x["slug"] for x in data2["items"]]
    assert "user_id_col" in slugs

def test_search_edges(client, discovery_seed):
    resp = client.post(f"{PREFIX}/edges", json={
        "query": "Order belongs",
        "datasource_slug": discovery_seed['ds'].slug
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert len(data["items"]) >= 1
    assert "orders_table.user_ref_col" in data["items"][0]["source"]

def test_search_edges_with_table(client, discovery_seed):
    # Test table filter
    resp = client.post(f"{PREFIX}/edges", json={
        "query": "",
        "datasource_slug": discovery_seed['ds'].slug,
        "table_slug": "users_table"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert len(data["items"]) >= 1
    # Check that users_table is involved (as target in our seed: orders -> users)
    edge = data["items"][0]
    assert "users_table" in edge['target'].split('.')[0]

def test_search_metrics(client, discovery_seed):
    # Test basic search
    resp = client.post(f"{PREFIX}/metrics", json={"query": "Total Orders"})
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert len(data["items"]) >= 1
    assert data["items"][0]["slug"] == "total_orders_metric"
    # Verify required_tables are resolved to slugs
    assert "required_tables" in data["items"][0]
    assert data["items"][0]["required_tables"] == ["orders_table"]
    
    # Test datasource filtering
    resp_filtered = client.post(f"{PREFIX}/metrics", json={
        "query": "Total Orders",
        "datasource_slug": discovery_seed['ds'].slug
    })
    assert resp_filtered.status_code == 200
    data_filtered = resp_filtered.json()
    assert "items" in data_filtered
    assert len(data_filtered["items"]) >= 1
    assert data_filtered["items"][0]["slug"] == "total_orders_metric"

def test_search_synonyms(client, discovery_seed):
    resp = client.post(f"{PREFIX}/synonyms", json={"query": "clients"})
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert len(data["items"]) >= 1
    assert data["items"][0]["term"] == "clients"

def test_search_golden_sql(client, discovery_seed):
    resp = client.post(f"{PREFIX}/golden_sql", json={
        "query": "active users",
        "datasource_slug": discovery_seed['ds'].slug
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert len(data["items"]) >= 1
    assert "active users" in data["items"][0]["prompt"]
    
    # Test list all (empty query)
    resp_all = client.post(f"{PREFIX}/golden_sql", json={"query": ""})
    assert resp_all.status_code == 200
    data_all = resp_all.json()
    assert len(data_all["items"]) >= 1

def test_search_context_rules(client, discovery_seed):
    # Test datasource level filtering
    resp = client.post(f"{PREFIX}/context_rules", json={
        "query": "deleted orders",
        "datasource_slug": discovery_seed['ds'].slug
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert len(data["items"]) >= 1
    assert data["items"][0]["slug"] == "rule_no_deleted_orders"

def test_search_low_cardinality_values(client, discovery_seed):
    # Test table level filtering
    resp = client.post(f"{PREFIX}/low_cardinality_values", json={
        "query": "Person",
        "datasource_slug": discovery_seed['ds'].slug,
        "table_slug": "orders_table"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert len(data["items"]) >= 1
    assert data["items"][0]["value_label"] == "Very Important Person"
    assert data["items"][0]["table_slug"] == "orders_table"

    # Test search by value_raw (Regression test for issue where raw value was not indexed)
    resp_raw = client.post(f"{PREFIX}/low_cardinality_values", json={
        "query": "VIP",
        "datasource_slug": discovery_seed['ds'].slug
    })
    assert resp_raw.status_code == 200
    data_raw = resp_raw.json()
    assert data_raw["items"][0]["value_raw"] == "VIP"

    # Test independent table_slug filter (Regression test for bug where table_slug was ignored if no datasource_slug)
    # Search for "VIP" restricted to orders table (should find it)
    resp_orders = client.post(f"{PREFIX}/low_cardinality_values", json={
        "query": "VIP",
        "table_slug": "orders_table"
    })
    assert resp_orders.status_code == 200
    assert len(resp_orders.json()["items"]) >= 1

    # Search for "VIP" restricted to unrelated table (should NOT find it)
    resp_other = client.post(f"{PREFIX}/low_cardinality_values", json={
        "query": "VIP",
        "table_slug": "products_table" # Assuming products_table exists from seed
    })
    assert resp_other.status_code == 200
    assert len(resp_other.json()["items"]) == 0
