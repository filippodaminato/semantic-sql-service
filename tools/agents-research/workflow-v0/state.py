from typing import TypedDict, Annotated, List, Dict, Any, Optional
import operator

# Only merge logs, overwrite others
def merge_logs(a, b):
    if not a:
        return b
    if not b:
        return a
    return a + b

class AgentState(TypedDict):
    """
    The state of the agent workflow.
    """
    # Retrieval Phase
    question: str
    search_plan: Optional[Any] # Pydantic model
    selected_datasource: Optional[Any] # Pydantic model or dict
    
    # Refinement Phase
    working_datasource: Dict[str, Any]
    current_plan: Optional[Any] # QueryPlan
    iterations: int
    pending_search_results: List[Any]
    current_fetch_target: Any
    
    # Logs (Append only)
    logs: Annotated[List[Dict[str, Any]], merge_logs]
