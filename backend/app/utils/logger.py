import logging
import sys
from typing import Optional


def setup_logger(name: Optional[str] = "finlens") -> logging.Logger:
    """Configures a standardized structured logger for FinLens."""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # Console Handler with clear timestamp and component formatting
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        formatter = logging.Formatter(
            fmt="[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)d] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        logger.propagate = False
        
    return logger


logger = setup_logger()
