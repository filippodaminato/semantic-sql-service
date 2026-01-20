import os
import sys
import uuid
from typing import TypedDict
# Ensure environment is loaded BEFORE other imports that might use it
try:
    from dotenv import load_dotenv
    # Load from project root
    dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), ".env")
    load_dotenv(dotenv_path)
except ImportError:
    pass

from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from retrieval.workflow import build_retrieval_subgraph

# --- Main Agent State ---
class AgentState(TypedDict):
    question: str
    final_sql: str
    context_data: str # Output del retrieval subgraph

# --- Main Nodes ---
async def call_retrieval_subgraph(state: AgentState):
    print(f"--- 1. START RETRIEVAL for: {state['question']} ---")
    retrieval_app = build_retrieval_subgraph()
    inputs = {"user_prompt": state["question"]}
    
    final_context = []
    
    # Stream the retrieval subgraph to see steps
    async for event in retrieval_app.astream(inputs):
        for key, value in event.items():
            print(f"\n  [Retrieval Step - {key}]:")
            # Print full state update content as requested
            print(json.dumps(value, indent=2, default=str))
            
            # If it's the consolidator, capturing the result
            if "final_context" in value:
                final_context = value["final_context"]

    return {"context_data": final_context}


# --- Main Workflow Construction ---
workflow = StateGraph(AgentState)

workflow.add_node("retrieval_process", call_retrieval_subgraph)

workflow.set_entry_point("retrieval_process")
workflow.add_edge("retrieval_process", END)

checkpointer = MemorySaver()
app = workflow.compile(checkpointer=checkpointer)

import asyncio
import json

# --- Execution Example ---
async def main():
    print("Retrieval Agent Chat (workflow-v0)")
    print("----------------------------------")
    
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    
    while True:
        try:
            user_input = input("\nUser: ")
            if user_input.lower() in ["quit", "exit", "q"]:
                break
            
            inputs = {"question": user_input}
            
            final_output = None
            
            async for event in app.astream(inputs, config=config):
                 for key, value in event.items():
                    print(f"[{key}]: processed.")
                    if "context_data" in value:
                        final_output = value["context_data"]
            
            if final_output:
                print(f"\n[Result]: Saving {len(final_output)} items to retrieval_output.json")
                with open("retrieval_output.json", "w") as f:
                    json.dump(final_output, f, indent=2, default=str)
                print(json.dumps(final_output, indent=2, default=str))

        except KeyboardInterrupt:
            break

        except KeyboardInterrupt:
            break
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())