from langgraph.graph import StateGraph, END
from retrieval.state import RetrievalState
from retrieval.nodes import plan_search_node, execute_search_node, select_datasource_node

from functools import partial

def build_retrieval_subgraph(llm):
    """Builds and compiles the retrieval subgraph."""
    workflow = StateGraph(RetrievalState)
    
    # Add Nodes (Dependency Injection for LLM)
    workflow.add_node("planner", partial(plan_search_node, llm=llm))
    workflow.add_node("executor", execute_search_node)
    workflow.add_node("selector", partial(select_datasource_node, llm=llm))
    
    # Define Edges (Linear Flow)
    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "executor")
    workflow.add_edge("executor", "selector")
    workflow.add_edge("selector", END)
    
    return workflow.compile()