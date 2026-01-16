from langchain_core.messages import SystemMessage
from retrieval.state import RetrievalState
from retrieval.tools import (
    search_datasources,
    search_tables,
    search_columns,
    search_edges,
    search_metrics,
    search_synonyms,
    search_context_rules,
    search_low_cardinality_values,
    search_golden_sql,
)

from prompts import create_search_text_prompt

async def create_search_text_node(state: RetrievalState):
    prompt = create_search_text_prompt
    
    pass

# --- Parallel Nodes ---

async def datasources_scout_node(state: RetrievalState):
    pass

async def golden_sql_scout_node(state: RetrievalState):
    pass

async def metrics_scout_node(state: RetrievalState):
    pass

async def tables_scout_node(state: RetrievalState):
    pass

async def columns_scout_node(state: RetrievalState):
    pass

async def edges_scout_node(state: RetrievalState):
    pass

# deprecated
async def synonyms_scout_node(state: RetrievalState):
    pass

async def context_rules_scout_node(state: RetrievalState):
    pass

async def low_cardinality_values_scout_node(state: RetrievalState):
    pass

# --- Consolidator Node (The Brain) ---

def consolidator_node(state: RetrievalState):
    print("   [Consolidator] Merging & Reranking contexts...")
    
    # 1. Deduplicazione (set)
    unique_tables = sorted(list(set(state["found_tables"])))
    unique_metrics = sorted(list(set(state["found_metrics"])))
    golden_sqls = state["found_golden_sqls"]
    
    # 2. Costruzione del Prompt Context
    context_parts = []
    
    if unique_tables:
        context_parts.append("### Database Schema:\n" + "\n".join(unique_tables))
        
    if unique_metrics:
        context_parts.append("### Business Definitions / Metrics:\n" + "\n".join(unique_metrics))
        
    if golden_sqls:
        examples_str = "\n".join([f"- Q: {g['question']}\n  SQL: {g['sql']}" for g in golden_sqls])
        context_parts.append("### Verified Examples (Golden SQL):\n" + examples_str)
        
    final_context_str = "\n\n".join(context_parts)
    
    return {"final_context": final_context_str}