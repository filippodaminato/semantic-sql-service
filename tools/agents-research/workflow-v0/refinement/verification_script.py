import sys
import os
import asyncio
from unittest.mock import MagicMock, AsyncMock

# Add project root to sys.path
sys.path.append(os.getcwd())

from refinement.nodes import pruner_worker_node, search_evaluator_node, _inject_note_into_column, planner_node
from refinement.schemas import QueryPlan, PruneTarget, SearchEvaluation, FetchTarget
from utils.context_formatter import AgentContextFormatter

# Mock Data
MOCK_DATASOURCE = {
    "name": "Sales DB",
    "slug": "sales_db",
    "tables": [
        {
            "physical_name": "orders",
            "slug": "sales_db.orders",
            "columns": [
                {"name": "id", "slug": "sales_db.orders.id", "data_type": "int"},
                {"name": "amount", "slug": "sales_db.orders.amount", "data_type": "float"}
            ]
        },
        {
            "physical_name": "users",
            "slug": "sales_db.users",
            "columns": []
        }
    ],
    "metrics": [
        {"name": "Total Revenue", "slug": "sales_db.metrics.total_revenue"}
    ]
}

def test_formatter():
    print("Testing Formatter...")
    md = AgentContextFormatter.datasource_to_markdown(MOCK_DATASOURCE)
    print(md)
    assert "**Slug**: `sales_db.orders`" in md
    assert "`sales_db.metrics.total_revenue`" in md
    print("Formatter OK ✅")

def test_pruner():
    print("Testing Pruner...")
    ds = MOCK_DATASOURCE.copy()
    # Need deepish copy for lists/dicts
    ds["tables"] = list(MOCK_DATASOURCE["tables"])
    ds["metrics"] = list(MOCK_DATASOURCE["metrics"])
    
    plan = QueryPlan(
        status_reasoning="Test",
        action_type="PRUNE",
        prune_targets=[
            PruneTarget(entity_type="table", entity_slug="sales_db.users"),
            PruneTarget(entity_type="metric", entity_slug="sales_db.metrics.total_revenue")
        ]
    )
    
    state = {
        "current_plan": plan,
        "working_datasource": ds
    }
    
    res = pruner_worker_node(state)
    new_ds = res["working_datasource"]
    
    table_slugs = [t["slug"] for t in new_ds["tables"]]
    metric_slugs = [m["slug"] for m in new_ds.get("metrics", [])]
    
    assert "sales_db.users" not in table_slugs
    assert "sales_db.metrics.total_revenue" not in metric_slugs
    assert "sales_db.orders" in table_slugs
    print("Pruner OK ✅")

async def test_evaluator():
    print("Testing Evaluator...")
    ds = MOCK_DATASOURCE.copy()
    
    # Mock LLM
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value.ainvoke = AsyncMock(return_value=SearchEvaluation(
        selected_indices=[0],
        reasoning="Relevant",
        formatted_note="Valid Region: Veneto"
    ))
    
    state = {
        "question": "Sales in Veneto?",
        "current_fetch_target": FetchTarget(entity_type="low_cardinality_value", search_text="Veneto", context_slug="sales_db.orders.id"), # Using random slug for test
        "pending_search_results": [{"value_raw": "Veneto", "value_label": "Region"}],
        "working_datasource": ds
    }
    
    res = await search_evaluator_node(state, mock_llm)
    new_ds = res["working_datasource"]
    
    # Check broad injection
    assert any("Veneto" in note for note in new_ds.get("enrichment_notes", []))
    
    # Check targeted injection logic (mocked slug was orders.id)
    # Re-fetch ds references because of copy
    target_col = new_ds["tables"][0]["columns"][0] # orders.id
    assert "Veneto" in target_col.get("context_note", "")
    print("Evaluator OK ✅")

async def main():
    test_formatter()
    test_pruner()
    await test_evaluator()

if __name__ == "__main__":
    asyncio.run(main())
