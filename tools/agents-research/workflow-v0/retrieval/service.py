import asyncio
from typing import List, Dict, Any, Optional
from retrieval.tools import (
    search_datasources,
    search_tables,
    search_columns,
    search_metrics,
    search_synonyms,
    search_context_rules,
    search_low_cardinality_values,
    search_golden_sql,
)

class RetrievalService:
    """
    Service to execute search plans against the Discovery API / Tools.
    """
    async def execute_hierarchical_search(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the search plan in parallel.
        Plan structure expected:
        {
            "search_text_datasources": [...],
            "search_text_tables": [...],
            ...
        }
        """
        tasks = []
        
        # Datasources
        for q in plan.get("search_text_datasources", []):
            tasks.append(search_datasources(q))
            
        # Tables
        for q in plan.get("search_text_tables", []):
            tasks.append(search_tables(q))
            
        # Columns
        for q in plan.get("search_text_columns", []):
            tasks.append(search_columns(q))

        # Metrics
        for q in plan.get("search_text_metrics", []):
            tasks.append(search_metrics(q))

        # Context Rules (Restricted/Special)
        for q in plan.get("search_text_context_rules", []):
            tasks.append(search_context_rules(q))
            
        # Execute all
        results_flat = await asyncio.gather(*tasks)
        
        # Flatten results (simplification)
        # Ideally we structure them by type
        combined_results = []
        for r in results_flat:
            if isinstance(r, list):
                combined_results.extend(r)
            else:
                combined_results.append(r)
                
        return {
            "results": combined_results,
            "raw_count": len(combined_results)
        }
