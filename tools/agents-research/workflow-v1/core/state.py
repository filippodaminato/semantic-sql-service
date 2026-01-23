from typing import TypedDict, Optional, Dict, Any, List
from typing_extensions import Annotated
import operator

def merge_logs(a: List, b: List) -> List:
    """Merges logs from different subgraphs without overwriting."""
    return a + b

class AgentState(TypedDict):
    # META
    run_id: str       # UUID univoco della sessione di esecuzione
    
    # --- INPUT ---
    question: str
    user_id: Optional[str] = "default_user"
    
    # --- PHASE 1 OUTPUT: RETRIEVAL ---
    # The raw selected datasource containing all found tables.
    # This acts as input for the Refinement Phase.
    raw_datasource: Optional[Dict[str, Any]] 
    
    # --- PHASE 2 OUTPUT: REFINEMENT ---
    refined_datasource: Optional[Dict[str, Any]]
    
    # --- PHASE 3 OUTPUT: GENERATION ---
    final_sql: Optional[str]
    final_answer: Optional[str]
    
    # --- OBSERVABILITY ---
    # Accumulated trace logs for debugging purposes.
    global_logs: Annotated[List[str], merge_logs]