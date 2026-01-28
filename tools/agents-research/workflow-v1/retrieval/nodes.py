import logging
import time
from retrieval.chains import build_search_planner_chain, build_selector_chain
from retrieval.tools import perform_discovery
from utils.formatter import AgentContextFormatter
from core.logger import log_llm_interaction, log_state_transition, NodeLoggerAdapter

# Retrieve the configured logger
logger = logging.getLogger("agent_logger")

async def plan_search_node(state, llm):
    start_time = time.time()
    # Use Adapter to inject node context
    adapter = NodeLoggerAdapter(logger, {"node": "plan_search_node"})
    adapter.info("▶️ NODE START")
    
    # 1. Logic
    chain, prompt_tpl = build_search_planner_chain(llm)
    
    # Log Pre-Execution (What are we about to ask?)
    adapter.debug("Building Prompt for Search Planner", extra={"input_question": state["question"]})

    try:
        # Generate the Prompt string for logging
        prompt_val = await prompt_tpl.ainvoke({"question": state["question"]})
        prompt_str = prompt_val.to_string() # Or .to_messages() depending on format preference

        plan = await chain.ainvoke({"question": state["question"]})
    except Exception as e:
        adapter.error(f"❌ LLM Error in plan_search_node: {str(e)}", exc_info=True)
        raise e

    duration = time.time() - start_time

    # 2. EXHAUSTIVE LOG (LLM Input/Output)
    # This goes into the JSONL file, doesn't clog the console
    log_llm_interaction(
        adapter, 
        step_name="plan_search_node", 
        inputs={"question": state["question"]}, 
        outputs=plan, 
        latency=duration,
        prompt=prompt_str
    )

    # 3. Log State Change
    log_state_transition(adapter, "plan_search_node", {"search_plan": plan.dict()})
    
    # Extract keywords for summary log
    keywords_summary = (
        f"DS: {len(plan.search_text_datasources)} | "
        f"Tables: {len(plan.search_text_tables)} | "
        f"Cols: {len(plan.search_text_columns)} | "
        f"Metrics: {len(plan.search_text_metrics)} | "
        f"Edges: {len(plan.search_text_edges)} | "
        f"Rules: {len(plan.search_text_context_rules)} | "
        f"Vals: {len(plan.search_text_low_cardinality_values)} | "
        f"G.SQL: {len(plan.search_text_golden_sqls)}"
    )

    return {
        "search_plan": plan,
        "local_logs": [f"Planned search. {keywords_summary}"]
    }

async def execute_search_node(state):
    """Executes the search API call using REAL tools."""
    start_time = time.time()
    # Use Adapter to inject node context
    adapter = NodeLoggerAdapter(logger, {"node": "execute_search_node"})
    adapter.info("▶️ NODE START")
    
    plan = state["search_plan"]
    
    try:
        # Real API Call
        response_data = await perform_discovery(plan)
        
        # Format results using the profesional formatter
        context_txt = AgentContextFormatter.format_resolved_context(response_data)
        
    except Exception as e:
        adapter.error(f"❌ API Error in execute_search_node: {str(e)}", exc_info=True)
        raise e

    duration = time.time() - start_time
    
    found_count = len(response_data.get("graph", []))
    adapter.info(f"API Call completed in {duration:.2f}s. Found {found_count} items.")
    
    # Log Full API Response for Inspection
    adapter.debug("API Response Payload", extra={"api_response": response_data})

    return {
        "raw_api_response": response_data,
        "retrieved_results_txt": context_txt,
        "local_logs": [f"Executed search. Found {found_count} datasources in graph."]
    }

async def select_datasource_node(state, llm):
    """Decides which datasource to use based on search results."""
    start_time = time.time()
    # Use Adapter to inject node context
    adapter = NodeLoggerAdapter(logger, {"node": "select_datasource_node"})
    adapter.info("▶️ NODE START")
    
    chain, prompt_tpl = build_selector_chain(llm)
    
    inputs = {
        "question": state["question"],
        "context": state["retrieved_results_txt"]
    }

    try:
        # Generate Prompt string for logging
        prompt_val = await prompt_tpl.ainvoke(inputs)
        prompt_str = prompt_val.to_string()
        
        selection = await chain.ainvoke(inputs)
    except Exception as e:
        adapter.error(f"❌ LLM Error in select_datasource_node: {str(e)}", exc_info=True)
        raise e
    
    duration = time.time() - start_time
    
    log_llm_interaction(
        adapter, 
        step_name="select_datasource_node", 
        inputs=inputs, # Pass FULL inputs (including full context string)
        outputs=selection, 
        latency=duration,
        prompt=prompt_str
    )

    # Lookup the full datasource object
    selected_ds_obj = None
    # raw_api_response is in local state if we are in subgraph or global state if we are lucky. 
    # LangGraph merges state, so raw_api_response returned by previous node should be here.
    raw_response = state.get("raw_api_response", {})
    graph_list = raw_response.get("graph", [])
    
    for ds in graph_list:
        if ds.get("name") == selection.selected_datasource_name:
            selected_ds_obj = ds
            break
            
    if not selected_ds_obj:
        adapter.warning(f"⚠️ Selected Datasource '{selection.selected_datasource_name}' not found in API response graph.")
        
        # FALLBACK STRATEGY:
        # If the LLM failed to match, or said N/A, but we HAVE results from search, 
        # let's pick the first one as a best-effort guess (since search found it relevant).
        if graph_list:
            selected_ds_obj = graph_list[0]
            adapter.info(f"🔄 Fallback: Defaulting to first available datasource: {selected_ds_obj.get('name')}")
        else:
            # User requested object, so if missing, maybe we maintain name or Partial dict
            selected_ds_obj = {"name": selection.selected_datasource_name, "error": "Object not found in graph", "slug": "default"}

    return {
        "selection": selection,
        "raw_datasource": selected_ds_obj, 
        "local_logs": [f"Selected Datasource: {selection.selected_datasource_name} - {selection.thought_process}"]
    }