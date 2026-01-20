from typing import List, Dict, Any
import httpx
import asyncio

BASE_URL = "http://localhost:8000/api/v1/discovery"

async def _post(endpoint: str, payload: Dict[str, Any]) -> Any:
    async with httpx.AsyncClient() as client:
        try:
            # Clean payload
            clean_payload = {k: v for k, v in payload.items() if v is not None}
            response = await client.post(f"{BASE_URL}{endpoint}", json=clean_payload, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error calling {endpoint}: {e}")
            return {}

async def search_datasources(query: str) -> List[dict]:
    # post /api/v1/discovery/datasources
    res = await _post("/datasources", {"query": query, "limit": 5})
    if not res or "items" not in res: return []
    return res["items"]

async def search_tables(query: str) -> List[dict]:
    # post /api/v1/discovery/tables
    res = await _post("/tables", {"query": query, "limit": 5})
    if not res or "items" not in res: return []
    return res["items"]

async def search_columns(query: str) -> List[dict]:
    # post /api/v1/discovery/columns
    res = await _post("/columns", {"query": query, "limit": 5})
    if not res or "items" not in res: return []
    return res["items"]

async def search_edges(query: str) -> List[dict]:
    # post /api/v1/discovery/edges
    res = await _post("/edges", {"query": query, "limit": 5})
    if not res or "items" not in res: return []
    return res["items"]

async def search_metrics(query: str) -> List[dict]:
    # post /api/v1/discovery/metrics
    res = await _post("/metrics", {"query": query, "limit": 5})
    if not res or "items" not in res: return []
    return res["items"]

async def search_synonyms(query: str) -> List[dict]:
    # post /api/v1/discovery/synonyms
    res = await _post("/synonyms", {"query": query, "limit": 5})
    if not res or "items" not in res: return []
    return res["items"]

async def search_context_rules(query: str) -> List[dict]:
    # post /api/v1/discovery/context_rules
    res = await _post("/context_rules", {"query": query, "limit": 5})
    if not res or "items" not in res: return []
    return res["items"]

async def search_low_cardinality_values(query: str) -> List[dict]:
    # post /api/v1/discovery/low_cardinality_values
    res = await _post("/low_cardinality_values", {"query": query, "limit": 5})
    if not res or "items" not in res: return []
    return res["items"]

async def search_golden_sql(query: str) -> List[dict]:
    # post /api/v1/discovery/golden_sql
    res = await _post("/golden_sql", {"query": query, "limit": 5})
    if not res or "items" not in res: return []
    return res["items"]

