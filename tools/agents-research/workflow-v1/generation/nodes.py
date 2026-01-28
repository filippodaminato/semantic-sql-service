import json
import time
import logging
from generation.chains import build_generator_chain, build_validator_chain
from utils.formatter import AgentContextFormatter as ContextFormatter
from core.logger import log_llm_interaction, log_state_transition, NodeLoggerAdapter

logger = logging.getLogger("agent_logger")

async def sql_generator_node(state, llm):
    """Writes the SQL based on the Blueprint."""
    start_time = time.time()
    adapter = NodeLoggerAdapter(logger, {"node": "sql_generator_node"})
    adapter.info("▶️ NODE START")
    
    blueprint = state["query_blueprint"]
    ds = state["refined_datasource"]
    
    # We format the blueprint into a readable string
    if hasattr(blueprint, "dict"):
        blueprint_dict = blueprint.dict()
    elif hasattr(blueprint, "model_dump"): # Pydantic v2
        blueprint_dict = blueprint.model_dump()
    else:
        blueprint_dict = blueprint
        
    blueprint_str = json.dumps(blueprint_dict, indent=2)
    schema_str = ContextFormatter.to_markdown(ds)
    
    chain, prompt_tpl = build_generator_chain(llm)
    
    # If we are in a correction loop, we pass the previous error
    prev_error = state.get("validation_error", "None")
    
    inputs = {
        "blueprint_json": blueprint_str,
        "schema_context": schema_str,
        "previous_error": prev_error
    }
    
    try:
        # Generate prompt for logging
        prompt_val = await prompt_tpl.ainvoke(inputs)
        prompt_str = prompt_val.to_string()
        
        result = await chain.ainvoke(inputs)
    except Exception as e:
        adapter.error(f"❌ LLM Error in sql_generator_node: {str(e)}", exc_info=True)
        raise e
        
    duration = time.time() - start_time
    
    log_llm_interaction(
        adapter,
        step_name="sql_generator_node",
        inputs=inputs,
        outputs=result,
        latency=duration,
        prompt=prompt_str
    )
    
    log_state_transition(adapter, "sql_generator_node", {"candidate_sql": result.sql})
    
    return {
        "candidate_sql": result.sql,
        "attempt_count": state["attempt_count"] + 1,
        "local_logs": state["local_logs"] + ["SQL Generated."]
    }

async def sql_validator_node(state, llm):
    """Checks the SQL (Static Analysis or Dry-Run)."""
    start_time = time.time()
    adapter = NodeLoggerAdapter(logger, {"node": "sql_validator_node"})
    adapter.info("▶️ NODE START")
    
    sql = state["candidate_sql"]
    ds = state["refined_datasource"]
    schema_str = ContextFormatter.to_markdown(ds)
    
    # --- OPTION A: LLM Check ---
    chain, prompt_tpl = build_validator_chain(llm)
    
    inputs = {
        "schema_context": schema_str,
        "sql_code": sql
    }
    
    try:
        prompt_val = await prompt_tpl.ainvoke(inputs)
        prompt_str = prompt_val.to_string()
        
        res = await chain.ainvoke(inputs)
    except Exception as e:
        adapter.error(f"❌ LLM Error in sql_validator_node: {str(e)}", exc_info=True)
        raise e
    
    duration = time.time() - start_time
    
    log_llm_interaction(
        adapter,
        step_name="sql_validator_node",
        inputs=inputs,
        outputs=res,
        latency=duration,
        prompt=prompt_str
    )
    
    # --- OPTION B: Real DB 'EXPLAIN' (If you have the connection) ---
    # try:
    #     db.execute(f"EXPLAIN {sql}")
    #     res = ValidationResult(is_valid=True)
    # except Exception as e:
    #     res = ValidationResult(is_valid=False, error_message=str(e))
    
    if res.is_valid:
        adapter.info(f"✅ SQL Validation Passed\n```sql\n{sql}\n```")
        return {
            "is_valid": True,
            "final_sql": sql,
            "validation_error": None,
            "local_logs": state["local_logs"] + ["Validation Passed."]
        }
    else:
        adapter.warning(f"⚠️ SQL Validation Failed: {res.error_message}\n```sql\n{sql}\n```")
        log_state_transition(adapter, "sql_validator_node", {"error": res.error_message})
        return {
            "is_valid": False,
            "validation_error": res.error_message,
            "local_logs": state["local_logs"] + [f"Validation Failed: {res.error_message}"]
        }