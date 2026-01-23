import httpx
import logging
from typing import List, Dict, Any
from retrieval.schemas import SearchPlan

logger = logging.getLogger("agent_logger")

DISCOVERY_API_URL = "http://localhost:8000/api/v1/discovery/resolve-context"

async def perform_discovery(plan: SearchPlan) -> Dict[str, Any]:
    """
    Executes the discovery search by calling the resolve-context endpoint.
    Maps the Planner's output to the API payload structure.
    """
    
    # 1. Construct Payload
    # Payload format: List[ContextSearchEntity] -> [{"entity": "...", "search_text": "..."}]
    payload = []
    
    # Map fields to entity types
    # Assumptions on entity names based on typical discovery services
    
    for term in plan.search_text_datasources:
        payload.append({"entity": "datasources", "search_text": term, "min_ratio_to_best": 0.75})
        
    for term in plan.search_text_tables:
        payload.append({"entity": "tables", "search_text": term, "min_ratio_to_best": 0.75})
        
    for term in plan.search_text_columns:
        payload.append({"entity": "columns", "search_text": term, "min_ratio_to_best": 0.75})
        
    for term in plan.search_text_metrics:
        payload.append({"entity": "metrics", "search_text": term, "min_ratio_to_best": 0.75})
        
    for term in plan.search_text_edges:
        payload.append({"entity": "edges", "search_text": term, "min_ratio_to_best": 0.75})
        
    for term in plan.search_text_context_rules:
        # Assuming entity is context_rule
        payload.append({"entity": "context_rules", "search_text": term, "min_ratio_to_best": 0.75})

    # Synonyms, Low Card values, Golden SQL usually function as filters or specific entity searches
    # Mapping them to generic or specific entities if supported.
    # The API expects 'low_cardinality_values' and 'golden_sql'
    
    for term in plan.search_text_low_cardinality_values:
        payload.append({"entity": "low_cardinality_values", "search_text": term, "min_ratio_to_best": 0.75})
        
    for term in plan.search_text_golden_sqls:
        payload.append({"entity": "golden_sql", "search_text": term, "min_ratio_to_best": 0.75})

    if not payload:
        logger.warning("Search Plan is empty. No API call made.")
        return {"graph": []}

    # 2. Execute Request
    logger.info(f"Using Discovery API: {DISCOVERY_API_URL} with {len(payload)} search items used.")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(DISCOVERY_API_URL, json=payload, timeout=30.0)
            response.raise_for_status()
            data = response.json()
            return data
            
    except httpx.HTTPStatusError as e:
        logger.error(f"API Error {e.response.status_code}: {e.response.text}")
        raise
    except Exception as e:
        logger.error(f"Network Error during Discovery: {str(e)}")
        raise