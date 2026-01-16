from typing import TypedDict, List, Annotated, Dict, Any
import operator

class RetrievalState(TypedDict):

    question: str
    
    search_text_datasources: str
    found_datasources: Annotated[List[str], operator.add]

    search_text_tables: str
    found_tables: Annotated[List[str], operator.add] 

    search_text_columns: str
    found_columns: Annotated[List[str], operator.add]

    search_text_edges: str
    found_edges: Annotated[List[str], operator.add]

    search_text_metrics: str
    found_metrics: Annotated[List[str], operator.add]  

    search_text_synonyms: str
    found_synonyms: Annotated[List[str], operator.add] 

    search_text_context_rules: str
    found_context_rules: Annotated[List[str], operator.add]

    search_text_low_cardinality_values: str
    found_low_cardinality_values: Annotated[List[str], operator.add] 

    search_text_golden_sqls: str
    found_golden_sqls: Annotated[List[dict], operator.add]
    
    final_context: str
