"""
Logging configuration for agent integration module.

Provides structured logging for all agent integration components
with appropriate log levels and formatting.
"""

import logging

# Module logger
logger = logging.getLogger("divineos.agent_integration")

# Component loggers
mcp_integration_logger = logging.getLogger("divineos.agent_integration.mcp")
loop_prevention_logger = logging.getLogger("divineos.agent_integration.loop_prevention")
learning_loop_logger = logging.getLogger("divineos.agent_integration.learning_loop")
behavior_analyzer_logger = logging.getLogger("divineos.agent_integration.behavior_analyzer")
feedback_system_logger = logging.getLogger("divineos.agent_integration.feedback_system")


def setup_logging(level: int = logging.INFO) -> None:
    """
    Set up logging for agent integration module.

    Args:
        level: Logging level (default: logging.INFO)
    """
    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s | %(name)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Configure main logger
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(level)

    # Configure component loggers
    for component_logger in [
        mcp_integration_logger,
        loop_prevention_logger,
        learning_loop_logger,
        behavior_analyzer_logger,
        feedback_system_logger,
    ]:
        if not component_logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(formatter)
            component_logger.addHandler(handler)
            component_logger.setLevel(level)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific component.

    Args:
        name: Component name

    Returns:
        Logger instance
    """
    return logging.getLogger(f"divineos.agent_integration.{name}")
