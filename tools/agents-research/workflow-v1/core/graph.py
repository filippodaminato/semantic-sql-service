from langgraph.graph import StateGraph, END
from functools import partial
from core.state import AgentState
from retrieval.graph import build_retrieval_subgraph
from refinement.graph import build_refinement_subgraph

async def call_refinement_bridge(state: AgentState, subgraph):
    """
    Bridge function that maps Global State to Refinement Subgraph State
    and maps the output back to Global State.
    """
    # 1. Map Global -> Local
    # We take the raw datasource found by Retrieval and pass it as 'working_datasource' to Refinement
    input_state = {
        "question": state["question"],
        "working_datasource": state["raw_datasource"],
        "iterations": 0,
        "local_logs": [],
        "pending_search_results": []
    }
    
    # 2. Invoke Subgraph
    # The subgraph is a compiled Runnable
    output = await subgraph.ainvoke(input_state)
    
    # 3. Map Local -> Global
    return {
        "refined_datasource": output["working_datasource"],
        "logical_query_plan": output["final_logical_plan"],
        "global_logs": output["local_logs"]
    }

def build_main_graph(llm):
    """
    Builds the main agent graph composed of subgraphs.
    """
    workflow = StateGraph(AgentState)
    
    # --- SUBGRAPHS ---
    retrieval_graph = build_retrieval_subgraph(llm)
    refinement_graph = build_refinement_subgraph(llm)
    
    # --- NODES ---
    # Retrieval matches AgentState keys partially, so we can use it directly?
    # Actually, Retrieval expects 'search_plan' etc internally.
    # But since it's a StateGraph(RetrievalState), LangGraph handles extra keys by ignoring them 
    # IF the state schema allows it. AgentState is a TypedDict showing only global keys.
    # However, 'retrieval_graph' will accept AgentState input if keys match.
    # Safe approach: usage of simple nodes.
    
    workflow.add_node("retrieval", retrieval_graph)
    
    # Refinement needs a bridge because input keys differ (raw_datasource -> working_datasource)
    workflow.add_node("refinement", partial(call_refinement_bridge, subgraph=refinement_graph))
    
    # --- EDGES ---
    workflow.set_entry_point("retrieval")
    workflow.add_edge("retrieval", "refinement")
    workflow.add_edge("refinement", END)
    
    return workflow.compile()
