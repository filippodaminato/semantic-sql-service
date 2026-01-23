import pytest
from uuid import uuid4
from src.db.models import (
    Datasource, TableNode, ColumnNode, SchemaEdge, SemanticMetric, 
    SemanticSynonym, ColumnContextRule, LowCardinalityValue, GoldenSQL,
    SQLEngineType, RelationshipType, SynonymTargetType
)
from src.schemas.discovery import ContextSearchEntity

PREFIX = "/api/v1/discovery"

@pytest.fixture
def mcp_seed_full(db_session):
    """Seed comprehensive data for MCP tests."""
    # 1. Datasource
    ds = Datasource(
        id=uuid4(),
        slug="mcp_ds_full",
        name="MCP Full DS",
        engine=SQLEngineType.POSTGRES,
        description="Comprehensive DS"
    )
    db_session.add(ds)
    
    # 2. Table
    table = TableNode(
        id=uuid4(),
        datasource_id=ds.id,
        physical_name="t_orders",
        slug="orders_table",
        semantic_name="Orders",
        description="Orders table"
    )
    db_session.add(table)
    db_session.flush()

    # 3. Column with Rule and LCV
    col = ColumnNode(
        id=uuid4(),
        table_id=table.id,
        name="status",
        slug="status_col",
        semantic_name="Order Status",
        data_type="VARCHAR",
        description="Current status"
    )
    db_session.add(col)
    db_session.flush()

    rule = ColumnContextRule(
        id=uuid4(),
        column_id=col.id,
        slug="rule_status_validation",
        rule_text="Status cannot go back to Pending"
    )
    db_session.add(rule)

    lcv = LowCardinalityValue(
        id=uuid4(),
        column_id=col.id,
        slug="val_shipped",
        value_raw="SHIPPED",
        value_label="Order Shipped"
    )
    db_session.add(lcv)
    
    # 4. Metric
    metric = SemanticMetric(
        id=uuid4(),
        datasource_id=ds.id,
        name="Total Revenue",
        slug="total_revenue",
        description="Sum of all orders",
        calculation_sql="SELECT SUM(amount) FROM t_orders"
    )
    db_session.add(metric)

    # 5. Golden SQL
    gsql = GoldenSQL(
        id=uuid4(),
        datasource_id=ds.id,
        slug="gsql_revenue",
        prompt_text="What is the total revenue?",
        sql_query="SELECT SUM(amount) FROM t_orders",
        complexity_score=1,
        verified=True
    )
    db_session.add(gsql)

    # 6. Edge
    edge = SchemaEdge(
        id=uuid4(),
        source_column_id=col.id, # Linking status to itself just for edge demo
        target_column_id=col.id,
        relationship_type=RelationshipType.ONE_TO_ONE,
        description="Self link demo"
    )
    db_session.add(edge)
    
    db_session.commit()
    
    return {
        "ds": ds,
        "table": table,
        "col": col,
        "rule": rule,
        "metric": metric,
        "gsql": gsql,
        "edge": edge
    }

def test_mcp_resolve_context_full(client, mcp_seed_full):
    # Request everything to ensure full graph resolution
    payload = [
        {
            "entity": "tables",
            "search_text": "Orders"
        },
        {
            "entity": "metrics",
            "search_text": "Revenue"
        },
        {
            "entity": "golden_sql",
            "search_text": "revenue"
        },
        {
            "entity": "edges",
            "search_text": "Self link"
        }
    ]
    
    resp = client.post(f"{PREFIX}/mcp/resolve-context", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    formatted = data["res"]
    
    # Core Structure
    assert "## Datasource: `MCP Full DS`" in formatted
    assert "### Table: `t_orders`" in formatted
    
    # Columns & Values
    assert "#### Founded Columns:" in formatted
    assert "- `status` (VARCHAR)" in formatted
    assert "> VALUES: SHIPPED" in formatted
    
    # Rules
    assert "> RULE: Status cannot go back to Pending" in formatted
    
    # Metrics
    assert "### Semantic Metrics" in formatted
    assert "- **Total Revenue** (`total_revenue`)" in formatted
    assert "_SQL_: `SELECT SUM(amount) FROM t_orders`" in formatted
    
    # Golden SQL
    assert "### Golden SQL Examples" in formatted
    assert "- **Prompt**: \"What is the total revenue?\"" in formatted
    
    # Relationships
    # Note: Edges are usually fetched if tables are in context.
    # Our self-link edge logic in bulk_fetch checks if target table is in known_table_ids.
    # Since source=target=table, it should be included.
    assert "### Relationships" in formatted
    assert "->" in formatted # Check for the arrow
