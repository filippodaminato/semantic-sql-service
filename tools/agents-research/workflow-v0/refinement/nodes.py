from typing import Dict, Any, List
from state import AgentState
from refinement.schemas import QueryPlan, SearchEvaluation
from refinement.tools import search_tables, search_columns
from utils.context_formatter import AgentContextFormatter
from pydantic import BaseModel, Field

# --- Nodes ---

async def planner_node(state: AgentState, llm):
    """
    Decides the next step: PRUNE, FETCH, or READY.
    """
    datasource = state["working_datasource"]
    question = state["question"]
    iterations = state["iterations"]
    
    # Format context for LLM
    context_md = AgentContextFormatter.datasource_to_markdown(datasource)
    
    planner = llm.with_structured_output(QueryPlan)
    
    prompt = f"""You are a Database Context Refiner. Your goal is to perfect the context for answering the user's question.
    
    User Question: "{question}"
    
    Current Context:
    {context_md}
    
    Iteration: {iterations}
    
    Analyze the context.
    - If there is irrelevant noise (tables/columns not needed), PRUNE it.
    - If information is missing (e.g. need specific values, formulas, or check if a table exists), FETCH it.
    - If the context is sufficient and clean, output READY.
    """
    
    plan = await planner.ainvoke(prompt)
    
    return {
        "current_plan": plan,
        "iterations": iterations + 1,
        "logs": [{
            "step": "refinement_plan",
            "iteration": iterations + 1,
            "plan": plan.dict()
        }]
    }

def pruner_worker_node(state: AgentState):
    """
    Executes PRUNE actions.
    """
    plan = state["current_plan"]
    ds = state["working_datasource"]
    
    pruned_tables = []
    pruned_columns = []
    
    if plan.action_type == "PRUNE":
        for target in plan.prune_targets:
            if target.target_type == "table":
                # Logic to remove table from ds['tables']
                original_tables = ds.get("tables", [])
                ds["tables"] = [t for t in original_tables if t.get("name") != target.name]
                if len(ds["tables"]) < len(original_tables):
                    pruned_tables.append(target.name)
            elif target.target_type == "column":
                # Logic to remove column from specific table? 
                # Name might be 'table.column'
                pass # implementation detail omitted for brevity in restore
    
    return {
        "working_datasource": ds,
        "logs": [{
            "step": "pruner_worker",
            "pruned_tables": pruned_tables,
            "pruned_columns": pruned_columns
        }]
    }

async def fetch_worker_node(state: AgentState):
    """
    Executes FETCH actions.
    """
    plan = state["current_plan"]
    ds = state["working_datasource"]
    ds_slug = ds.get("slug")
    
    target = plan.fetch_targets[0] if plan.fetch_targets else None
    results = []
    
    if target:
        # Simple dispatch
        results = await search_tables(target.search_text, ds_slug)
    
    return {
        "pending_search_results": results,
        "current_fetch_target": target,
        "logs": [{
            "step": "fetch_worker",
            "target": target.dict() if target else {},
            "found_count": len(results)
        }]
    }

async def search_evaluator_node(state: AgentState, llm):
    """
    Evaluates search results and enriches context.
    """
    question = state["question"]
    target = state["current_fetch_target"]
    raw_results = state["pending_search_results"]
    
    evaluator = llm.with_structured_output(SearchEvaluation)
    
    results_str = str(raw_results)[:2000] # Truncate for prompt
    
    prompt = f"""Evaluate these search results for the question: "{question}"
    Search Target: {target.search_text if target else 'N/A'}
    Results:
    {results_str}
    
    Are they relevant? If yes, provide a strict Note to add to the context.
    """
    
    evaluation = await evaluator.ainvoke(prompt)
    ds = state["working_datasource"]
    
    if not evaluation.is_irrelevant and evaluation.formatted_note:
        if "enrichment_notes" not in ds:
            ds["enrichment_notes"] = []
        ds["enrichment_notes"].append(evaluation.formatted_note)
    
    return {
        "working_datasource": ds,
        "pending_search_results": [],
        "logs": [{
            "step": "search_evaluator",
            "evaluation": evaluation.dict()
        }]
    }

def router_logic(state: AgentState):
    """
    Routes based on planner decision.
    """
    if state["iterations"] > 5:
        return "generate_sql"
    
    plan = state.get("current_plan")
    if not plan:
        return "generate_sql"
        
    action = plan.action_type
    if action == "PRUNE":
        return "pruner_worker"
    elif action == "FETCH":
        return "fetch_worker"
    elif action == "READY":
        return "generate_sql"
    
    return "generate_sql"
