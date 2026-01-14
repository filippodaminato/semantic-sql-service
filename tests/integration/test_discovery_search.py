import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.main import app
from src.db.models import Datasource, TableNode, SemanticMetric, SQLEngineType
from src.core.database import get_db

client = TestClient(app)

@pytest.fixture
def db_session():
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()

def test_discovery_empty_search_pagination(db_session: Session):
    """
    Test that empty search returns all items and pagination count is correct.
    """
    # Setup: Create a datasource and 12 tables
    ds = Datasource(
        name=f"Test DS {uuid4()}",
        slug=f"test-ds-{uuid4()}", 
        engine=SQLEngineType.POSTGRES,
        description="Test Datasource"
    )
    db_session.add(ds)
    db_session.flush()

    for i in range(12):
        table = TableNode(
            datasource_id=ds.id,
            physical_name=f"t_test_{i}",
            slug=f"t-test-{i}-{uuid4()}",
            semantic_name=f"Test Table {i}",
            description=f"Description for table {i}"
        )
        db_session.add(table)
    db_session.commit()

    # 1. Test Empty Search ("List All")
    response = client.post(
        "/api/v1/discovery/tables",
        json={"query": "", "datasource_slug": ds.slug, "page": 1, "limit": 5}
    )
    assert response.status_code == 200
    data = response.json()
    
    # Verify we get items
    assert len(data["items"]) == 5
    # Verify Total is 12 (not just the page limit or 0)
    assert data["total"] == 12 
    assert data["page"] == 1
    assert data["limit"] == 5
    assert data["has_next"] is True
    assert data["total_pages"] == 3

    # 2. Test Page 3 (Last Page)
    response = client.post(
        "/api/v1/discovery/tables",
        json={"query": "", "datasource_slug": ds.slug, "page": 3, "limit": 5}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2 # 12 total, 5 per page -> 5, 5, 2
    assert data["has_next"] is False

def test_discovery_metrics_slug_resolution(db_session: Session):
    """
    Test that metrics search returns table slugs in required_tables.
    """
    # Setup: DS, Table, Metric
    ds = Datasource(
        name=f"Metric DS {uuid4()}",
        slug=f"metric-ds-{uuid4()}",
        engine=SQLEngineType.POSTGRES
    )
    db_session.add(ds)
    db_session.flush()

    table = TableNode(
        datasource_id=ds.id,
        physical_name="t_revenue",
        slug=f"t-revenue-{uuid4()}",
        semantic_name="Revenue Table",
        description="Revenue data"
    )
    db_session.add(table)
    db_session.flush()

    # Create metric depending on this table (store ID as string in JSON list)
    metric = SemanticMetric(
        datasource_id=ds.id,
        name=f"Total Revenue {uuid4()}",
        slug=f"total-revenue-{uuid4()}",
        description="Sum of revenue",
        calculation_sql="SELECT sum(amount) FROM t_revenue",
        required_tables=[str(table.id)] # Stored as ID
    )
    db_session.add(metric)
    db_session.commit()

    # Search for this metric
    response = client.post(
        "/api/v1/discovery/metrics",
        json={"query": "Revenue", "datasource_slug": ds.slug}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) >= 1
    
    found_metric = None
    for item in data["items"]:
        if item["id"] == str(metric.id):
            found_metric = item
            break
    
    assert found_metric is not None
    # CRITICAL CHECK: required_tables should contain the SLUG, not the ID
    assert found_metric["required_tables"] == [table.slug]
