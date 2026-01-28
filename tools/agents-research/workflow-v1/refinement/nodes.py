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
    
    # Organize targets by type for efficient processing
    targets_by_type = {}
    for t in plan.targets:
        if t.entity_type not in targets_by_type:
            targets_by_type[t.entity_type] = set()
        targets_by_type[t.entity_type].add(t.identifier)

    # 1. Prune Tables
    if "tables" in targets_by_type:
        table_targets = targets_by_type["tables"]
        original_tables = len(ds.get("tables", []))
        ds["tables"] = [
            t for t in ds.get("tables", []) 
            if t.get("name") not in table_targets 
            and t["slug"] not in table_targets 
            and t.get("physical_name") not in table_targets
        ]
        pruned_count += (original_tables - len(ds["tables"]))

    # 2. Prune Columns
    if "columns" in targets_by_type:
        col_targets = targets_by_type["columns"]
        for table in ds.get("tables", []):
            if "columns" in table:
                original_cols = len(table["columns"])
                table["columns"] = [
                    c for c in table["columns"]
                    if c.get("name") not in col_targets 
                    and c["slug"] not in col_targets
                ]
                pruned_count += (original_cols - len(table["columns"]))

    # 3. Prune Metrics
    if "metrics" in targets_by_type:
        metric_targets = targets_by_type["metrics"]
        original_metrics = len(ds.get("metrics", []))
        ds["metrics"] = [
            m for m in ds.get("metrics", [])
            if m.get("name") not in metric_targets and m["slug"] not in metric_targets
        ]
        pruned_count += (original_metrics - len(ds["metrics"]))

    # 4. Prune Edges (Relationships)
    if "edges" in targets_by_type:
        edge_targets = targets_by_type["edges"]
        original_edges = len(ds.get("edges", []))
        ds["edges"] = [
            e for e in ds.get("edges", [])
            if str(e.get("id")) not in edge_targets # ID is usually safe
            and e.get("slug") not in edge_targets
        ]
        pruned_count += (original_edges - len(ds["edges"]))

    # 5. Prune Golden SQLs
    if "golden_sqls" in targets_by_type:
        gsql_targets = targets_by_type["golden_sqls"]
        original_gsqls = len(ds.get("golden_sqls", []))
        ds["golden_sqls"] = [
            g for g in ds.get("golden_sqls", [])
            if str(g.get("id")) not in gsql_targets
            and g.get("prompt") not in gsql_targets # Sometimes prompts are used as identifiers
        ]
        pruned_count += (original_gsqls - len(ds["golden_sqls"]))
        
    # 6. Prune Low Cardinality Values (from Context Rules or Columns?)
    # Usually these are attached to columns. If the request is to prune values, we might need to clear nominal_values.
    # Implementation depends on where they are stored. Usually in column['nominal_values'].
    if "low_cardinality_values" in targets_by_type:
        lcv_targets = targets_by_type["low_cardinality_values"]
        # This is tricky because LCVs are lists inside columns.
        # We assume identifier points to the column slug from which to remove values, or the value itself?
        # For now, if a column slug is targeted here, we clear its nominal_values.
        for table in ds.get("tables", []):
            for col in table.get("columns", []):
                if col["slug"] in lcv_targets or col.get("name") in lcv_targets:
                     col["nominal_values"] = []
                     pruned_count += 1
    
    # 7. Prune Context Rules
    if "context_rules" in targets_by_type:
        rule_targets = targets_by_type["context_rules"]
        for table in ds.get("tables", []):
            for col in table.get("columns", []):
                if "context_rules" in col and col["context_rules"]:
                    original_rules = len(col["context_rules"])
                    col["context_rules"] = [
                        r for r in col["context_rules"]
                        if r.get("slug") not in rule_targets
                        and r.get("rule_text") not in rule_targets
                    ]
                    pruned_count += (original_rules - len(col["context_rules"]))
    
    adapter.info(f"Pruned {pruned_count} items from context.")
    log_state_transition(adapter, "pruner_worker_node", {"pruned_count": pruned_count})

    return {
        "working_datasource": ds,
        "local_logs": state.get("local_logs", []) + [f"Pruned {pruned_count} items."]
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
                    
                    # Try to resolve semantic/physical names to slugs from current context
                    current_tables = state["working_datasource"].get("tables", [])
                    
                    def resolve_slug(name_or_slug):
                        # 1. Check if it matches a slug exactly
                        for t in current_tables:
                            if t["slug"] == name_or_slug:
                                return t["slug"]
                        # 2. Check physical name
                        for t in current_tables:
                            if t.get("physical_name") == name_or_slug:
                                return t["slug"]
                        # 3. Check semantic name
                        for t in current_tables:
                            if t.get("name") == name_or_slug: # name often holds semantic name in some contexts
                                return t["slug"]
                        return name_or_slug # Fallback

                    src_resolved = resolve_slug(src_f)
                    tgt_resolved = resolve_slug(tgt_f)

                    adapter.info(f"🔄 Parsed join targets: {src_f} -> {src_resolved} <-> {tgt_f} -> {tgt_resolved}")
                    results = await search_graph_paths(src_resolved, tgt_resolved, ds_slug, **filters)
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
    Genera il piano discorsivo finale.
    """
    start_time = time.time()
    adapter = NodeLoggerAdapter(logger, {"node": "generate_blueprint_node"})
    adapter.info("▶️ NODE START")

    ds = state["working_datasource"]
    question = state["question"]
    
    # Prepariamo il contesto
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
    
    # Salviamo nel campo 'final_logical_plan'
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
        
    # --- SIDE EFFECT: Inject Columns if Join Path ---
    if evaluation.is_relevant and target.entity_type == "join_path":
        _inject_columns_from_paths(ds, raw_results, adapter)
        
    return {
        "working_datasource": ds,
        "pending_search_results": [], # Clear buffer
        "current_fetch_target": None,
        "local_logs": state.get("local_logs", []) + [log_msg],
        "failed_targets": current_failed
    }

def _inject_columns_from_paths(ds, paths, adapter):
    """
    Parses structured join paths and adds missing columns to the datasource.
    Crucial for Validator to accept FKs/PKs that were filtered out during Retrieval.
    """
    for path in paths:
        if not isinstance(path, list): continue # Skip error strings
        
        for hop in path:
            # hop = {source: {...}, target: {...}}
            if not isinstance(hop, dict): continue
            
            src = hop.get("source")
            tgt = hop.get("target")
            
            if src: _ensure_column_exists(ds, src, adapter)
            if tgt: _ensure_column_exists(ds, tgt, adapter)

def _ensure_column_exists(ds, col_info, adapter):
    """
    col_info: {table_slug, column_slug, column_name, ...}
    """
    t_slug = col_info.get("table_slug")
    c_name = col_info.get("column_name")
    c_slug = col_info.get("column_slug")
    
    if not t_slug or not c_name: return

    # Find Table
    table_obj = next((t for t in ds.get("tables", []) if t["slug"] == t_slug), None)
    if not table_obj:
        # Table might be missing? That would be weird if retrieval found the path.
        # But if pruned, maybe we shouldn't add it back? 
        # Actually, if we are joining on it, we probably need it.
        # For now, only add column if table exists.
        return

    # Check if column exists
    if "columns" not in table_obj: table_obj["columns"] = []
    
    exists = any(c.get("name") == c_name or c.get("slug") == c_slug for c in table_obj["columns"])
    
    if not exists:
        # Construct a minimal column object
        # We don't have full metadata (type, desc) from search_graph_paths usually, 
        # unless search_graph_paths returns it.
        # Looking at logs: source: {table_slug..., column_name...}
        # It lacks type and description. 
        # But for the Validator (LLM), existence is often enough, 
        # or we defaults.
        new_col = {
            "name": c_name,
            "slug": c_slug or f"{t_slug}_{c_name}",
            "physical_name": c_name,
            "description": "Injected from Join Path",
            "data_type": "UNKNOWN", # Ideally we fetch this, but for now this unblocks 404
            "is_injected": True
        }
        table_obj["columns"].append(new_col)
        adapter.info(f"💉 Injected missing column `{c_name}` into `{t_slug}` from Join Path.")