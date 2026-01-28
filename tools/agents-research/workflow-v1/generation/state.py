from typing import TypedDict, Optional, Dict, Any, List

class GenerationState(TypedDict):
    # --- INPUTS (From Global State) ---
    question: str
    refined_datasource: Dict[str, Any]
    query_blueprint: Dict[str, Any] # Our discursive plan
    
    # --- INTERNAL MEMORY ---
    candidate_sql: str
    validation_error: Optional[str] # If present, triggers the fixer
    attempt_count: int
    
    # --- OUTPUTS ---
    final_sql: str
    is_valid: bool
    local_logs: List[str]