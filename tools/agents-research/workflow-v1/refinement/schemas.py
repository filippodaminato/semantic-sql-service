from pydantic import BaseModel, Field
from typing import Literal, List, Optional, Dict, Any

class RefinementPayload(BaseModel):
    """Specific payload for refinement actions."""
    source: Optional[str] = None
    target: Optional[str] = None
    source_table: Optional[str] = None
    target_table: Optional[str] = None
    table_slug: Optional[str] = None
    column_slug: Optional[str] = None
    datasource_slug: Optional[str] = None
    max_depth: Optional[int] = None

class RefinementTarget(BaseModel):
    """Identifies a specific entity in the schema or a concept to search for."""
    entity_type: Literal["tables", "columns", "golden_sqls", "metrics", "context_rules", "low_cardinality_values","join_path"] = Field(
        ..., 
        description="The type of entity. Use 'join_path' when you have two tables and you have to know how to link them (never guess)."
    )
    identifier: str = Field(
        ..., 
        description="The slug/name of the entity (for PRUNE) or the search term (for FETCH)."
    )
    payload: Optional[RefinementPayload] = Field(
        default=None,
        description="Additional parameters for specific actions."
    )

class RefinementPlan(BaseModel):
    """The strategic decision made by the Planner."""
    reasoning: str = Field(
        ..., 
        description="Detailed Chain-of-Thought: Analyze the current schema vs user question. Explain WHY you are pruning or fetching."
    )
    action_type: Literal["PRUNE", "FETCH", "READY"] = Field(
        ..., 
        description="PRUNE: Remove noise. FETCH: Find missing values/paths. READY: Schema is perfect."
    )
    targets: List[RefinementTarget] = Field(
        default=[], 
        description="List of items to prune or fetch."
    )

class EvaluationResult(BaseModel):
    """The verdict from the Evaluator on search results."""
    reasoning: str = Field(
        ..., 
        description="Critical analysis: Compare the user's intent with the raw search results. Resolve ambiguities."
    )
    is_relevant: bool = Field(
        ..., 
        description="True if at least one result is useful for the query."
    )
    context_note: Optional[str] = Field(
        None, 
        description="A concise, affirmed note to inject into the context (e.g., 'Join X and Y via column Z')."
    )
    
class QueryBlueprint(BaseModel):
    """
    The technical specification document for the SQL Generator.
    It is not code, but an algorithmic description of the solution.
    """
    approach_summary: str = Field(
        ..., 
        description="High-level strategy (e.g., 'Use a CTE to calculate monthly avg, then filter')."
    )
    
    logical_steps: List[str] = Field(
        ..., 
        description="Step-by-step instructions (e.g., '1. Join Orders and Users on user_id. 2. Filter status=shipped')."
    )
    
    necessary_filters: List[str] = Field(
        default=[], 
        description="List of strict constraints derived from user question and validated values (e.g., 'region MUST be 'Veneto'')."
    )
    
    caveats: List[str] = Field(
        default=[], 
        description="Technical warnings or schema quirks identified during refinement (e.g., 'Remember that revenue is in cents')."
    )