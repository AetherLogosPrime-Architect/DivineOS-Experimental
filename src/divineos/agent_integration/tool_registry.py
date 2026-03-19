"""Tool Registry for Agent Integration.

Maintains a registry of all Kiro agent tools that should be captured,
and provides utilities for tool registration and lookup.
"""

from collections.abc import Callable
from typing import Any

from loguru import logger

# Registry of all Kiro agent tools that should be captured
AGENT_TOOLS: set[str] = {
    # File reading tools
    "readFile",
    "readCode",
    "readMultipleFiles",
    # File writing tools
    "strReplace",
    "fsWrite",
    "fsAppend",
    "editCode",
    # File system tools
    "deleteFile",
    "listDirectory",
    # Search and analysis tools
    "grepSearch",
    "fileSearch",
    "getDiagnostics",
    # Additional tools
    "semanticRename",
    "smartRelocate",
}

# Registry of wrapped tools (tool_name -> wrapped_function)
_wrapped_tools: dict[str, Callable[..., Any]] = {}


def register_agent_tool(tool_name: str) -> None:
    """Register a tool as an agent tool that should be captured.

    Args:
        tool_name: Name of the tool to register

    """
    AGENT_TOOLS.add(tool_name)
    logger.debug(f"Registered agent tool: {tool_name}")


def unregister_agent_tool(tool_name: str) -> None:
    """Unregister a tool from agent tool capture.

    Args:
        tool_name: Name of the tool to unregister

    """
    AGENT_TOOLS.discard(tool_name)
    logger.debug(f"Unregistered agent tool: {tool_name}")


def is_agent_tool(tool_name: str) -> bool:
    """Check if a tool is registered as an agent tool.

    Args:
        tool_name: Name of the tool

    Returns:
        True if tool is registered, False otherwise

    """
    return tool_name in AGENT_TOOLS


def get_agent_tools() -> set[str]:
    """Get all registered agent tools.

    Returns:
        Set of agent tool names

    """
    return AGENT_TOOLS.copy()


def register_wrapped_tool(tool_name: str, wrapped_function: Callable[..., Any]) -> None:
    """Register a wrapped tool function.

    Args:
        tool_name: Name of the tool
        wrapped_function: Wrapped tool function

    """
    _wrapped_tools[tool_name] = wrapped_function
    logger.debug(f"Registered wrapped tool: {tool_name}")


def get_wrapped_tool(tool_name: str) -> Callable[..., Any] | None:
    """Get a wrapped tool function.

    Args:
        tool_name: Name of the tool

    Returns:
        Wrapped tool function, or None if not registered

    """
    return _wrapped_tools.get(tool_name)


def get_all_wrapped_tools() -> dict[str, Callable[..., Any]]:
    """Get all wrapped tool functions.

    Returns:
        Dictionary of tool_name -> wrapped_function

    """
    return _wrapped_tools.copy()


def clear_wrapped_tools() -> None:
    """Clear all wrapped tool registrations."""
    _wrapped_tools.clear()
    logger.debug("Cleared all wrapped tool registrations")
