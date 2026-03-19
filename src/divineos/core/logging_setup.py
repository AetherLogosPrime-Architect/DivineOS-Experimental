"""Centralized Logging Setup for DivineOS.

This module provides a single, centralized logging configuration using loguru.
All modules should use: from loguru import logger

The setup_logging() function should be called once at application startup.
"""

import sys
from pathlib import Path

from loguru import logger


def setup_logging() -> None:
    """Initialize loguru with persistent file output.

    This function:
    1. Removes the default loguru handler
    2. Adds a console handler (INFO+) with colored output
    3. Adds a file handler (DEBUG+) with rotation and retention
    4. Creates ~/.divineos directory if it doesn't exist

    This function is idempotent - calling it multiple times is safe.
    """
    # Remove default handler
    logger.remove()

    # Create ~/.divineos directory if it doesn't exist
    log_dir = Path.home() / ".divineos"
    log_dir.mkdir(exist_ok=True, parents=True)

    # Add console handler (INFO+)
    logger.add(
        sys.stderr,
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        colorize=True,
    )

    # Add file handler (DEBUG+) with rotation and retention
    log_file = log_dir / "divineos.log"
    logger.add(
        log_file,
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation="500 MB",
        retention="30 days",
    )
