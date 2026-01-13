"""
Logging configuration and utilities.

This module provides centralized logging configuration for the application.
All loggers use a consistent format and output to stdout for container-friendly logging.

Future enhancements could include:
- JSON logging for structured log aggregation (ELK, CloudWatch, etc.)
- File-based logging with rotation
- Log level configuration from environment variables
- Contextual logging (request IDs, user IDs, etc.)
"""

import logging
import sys
from typing import Optional

# Configure base logging for the entire application
# This configuration applies to all loggers unless overridden
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)  # Output to stdout for container compatibility
    ],
    # Additional configuration options:
    # datefmt="%Y-%m-%d %H:%M:%S",  # Custom date format
    # force=True,  # Override existing configuration
)


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance for a module or component.
    
    This function creates or retrieves a logger with the specified name.
    The logger inherits the base configuration but can be customized per module.
    
    Args:
        name: Logger name, typically __name__ or module name.
              Examples: "main", "api.ontology", "services.embedding"
    
    Returns:
        logging.Logger: Configured logger instance
    
    Example:
        ```python
        from .core.logging import get_logger
        
        logger = get_logger(__name__)
        logger.info("Application started")
        logger.error("An error occurred", exc_info=True)
        ```
    
    Note:
        Logger names follow a hierarchy. For example:
        - "api" is the parent of "api.ontology"
        - Setting level on "api" affects all child loggers
        
    Future Enhancements:
        - Support JSON logging format for structured logs
        - Add request ID tracking
        - Support different log levels per module
        - Integration with external logging services
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    return logger
