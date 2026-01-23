from typing import TypedDict, List, Dict, Any, Optional
from refinement.schemas import RefinementPlan, RefinementTarget, QueryBlueprint

class RefinementState(TypedDict):
    # --- INPUT ---
    question: str
    working_datasource: Dict[str, Any] # Mutable schema that evolves
    
    # --- LOOP MEMORY ---
    current_plan: Optional[RefinementPlan]
    iterations: int
    
    # --- FETCH/EVAL BUFFER ---
    current_fetch_target: Optional[RefinementTarget]
    pending_search_results: List[Any] # Raw results from tools
    failed_targets: List[str] # List of identifiers that returned no results or were rejected

    # The final blueprint generated before exit
    final_logical_plan: Optional[QueryBlueprint]
    
    # --- LOGS ---
    local_logs: List[str]