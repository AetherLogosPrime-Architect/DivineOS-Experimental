"""
Logging configuration for clarity system.

Sets up structured logging for all clarity system components.
"""

import logging
import sys
from typing import Optional


def setup_clarity_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
) -> logging.Logger:
    """
    Set up logging for clarity system.

    Args:
        level: Logging level (default: INFO)
        log_file: Optional file to write logs to

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger("divineos.clarity_system")
    logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_clarity_logger(name: str) -> logging.Logger:
    """
    Get a logger for a clarity system component.

    Args:
        name: Component name

    Returns:
        Logger instance
    """
    return logging.getLogger(f"divineos.clarity_system.{name}")


# Module-level logger
logger = setup_clarity_logging()
