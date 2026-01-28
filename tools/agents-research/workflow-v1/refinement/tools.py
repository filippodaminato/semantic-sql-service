from typing import List, Dict, Any
import httpx


# NOTA IMPORTANTE NEL PAYLOAD METTERE SEMPRE datasource_slug: {current_datasource_slug}
# Inoltre alcune api hanno la possibilità di aggiungere filtri tipo table_slug: {table_slug} va messo in payload e detto all'LLM
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


# In a real implementation these would be defined in a shared schema or proper type hint
# We use kwargs to support flexible filters like table_slug, column_slug, etc.

async def search_tables(query: str, datasource_slug: str, **kwargs) -> List[dict]:
    # post /api/v1/discovery/tables
    payload = {"query": query, "datasource_slug": datasource_slug, "limit": 5, "min_ratio_to_best": 0.75}
    payload.update(kwargs)
    res = await _post("/tables", payload)
    if not res or "items" not in res: return []
    return res["items"]

async def search_columns(query: str, datasource_slug: str, **kwargs) -> List[dict]:
    # post /api/v1/discovery/columns
    payload = {"query": query, "datasource_slug": datasource_slug, "limit": 5, "min_ratio_to_best": 0.75}
    payload.update(kwargs)
    res = await _post("/columns", payload)
    if not res or "items" not in res: return []
    return res["items"]

async def search_metrics(query: str, datasource_slug: str, **kwargs) -> List[dict]:
    # post /api/v1/discovery/metrics
    payload = {"query": query, "datasource_slug": datasource_slug, "limit": 5, "min_ratio_to_best": 0.75}
    payload.update(kwargs)
    res = await _post("/metrics", payload)
    if not res or "items" not in res: return []
    return res["items"]

async def search_context_rules(query: str, datasource_slug: str, **kwargs) -> List[dict]:
    # post /api/v1/discovery/context_rules
    payload = {"query": query, "datasource_slug": datasource_slug, "limit": 5, "min_ratio_to_best": 0.75}
    payload.update(kwargs)
    res = await _post("/context_rules", payload)
    if not res or "items" not in res: return []
    return res["items"]

async def search_low_cardinality_values(query: str, datasource_slug: str, **kwargs) -> List[dict]:
    # post /api/v1/discovery/low_cardinality_values
    payload = {"query": query, "datasource_slug": datasource_slug, "limit": 5, "min_ratio_to_best": 0.75}
    payload.update(kwargs)
    res = await _post("/low_cardinality_values", payload)
    if not res or "items" not in res: return []
    return res["items"]

async def search_golden_sql(query: str, datasource_slug: str, **kwargs) -> List[dict]:
    # post /api/v1/discovery/golden_sql
    payload = {"query": query, "datasource_slug": datasource_slug, "limit": 5, "min_ratio_to_best": 0.75}
    payload.update(kwargs)
    res = await _post("/golden_sql", payload)
    if not res or "items" not in res: return []
    return res["items"]

async def search_graph_paths(source: str, target: str, datasource_slug: str, **kwargs) -> List[str]:
    """Finds valid SQL join paths between two tables using the graph-path endpoint."""
    print(f"🔗 [TOOL] Finding paths: {source} <-> {target} in {datasource_slug}")
    
    payload = {
        "source_table_slug": source,
        "target_table_slug": target,
        "datasource_slug": datasource_slug
    }
    payload.update(kwargs)
    
    try:
        res = await _post("/paths", payload)
        if not res or "paths" not in res: 
             return [f"No join paths found between {source} and {target}."]
        
        return res["paths"]
    except Exception as e:
        print(f"Error fetching join paths: {e}")
        return [f"Error fetching paths: {str(e)}"]

async def search_values(query: str, datasource_slug: str, **kwargs) -> List[str]:
    """
    Searches for specific values (Low Cardinality) within the datasource.
    """
    print(f"🔍 [TOOL] Searching values for '{query}' in {datasource_slug}")
    
    # 1. Search in low_cardinality_values endpoint
    # Pass kwargs to filter by column_slug if provided in payload
    results = await search_low_cardinality_values(query, datasource_slug, **kwargs)
    
    # Clean up results for LLM
    return [f"Value: '{r['matched_value']}' (Column: {r.get('column_slug')})" for r in results]

async def search_metadata(query: str, datasource_slug: str, **kwargs) -> List[str]:
    """
    Dispatcher for general metadata search based on query.
    """
    print(f"🔍 [TOOL] Searching metadata for '{query}' in {datasource_slug}")
    
    # Pass kwargs (filters) to all sub-searches
    t_res = await search_tables(query, datasource_slug, **kwargs)
    c_res = await search_columns(query, datasource_slug, **kwargs)
    m_res = await search_metrics(query, datasource_slug, **kwargs)
    
    combined = []
    
    for r in t_res:
        # Use physical_name if available, else slug
        name = r.get('physical_name', r['slug'])
        combined.append(f"[TABLE] {name} (Slug: {r['slug']}) - {r.get('description', '')}")
        
    for r in c_res:
        # Use physical name (name field) if available
        col_name = r.get('name', r['slug'])
        combined.append(f"[COLUMN] {col_name} (Table: {r.get('table_slug')}) - {r.get('description', '')}")
        
    for r in m_res:
        # Metrics use 'name' as semantic name usually, but that's fine for metrics
        combined.append(f"[METRIC] {r['name']} (Slug: {r['slug']}) - {r.get('description', '')}")
        
    return combined[:15]  # Return top 15 mixed results
