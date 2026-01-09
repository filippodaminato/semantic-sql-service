import os
from typing import Dict, Any

class Config:
    """
    Configuration manager for the Semantic CLI.
    Prioritizes:
    1. Environment variables (SEMANTIC_CLI_*)
    2. Defaults
    """
    
    DEFAULT_API_URL = "http://localhost:8000/api/v1/discovery"
    DEFAULT_TIMEOUT_SEC = 30
    DEFAULT_OUTPUT_FORMAT = "json"  # json, table

    def __init__(self):
        self.api_url = os.environ.get("SEMANTIC_CLI_API_URL", self.DEFAULT_API_URL).rstrip("/")
        self.timeout = int(os.environ.get("SEMANTIC_CLI_TIMEOUT", self.DEFAULT_TIMEOUT_SEC))
        self.output_format = os.environ.get("SEMANTIC_CLI_OUTPUT", self.DEFAULT_OUTPUT_FORMAT)
        self.debug = os.environ.get("SEMANTIC_CLI_DEBUG", "false").lower() == "true"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "api_url": self.api_url,
            "timeout": self.timeout,
            "output_format": self.output_format,
            "debug": self.debug
        }

settings = Config()
