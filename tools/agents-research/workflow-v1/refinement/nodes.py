import logging
import time
import copy
from refinement.chains import build_planner_chain, build_evaluator_chain, build_finalizer_chain
from refinement.tools import search_values, search_graph_paths, search_metadata
from utils.formatter import AgentContextFormatter as ContextFormatter
from core.logger import log_llm_interaction, log_state_transition, NodeLoggerAdapter

# Retrieve the configured logger
logger = logging.getLogger("agent_logger")

async def planner_node(state, llm):
    """Decides the next move (Prune, Fetch, or Ready)."""
    start_time = time.time()
    adapter = NodeLoggerAdapter(logger, {"node": "planner_node"})
    adapter.info("▶️ NODE START")

    # 1. Format Context
    context_md = ContextFormatter.to_markdown(state["working_datasource"])
    
    # 2. Invoke Planner (CoT)
    # 2. Invoke Planner (CoT)
    chain, prompt_tpl = build_planner_chain(llm)
    
    failed_txt = ", ".join(state.get("failed_targets", []))
    context_with_failed = f"{context_md}\n\n[ALREADY TRIED & FAILED]: {failed_txt}" if failed_txt else context_md
    
    inputs = {
        "question": state["question"],
        "context_md": context_with_failed
    }

    try:
        # Generate prompt string for logging
        prompt_val = await prompt_tpl.ainvoke(inputs)
        prompt_str = prompt_val.to_string()
        
        plan = await chain.ainvoke(inputs)
    except Exception as e:
        adapter.error(f"❌ LLM Error in planner_node: {str(e)}", exc_info=True)
        raise e

    duration = time.time() - start_time
    
    log_llm_interaction(
        adapter,
        step_name="planner_node",
        inputs={"question": state["question"]}, # Don't log full context to save space, maybe? Or log it.
        outputs=plan,
        latency=duration,
        prompt=prompt_str
    )
    
    log_state_transition(adapter, "planner_node", {"current_plan": plan.dict(), "iterations": state["iterations"] + 1})

    adapter.info(f"Planner Decision: {plan.action_type} | Reason: {plan.reasoning[:100]}...")
    
    # 3. SAFETY CHECK: Infinite Loop Prevention
    # If the LLM persists in fetching something we already failed to fetch/validate, force exist.
    failed_list = [f.lower() for f in state.get("failed_targets", [])]
    if plan.action_type == "FETCH":
        for t in plan.targets:
            if t.identifier.lower() in failed_list:
                adapter.warning(f"⚠️ LOOP DETECTED. Planner wants '{t.identifier}' but it is in failed_targets (normalized).")
                adapter.warning("➡️ Forcing Action to 'READY' to break loop.")
                
                # Force override
                plan.action_type = "READY"
                plan.reasoning = f"Forced READY. Planner tried to fetch failed target '{t.identifier}'."
                plan.targets = [] 
                break

    return {
        "current_plan": plan,
        "iterations": state["iterations"] + 1,
        "local_logs": state.get("local_logs", []) + [f"Plan: {plan.action_type} - {plan.reasoning}"]
    }

async def pruner_worker_node(state):
    """Executes Pruning (Removing items from schema)."""
    adapter = NodeLoggerAdapter(logger, {"node": "pruner_worker_node"})
    adapter.info("▶️ NODE START")
    
    plan = state["current_plan"]
    # Deep copy to avoid mutating previous states in memory if using state snapshots
    ds = copy.deepcopy(state["working_datasource"])
    
    pruned_count = 0
    targets = [t.identifier for t in plan.targets]
    
    if targets:
        adapter.debug(f"Pruning targets: {targets}")
        original_count = len(ds.get("tables", []))
        
        # Pruning Logic: Remove tables if their slug or name is in targets
        # Note: This is a simplistic implementation. A robust one would handle columns/metrics pruning too.
        ds["tables"] = [
            t for t in ds.get("tables", []) 
            if t.get("name") not in targets and t["slug"] not in targets and t.get("physical_name") not in targets
        ]
        
        pruned_count = original_count - len(ds["tables"])
        adapter.info(f"Pruned {pruned_count} tables from context.")
    
    log_state_transition(adapter, "pruner_worker_node", {"pruned_count": pruned_count})

    return {
        "working_datasource": ds,
        "local_logs": state.get("local_logs", []) + [f"Pruned {pruned_count} tables."]
    }

async def fetch_worker_node(state):
    """Dispatcher for search tools."""
    adapter = NodeLoggerAdapter(logger, {"node": "fetch_worker_node"})
    adapter.info("▶️ NODE START")
    
    plan = state["current_plan"]
    ds_slug = state["working_datasource"].get("slug", "default")
    
    # Process only the first target to keep loop focused (iterative)
    if not plan.targets:
        adapter.warning("Fetch plan has no targets!")
        return {"pending_search_results": [], "local_logs": state.get("local_logs", []) + ["Error: Fetch plan empty."]}

    target = plan.targets[0]
    adapter.info(f"Fetching target: {target.entity_type} -> {target.identifier}")
    
    # Extract filters from payload
    # Convert Pydantic model to dict, filtering None
    filters = target.payload.dict(exclude_none=True) if target.payload else {}
    
    # Remove datasource_slug from filters to avoid duplication as it is passed positionally
    filters.pop("datasource_slug", None)
    
    results = []
    start_time = time.time()
    
    try:
        if target.entity_type == "join_path":
            # Extract source/target from payload or dict
            possible_src = filters.get("source") or filters.get("source_table")
            possible_tgt = filters.get("target") or filters.get("target_table")
            
            if possible_src and possible_tgt:
                # Remove src/tgt from filters to avoid duplication in kwargs
                for k in ["source", "target", "source_table", "target_table"]:
                    filters.pop(k, None)
                    
                results = await search_graph_paths(possible_src, possible_tgt, ds_slug, **filters)
            else:
                # FALLBACK: Try to parse generic identifier "TableA, TableB" or "TableA to TableB"
                parts = []
                if "," in target.identifier:
                    parts = target.identifier.split(",")
                elif " to " in target.identifier:
                    parts = target.identifier.split(" to ")
                elif " and " in target.identifier:
                    parts = target.identifier.split(" and ")
                    
                if len(parts) >= 2:
                    src_f = parts[0].strip()
                    tgt_f = parts[1].strip()
                    adapter.info(f"🔄 Parsed join targets from identifier: {src_f} <-> {tgt_f}")
                    results = await search_graph_paths(src_f, tgt_f, ds_slug, **filters)
                else:
                    msg = f"Error: Missing source/target params for join_path. Identifier was: {target.identifier}"
                    adapter.error(msg)
                    results = [msg]
                
        elif target.entity_type in ["value", "low_cardinality_values"]:
             # Map 'value' or schema enum 'low_cardinality_values' to search_values
            results = await search_values(target.identifier, ds_slug, **filters)
            
        else:
            # Default to general metadata search
            results = await search_metadata(target.identifier, ds_slug, **filters)
            
    except Exception as e:
        adapter.error(f"Tool execution failed: {e}", exc_info=True)
        results = [f"System Error during fetch: {str(e)}"]

    duration = time.time() - start_time
    adapter.info(f"Fetch completed in {duration:.2f}s. Results: {len(results)}")
    
    # Log raw tool output
    adapter.debug("Tool Output", extra={"tool_results": results})

    # If no results, add to failed targets immediately
    failed_targets = state.get("failed_targets", [])
    if not results:
        failed_targets.append(target.identifier)

    return {
        "pending_search_results": results,
        "current_fetch_target": target,
        "local_logs": state.get("local_logs", []) + [f"Fetched {len(results)} raw results for {target.entity_type}."],
        "failed_targets": failed_targets
    }

async def generate_blueprint_node(state, llm):
    """
    Generates the final discursive blueprint.
    """
    start_time = time.time()
    adapter = NodeLoggerAdapter(logger, {"node": "generate_blueprint_node"})
    adapter.info("▶️ NODE START")

    ds = state["working_datasource"]
    question = state["question"]
    
    # Prepare context
    context_md = ContextFormatter.to_markdown(ds)
    notes = "\n".join(ds.get("enrichment_notes", []))
    
    adapter.debug("Generating Blueprint with confirmed notes", extra={"notes_count": len(ds.get("enrichment_notes", []))})

    chain, prompt_tpl = build_finalizer_chain(llm)
    
    inputs = {
        "question": question,
        "context_md": context_md,
        "notes": notes
    }
    
    try:
        # Generate prompt string for logging
        prompt_val = await prompt_tpl.ainvoke(inputs)
        prompt_str = prompt_val.to_string()
        
        blueprint = await chain.ainvoke(inputs)
    except Exception as e:
        adapter.error(f"❌ LLM Error in generate_blueprint_node: {str(e)}", exc_info=True)
        raise e
    
    duration = time.time() - start_time
    
    log_llm_interaction(
        adapter,
        step_name="generate_blueprint_node",
        inputs={"question": question, "notes_count": len(ds.get("enrichment_notes", []))},
        outputs=blueprint,
        latency=duration,
        prompt=prompt_str
    )
    
    # Save to 'final_logical_plan'
    return {
        "final_logical_plan": blueprint,
        "local_logs": state.get("local_logs", []) + ["Blueprint generated."]
    }

async def evaluator_node(state, llm):
    """Analyzes raw results and updates context."""
    start_time = time.time()
    adapter = NodeLoggerAdapter(logger, {"node": "evaluator_node"})
    adapter.info("▶️ NODE START")

    raw_results = state["pending_search_results"]
    target = state["current_fetch_target"]
    
    if not raw_results:
        adapter.warning("No results to evaluate.")
        return {"local_logs": state.get("local_logs", []) + ["Evaluator: No results to evaluate."]}

    # Prepare inputs
    # Handle mixed types in raw_results (strings, dicts)
    results_txt = "\n".join([f"- {str(r)}" for r in raw_results])
    
    target_desc = f"{target.entity_type}: {target.identifier}"
    
    inputs = {
        "question": state["question"],
        "target_description": target_desc,
        "raw_results_txt": results_txt
    }
    
    chain, prompt_tpl = build_evaluator_chain(llm)
    
    try:
        # Generate prompt string for logging
        prompt_val = await prompt_tpl.ainvoke(inputs)
        prompt_str = prompt_val.to_string()
        
        evaluation = await chain.ainvoke(inputs)
    except Exception as e:
        adapter.error(f"❌ LLM Error in evaluator_node: {str(e)}", exc_info=True)
        raise e
        
    duration = time.time() - start_time
    
    log_llm_interaction(
        adapter,
        step_name="evaluator_node",
        inputs=inputs,
        outputs=evaluation,
        latency=duration,
        prompt=prompt_str
    )
    
    # Update Schema if relevant
    ds = copy.deepcopy(state["working_datasource"])
    log_msg = f"Evaluator: Rejected results for {target.identifier}"
    
    failed_target_id = None
    
    if evaluation.is_relevant and evaluation.context_note:
        if "enrichment_notes" not in ds:
            ds["enrichment_notes"] = []
        
        # Inject the note
        note = f"[{target.entity_type.upper()}] {evaluation.context_note}"
        ds["enrichment_notes"].append(note)
        log_msg = f"Evaluator: Added note -> {note}"
        adapter.info(f"✅ Note Added: {note}")
    else:
        adapter.info("Results deemed irrelevant by Evaluator.")
        # Mark as failed/rejected so we don't fetch again
        failed_target_id = target.identifier

    log_state_transition(adapter, "evaluator_node", {"new_note": evaluation.context_note if evaluation.is_relevant else None})

    current_failed = state.get("failed_targets", [])
    if failed_target_id:
        current_failed.append(failed_target_id.lower())
        
    return {
        "working_datasource": ds,
        "pending_search_results": [], # Clear buffer
        "current_fetch_target": None,
        "local_logs": state.get("local_logs", []) + [log_msg],
        "failed_targets": current_failed
    }