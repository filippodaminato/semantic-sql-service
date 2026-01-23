from langgraph.graph import StateGraph, END
from refinement.state import RefinementState
from refinement.nodes import (
    planner_node, 
    pruner_worker_node, 
    fetch_worker_node, 
    evaluator_node,
    generate_blueprint_node # Nuovo nodo
)

from functools import partial

def route_planner(state):
    plan = state["current_plan"]
    if state["iterations"] > 6:
        return "finalizer" # Force exit to finalizer
        
    if plan.action_type == "PRUNE":
        return "pruner"
    elif plan.action_type == "FETCH":
        return "fetcher"
    elif plan.action_type == "READY":
        return "finalizer" # CRITICAL CHANGE: Goes to finalizer, not END
    
    return "finalizer"

def build_refinement_subgraph(llm):
    workflow = StateGraph(RefinementState)
    
    workflow.add_node("planner", partial(planner_node, llm=llm))
    workflow.add_node("pruner", pruner_worker_node)
    workflow.add_node("fetcher", fetch_worker_node)
    workflow.add_node("evaluator", partial(evaluator_node, llm=llm))
    
    # New node
    workflow.add_node("finalizer", partial(generate_blueprint_node, llm=llm))
    
    workflow.set_entry_point("planner")
    
    workflow.add_conditional_edges("planner", route_planner, {
        "pruner": "pruner",
        "fetcher": "fetcher",
        "finalizer": "finalizer"
    })
    
    workflow.add_edge("pruner", "planner")
    workflow.add_edge("fetcher", "evaluator")
    workflow.add_edge("evaluator", "planner")
    
    # The finalizer is the last stop
    workflow.add_edge("finalizer", END)
    
    return workflow.compile()