import json
import asyncio
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field

from state import AgentState
from retrieval.service import RetrievalService

# --- Schemas ---

class SearchPlan(BaseModel):
    """Derived from the user question."""
    search_text_datasources: list[str] = Field(default_factory=list)
    search_text_tables: list[str] = Field(default_factory=list)
    search_text_columns: list[str] = Field(default_factory=list)
    search_text_metrics: list[str] = Field(default_factory=list)
    search_text_context_rules: list[str] = Field(default_factory=list)
    reasoning: str = Field(..., description="Why these search terms?")

class DatasourceSelection(BaseModel):
    """Selection of the best datasource."""
    selected_datasource_slug: str = Field(..., description="Slug of the selected datasource")
    reasoning: str = Field(..., description="Why this datasource is the best fit.")

# --- Nodes ---

async def plan_search_node(state: AgentState, llm):
    """
    Step 1: Analyze question and plan search queries.
    """
    planner = llm.with_structured_output(SearchPlan)
    question = state["question"]
    
    prompt = f"""Plan a search to answer: "{question}"
    Identify keywords for datasources, tables, columns, and metrics.
    """
    
    plan = await planner.ainvoke(prompt)
    
    return {
        "search_plan": plan, # Store Pydantic model
        "logs": [{
            "step": "plan_search",
            "content": plan.dict()
        }]
    }

async def retrieve_and_select_node(state: AgentState, llm, retrieval_service):
    """
    Step 2: Execute search and select datasource.
    """
    plan = state["search_plan"]
    
    # Execute Search
    # Convert plan to dict if needed by service
    search_results = await retrieval_service.execute_hierarchical_search(plan.dict())
    
    # Select Datasource
    selector = llm.with_structured_output(DatasourceSelection)
    
    results_str = str(search_results.get("results", []))[:3000] # Truncate
    
    prompt = f"""Given the user question: "{state['question']}"
    And these search results:
    {results_str}
    
    Select the single most relevant datasource.
    """
    
    selection = await selector.ainvoke(prompt)
    
    # Construct 'selected_datasource' object/dict
    # Ideally we find the full object from results matchin slug
    # For now, we mock/construct a minimal one or find it
    
    selected_ds = None
    for item in search_results.get("results", []):
         if isinstance(item, dict) and item.get("slug") == selection.selected_datasource_slug:
             selected_ds = item
             break
    
    if not selected_ds:
        # Fallback
        selected_ds = {"slug": selection.selected_datasource_slug, "name": "Unknown", "tables": []}

    return {
        "selected_datasource": selected_ds,
        "logs": [{
            "step": "retrieval_selection",
            "retrieved_count": search_results.get("raw_count"),
            "reasoning": selection.reasoning,
            "selection_decision": selection # Store the Pydantic model for verify logic
        }]
    }