import logging
import json
import os
import uuid
from typing import Any
from datetime import datetime
from pythonjsonlogger import jsonlogger

# Creiamo una cartella logs se non esiste
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
    Adapter custom che unisce (merge) i field extra passati al log
    con quelli definiti nell'adapter (es. node name).
    Il LoggerAdapter standard sovrascrive 'extra', perdendo i dati.
    """
    def process(self, msg, kwargs):
        # Se c'è già un extra nel kwargs, lo uniamo con self.extra (il contesto del nodo)
        extra_payload = kwargs.get("extra", {})
        # Facciamo update su una copia per non sporcare il dizionario originale se riusato
        merged_extra = self.extra.copy()
        merged_extra.update(extra_payload)
        
        kwargs["extra"] = merged_extra
        return msg, kwargs

def setup_logger(run_id: str):
    """Configura un logger che scrive tutto su file JSON e l'essenziale su Console."""
    
    logger = logging.getLogger("agent_logger")
    logger.setLevel(logging.DEBUG) # Catturiamo tutto
    
    # Evita duplicati se richiamato più volte
    if logger.handlers:
        return logger

    # --- HANDLER 1: FILE ROTATING (JSON) ---
    # Ogni run avrà il suo file univoco per debug facile
    log_filename = f"{LOG_DIR}/run_{run_id}.jsonl"
    file_handler = logging.FileHandler(log_filename)
    file_formatter = CustomJsonFormatter('%(timestamp)s %(level)s %(name)s %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # --- HANDLER 2: CONSOLE (Colorato e Sintetico) ---
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO) # In console solo l'essenziale
    # Formatter semplice per umani
    console_format = logging.Formatter('%(asctime)s - \033[94m%(name)s\033[0m - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    return logger

def log_llm_interaction(logger, step_name: str, inputs: dict, outputs: Any, latency: float = 0.0, prompt: str = None):
    """Helper per loggare input/output LLM in modo strutturato senza sporcare la console."""
    log_payload = {
        "event_type": "llm_call",
        "step": step_name,
        "inputs": inputs, # Dump completo inputs
        "outputs": getattr(outputs, "dict", lambda: str(outputs))(), # Gestisce Pydantic o str
        "latency_seconds": latency
    }
    
    if prompt:
        log_payload["prompt"] = prompt

    logger.debug(
        f"LLM Interaction: {step_name}",
        extra=log_payload
    )

def log_state_transition(logger, step_name: str, state_diff: dict):
    """Logga come cambia lo stato."""
    logger.info(
        f"State Updated: {step_name}",
        extra={
            "event_type": "state_transition",
            "state_updates": state_diff
        }
    )