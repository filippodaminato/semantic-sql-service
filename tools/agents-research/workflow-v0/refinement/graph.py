from functools import partial
from langgraph.graph import StateGraph, END
from state import AgentState
from refinement.nodes import (
    planner_node,
    pruner_worker_node,
    fetch_worker_node,
    search_evaluator_node,
    router_logic
)

def create_refinement_graph(llm):
    """
    Creates and compiles the StateGraph for the Cyclic Refinement Loop.
    
    Args:
        llm: A LangChain compatible LLM object (must support structured output).
        
    Returns:
        CompiledStateGraph
    """
    workflow = StateGraph(AgentState)

    # --- 1. Add Nodes ---
    
    # Planner: Decides next move (Prune, Fetch, or Ready)
    # Allows passing 'llm' via partial
    workflow.add_node("planner", partial(planner_node, llm=llm))
    
    # Pruner Worker: Removes items from datasource
    # Sync node
    workflow.add_node("pruner_worker", pruner_worker_node)
    
    # Fetch Worker: Executes searches
    # Async node
    workflow.add_node("fetch_worker", fetch_worker_node)
    
    # Search Evaluator: Filters and enriches search results
    # Needs LLM
    workflow.add_node("search_evaluator", partial(search_evaluator_node, llm=llm))

    # --- 2. Add Edges ---
    
    # Start at Planner
    workflow.set_entry_point("planner")

    # Conditional Logic from Planner
    # Based on 'action_type' in the QueryPlan
    workflow.add_conditional_edges(
        "planner",
        router_logic,
        {
            "pruner_worker": "pruner_worker",
            "fetch_worker": "fetch_worker",
            "generate_sql": END  # Exit the Refinement Loop
        }
    )

    # Loop back logic
    workflow.add_edge("pruner_worker", "planner")           # After pruning, replan
    workflow.add_edge("fetch_worker", "search_evaluator")   # Fetch -> Evaluate
    workflow.add_edge("search_evaluator", "planner")        # After evaluating/enriching, replan

    return workflow.compile()
