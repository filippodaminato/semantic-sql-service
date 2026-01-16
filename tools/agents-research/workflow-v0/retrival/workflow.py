from langgraph.graph import StateGraph, END
from retrieval.state import RetrievalState
from retrieval.nodes import (
    datasources_scout_node,
    golden_sql_scout_node,
    metrics_scout_node,
    tables_scout_node,
    columns_scout_node,
    edges_scout_node,
    synonyms_scout_node,
    context_rules_scout_node,
    low_cardinality_values_scout_node,
    consolidator_node
)

def build_retrieval_subgraph():
    workflow = StateGraph(RetrievalState)
    
    workflow.add_node("datasources_scout", datasources_scout_node)
    workflow.add_node("golden_sql_scout", golden_sql_scout_node)
    workflow.add_node("metrics_scout", metrics_scout_node)
    workflow.add_node("tables_scout", tables_scout_node)
    workflow.add_node("columns_scout", columns_scout_node)
    workflow.add_node("edges_scout", edges_scout_node)
    workflow.add_node("synonyms_scout", synonyms_scout_node)
    workflow.add_node("context_rules_scout", context_rules_scout_node)
    workflow.add_node("low_cardinality_values_scout", low_cardinality_values_scout_node)
    workflow.add_node("consolidator", consolidator_node)
    
    workflow.set_entry_point([
        "datasources_scout", 
        "golden_sql_scout", 
        "metrics_scout", 
        "tables_scout", 
        "columns_scout", 
        "edges_scout", 
        "synonyms_scout", 
        "context_rules_scout", 
        "low_cardinality_values_scout"
    ])
    
    workflow.add_edge("datasources_scout", "consolidator")
    workflow.add_edge("golden_sql_scout", "consolidator")
    workflow.add_edge("metrics_scout", "consolidator")
    workflow.add_edge("tables_scout", "consolidator")
    workflow.add_edge("columns_scout", "consolidator")
    workflow.add_edge("edges_scout", "consolidator")
    workflow.add_edge("synonyms_scout", "consolidator")
    workflow.add_edge("context_rules_scout", "consolidator")
    workflow.add_edge("low_cardinality_values_scout", "consolidator")
    
    workflow.add_edge("consolidator", END)
    
    return workflow.compile()