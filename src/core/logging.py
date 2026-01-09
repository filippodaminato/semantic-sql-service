import logging
import sys
from typing import Optional

# Configure base logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance.
    In the future, this can be enhanced to support JSON logging or other formats.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    return logger
