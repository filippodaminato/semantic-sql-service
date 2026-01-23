from langgraph.graph import StateGraph, END
from core.state import AgentState
from retrieval.graph import build_retrieval_subgraph

def build_main_graph(llm):
    """
    Builds the main agent graph composed of subgraphs.
    """
    workflow = StateGraph(AgentState)
    
    # Subgraphs
    retrieval_graph = build_retrieval_subgraph(llm)
    
    # Add Nodes
    workflow.add_node("retrieval", retrieval_graph)
    
    # Edges
    workflow.set_entry_point("retrieval")
    workflow.add_edge("retrieval", END)
    
    return workflow.compile()
