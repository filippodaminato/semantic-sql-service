from langgraph.graph import StateGraph, END
from generation.state import GenerationState
from generation.nodes import sql_generator_node, sql_validator_node

def route_validation(state):
    if state["is_valid"]:
        return END
    
    if state["attempt_count"] > 3:
        # Give up after 3 tries to avoid infinite loops
        return END 
    
    return "generator" # Retry

def build_generation_subgraph(llm):
    workflow = StateGraph(GenerationState)
    
    async def generator_wrapper(state):
        return await sql_generator_node(state, llm)

    async def validator_wrapper(state):
        return await sql_validator_node(state, llm)

    workflow.add_node("generator", generator_wrapper)
    workflow.add_node("validator", validator_wrapper)
    
    workflow.set_entry_point("generator")
    
    workflow.add_edge("generator", "validator")
    
    workflow.add_conditional_edges(
        "validator",
        route_validation,
        {
            "generator": "generator", # Loop back to fix
            END: END
        }
    )
    
    return workflow.compile()