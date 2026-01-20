from typing import TypedDict, List, Annotated, Dict, Any
import operator

class RetrievalState(TypedDict):

    user_prompt: str
    
    search_text_datasources: List[str]
    found_datasources: Annotated[List[dict], operator.add]

    search_text_tables: List[str]
    found_tables: Annotated[List[dict], operator.add] 

    search_text_columns: List[str]
    found_columns: Annotated[List[dict], operator.add]

    search_text_edges: List[str]
    found_edges: Annotated[List[dict], operator.add]

    search_text_metrics: List[str]
    found_metrics: Annotated[List[dict], operator.add]  

    search_text_synonyms: List[str]
    found_synonyms: Annotated[List[dict], operator.add] 

    search_text_context_rules: List[str]
    found_context_rules: Annotated[List[dict], operator.add]

    search_text_low_cardinality_values: List[str]
    found_low_cardinality_values: Annotated[List[dict], operator.add] 

    search_text_golden_sqls: List[str]
    found_golden_sqls: Annotated[List[dict], operator.add]
    
    final_context: List[Any]
