import logging
import json
import os
import uuid
from typing import Any
from datetime import datetime
from pythonjsonlogger import jsonlogger

# Create a logs directory if it does not exist
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        if not log_record.get('timestamp'):
            log_record['timestamp'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        if log_record.get('level'):
            log_record['level'] = log_record['level'].upper()
        else:
            log_record['level'] = record.levelname

class NodeLoggerAdapter(logging.LoggerAdapter):
    """
    Custom adapter that merges extra fields passed to the log
    with those defined in the adapter (e.g. node name).
    The standard LoggerAdapter overwrites 'extra', losing data.
    """
    def process(self, msg, kwargs):
        # If there is already an extra in kwargs, we merge it with self.extra (the node context)
        extra_payload = kwargs.get("extra", {})
        # We update on a copy to avoid polluting the original dictionary if reused
        merged_extra = self.extra.copy()
        merged_extra.update(extra_payload)
        
        kwargs["extra"] = merged_extra
        return msg, kwargs

def setup_logger(run_id: str):
    """Configures a logger that writes everything to a JSON file and the essentials to Console."""
    
    logger = logging.getLogger("agent_logger")
    logger.setLevel(logging.DEBUG) # Catch everything
    
    # Avoid duplicates if called multiple times
    if logger.handlers:
        return logger

    # --- HANDLER 1: FILE ROTATING (JSON) ---
    # Each run will have its unique file for easy debugging
    log_filename = f"{LOG_DIR}/run_{run_id}.jsonl"
    file_handler = logging.FileHandler(log_filename)
    file_formatter = CustomJsonFormatter('%(timestamp)s %(level)s %(name)s %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # --- HANDLER 2: CONSOLE (Colored and Concise) ---
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO) # In console only the essentials
    # Simple formatter for humans
    console_format = logging.Formatter('%(asctime)s - \033[94m%(name)s\033[0m - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    return logger

def log_llm_interaction(logger, step_name: str, inputs: dict, outputs: Any, latency: float = 0.0, prompt: str = None):
    """Helper to log LLM input/output in a structured way without cluttering the console."""
    log_payload = {
        "event_type": "llm_call",
        "step": step_name,
        "inputs": inputs, # Full inputs dump
        "outputs": getattr(outputs, "dict", lambda: str(outputs))(), # Handles Pydantic or str
        "latency_seconds": latency
    }
    
    if prompt:
        log_payload["prompt"] = prompt

    logger.debug(
        f"LLM Interaction: {step_name}",
        extra=log_payload
    )

def log_state_transition(logger, step_name: str, state_diff: dict):
    """Logs how the state changes."""
    logger.info(
        f"State Updated: {step_name}",
        extra={
            "event_type": "state_transition",
            "state_updates": state_diff
        }
    )