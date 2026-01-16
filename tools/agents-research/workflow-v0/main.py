from typing import TypedDict
from langgraph.graph import StateGraph, END
from retrieval.workflow import build_retrieval_subgraph

# --- Main Agent State ---
class AgentState(TypedDict):
    question: str
    final_sql: str
    context_data: str # Output del retrieval subgraph

# --- Main Nodes ---
def call_retrieval_subgraph(state: AgentState):
    print(f"--- 1. START RETRIEVAL for: {state['question']} ---")
    # Invochiamo il sottografo compilato
    retrieval_app = build_retrieval_subgraph()
    result = retrieval_app.invoke({"question": state["question"]})
    return {"context_data": result["final_context"]}


# --- Main Workflow Construction ---
workflow = StateGraph(AgentState)

workflow.add_node("retrieval_process", call_retrieval_subgraph)


workflow.set_entry_point("retrieval_process")
workflow.add_edge("retrieval_process", END)
app = workflow.compile()

# --- Execution Example ---
if __name__ == "__main__":
    inputs = {"question": "Dammi il fatturato totale del mese scorso"}
    result = app.invoke(inputs)
    
    print("\n=== FINAL OUTPUT ===")
    print(f"Context Found:\n{result['context_data']}")