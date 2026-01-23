import os
import sys
import uuid
import asyncio
import json
import datetime
from typing import TypedDict, Optional, Dict, Any
from functools import partial

from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END

# Ensure environment is loaded
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
sys.path.append(project_root)

try:
    from dotenv import load_dotenv
    dotenv_path = os.path.join(project_root, ".env")
    load_dotenv(dotenv_path)
except ImportError:
    pass

# Imports
from langchain_openai import ChatOpenAI
from state import AgentState
from retrieval.nodes import plan_search_node, retrieve_and_select_node
from retrieval.service import RetrievalService
from refinement.nodes import (
    planner_node,
    pruner_worker_node,
    fetch_worker_node,
    search_evaluator_node,
    router_logic
)

# --- Dependencies ---
llm = ChatOpenAI(model="gpt-4o", temperature=0)
retrieval_service = RetrievalService()

# --- Bridge Node ---
def initialize_refinement_state(state):
    """
    Bridge node: Prepares the state for the Refinement Loop.
    """
    selected = state["selected_datasource"]
    
    if hasattr(selected, "model_dump"):
        working_ds = selected.model_dump()
    elif isinstance(selected, dict):
        working_ds = selected.copy()
    else:
        working_ds = dict(selected)

    return {
        "working_datasource": working_ds,
        "iterations": 0,
        "pending_search_results": [],
        "current_plan": None
    }

# --- Graph Construction (Monolithic) ---
workflow = StateGraph(AgentState)

# Retrieval Nodes
workflow.add_node("retrival_planner", partial(plan_search_node, llm=llm))
workflow.add_node("retriever", partial(retrieve_and_select_node, llm=llm, retrieval_service=retrieval_service))

# Refinement Nodes
workflow.add_node("initialize_refinement", initialize_refinement_state)
workflow.add_node("refinement_planner", partial(planner_node, llm=llm))
workflow.add_node("pruner_worker", pruner_worker_node)
workflow.add_node("fetch_worker", fetch_worker_node)
workflow.add_node("search_evaluator", partial(search_evaluator_node, llm=llm))

# Wiring - Retrieval
workflow.set_entry_point("retrival_planner")
workflow.add_edge("retrival_planner", "retriever")
workflow.add_edge("retriever", "initialize_refinement")

# Wiring - Refinement
workflow.add_edge("initialize_refinement", "refinement_planner")

workflow.add_conditional_edges(
    "refinement_planner",
    router_logic,
    {
        "pruner_worker": "pruner_worker",
        "fetch_worker": "fetch_worker",
        "generate_sql": END
    }
)

workflow.add_edge("pruner_worker", "refinement_planner")
workflow.add_edge("fetch_worker", "search_evaluator")
workflow.add_edge("search_evaluator", "refinement_planner")

app = workflow.compile()

# --- Main Interaction Loop ---
async def main():
    print("Retrieval Agent Chat (Monolithic Revert)")
    print("----------------------------------------")
    
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    
    # Simple logging (to file or console)
    logs_dir = os.path.join(current_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    while True:
        try:
            user_input = input("\nUser: ")
            if user_input.lower() in ["quit", "exit", "q"]:
                break
            
            inputs = {"question": user_input, "logs": []} # Init logs empty
            
            final_output = None
            
            print("Processing...")
            async for event in app.astream(inputs, config=config):
                for key, value in event.items():
                    print(f"[{key}] passed.")
                    
                    if "logs" in value and value["logs"]:
                         # Just print the last log's step
                         last_log = value["logs"][-1]
                         print(f"Log Step: {last_log.get('step')}")
                    
                    if "working_datasource" in value:
                        final_output = value["working_datasource"]

            if final_output:
                print("\nFinal Context Ready.")
                # Save trace
                ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                with open(os.path.join(logs_dir, f"trace_{ts}.json"), "w") as f:
                     # We can't easily access the full state 'logs' from 'event' unless we accumulate or get checkingpoint
                     # But 'value' contains the update. 
                     # For now, simplistic finish.
                     pass 

        except KeyboardInterrupt:
            break
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())