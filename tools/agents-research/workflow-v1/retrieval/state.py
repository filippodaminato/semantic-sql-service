from typing import TypedDict, Optional, Any, List
from retrieval.schemas import SearchPlan, DataSourceSelection

class RetrievalState(TypedDict):
    # Input (Mapped from Global State)
    question: str
    
    # Internal Memory
    search_plan: Optional[SearchPlan]
    retrieved_results_txt: str # Markdown text context for the LLM
    raw_api_response: Any      # Full API response object (to extract JSON later)
    
    # Local Output
    selection: Optional[DataSourceSelection]
    local_logs: List[str]
    raw_datasource: Any # Propagated to AgentState