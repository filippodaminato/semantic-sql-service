from langgraph.graph import StateGraph, END
from retrieval.states import RetrievalState
from retrieval.nodes import (
    create_search_texts_node,
    execute_search_node,
    consolidator_node
)

def build_retrieval_subgraph():
    workflow = StateGraph(RetrievalState)
    
    workflow.add_node("create_search_texts", create_search_texts_node)
    workflow.add_node("execute_search", execute_search_node)
    workflow.add_node("consolidator", consolidator_node)
    
    workflow.set_entry_point("create_search_texts")
    
    workflow.add_edge("create_search_texts", "execute_search")
    workflow.add_edge("execute_search", "consolidator")
    
    workflow.add_edge("consolidator", END)
    
    return workflow.compile()