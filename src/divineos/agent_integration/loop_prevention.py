"""
Loop Prevention Layer for Agent Integration

Prevents infinite loops by marking internal operations and excluding them
from event capture. Uses thread-local storage to maintain operation context.
"""

import threading
from contextlib import contextmanager
from typing import Set, Optional

from divineos.agent_integration.logging_config import loop_prevention_logger as logger
from divineos.agent_integration.types import INTERNAL_TOOLS


# Thread-local storage for operation context
_operation_context = threading.local()


def initialize_loop_prevention() -> None:
    """Initialize loop prevention system."""
    logger.debug("Initializing loop prevention")
    _operation_context.internal_flag = False
    _operation_context.operation_stack = []


def shutdown_loop_prevention() -> None:
    """Shutdown loop prevention system."""
    logger.debug("Shutting down loop prevention")
    if hasattr(_operation_context, "operation_stack"):
        _operation_context.operation_stack.clear()
    _operation_context.internal_flag = False


@contextmanager
def mark_internal_operation():
    """
    Context manager to mark operations as internal.

    Operations marked as internal will not be captured as tool calls,
    preventing recursive capture of OS operations.

    Usage:
        with mark_internal_operation():
            # This operation will not be captured
            emit_tool_call(...)
    """
    # Save previous state
    previous_flag = getattr(_operation_context, "internal_flag", False)

    try:
        # Set internal flag
        _operation_context.internal_flag = True
        yield
    finally:
        # Restore previous state
        _operation_context.internal_flag = previous_flag


def is_internal_operation() -> bool:
    """
    Check if current operation is marked as internal.

    Returns:
        True if operation is marked as internal, False otherwise
    """
    return getattr(_operation_context, "internal_flag", False)


def should_capture_tool(tool_name: str) -> bool:
    """
    Check if tool should be captured.

    A tool should NOT be captured if:
    1. Current operation is marked as internal
    2. Tool is in the internal tools list
    3. Tool is already in the operation stack (recursion)

    Args:
        tool_name: Name of the tool

    Returns:
        True if tool should be captured, False otherwise
    """
    # Check if internal operation flag is set
    if is_internal_operation():
        logger.debug(f"Skipping capture for {tool_name}: internal operation flag set")
        return False

    # Check if tool is in internal tools list
    if tool_name in INTERNAL_TOOLS:
        logger.debug(f"Skipping capture for {tool_name}: tool is internal")
        return False

    # Check if tool is already in operation stack (recursion detection)
    stack = getattr(_operation_context, "operation_stack", [])
    if tool_name in stack:
        logger.warning(f"Recursive capture detected for {tool_name}. Operation stack: {stack}")
        return False

    return True


def push_operation(tool_name: str) -> None:
    """
    Push an operation onto the operation stack.

    Args:
        tool_name: Name of the tool being executed
    """
    if not hasattr(_operation_context, "operation_stack"):
        _operation_context.operation_stack = []

    _operation_context.operation_stack.append(tool_name)
    logger.debug(f"Pushed {tool_name} onto operation stack: {_operation_context.operation_stack}")


def pop_operation() -> Optional[str]:
    """
    Pop an operation from the operation stack.

    Returns:
        Name of the popped operation, or None if stack is empty
    """
    if not hasattr(_operation_context, "operation_stack"):
        _operation_context.operation_stack = []

    if _operation_context.operation_stack:
        tool_name = _operation_context.operation_stack.pop()
        logger.debug(
            f"Popped {tool_name} from operation stack: {_operation_context.operation_stack}"
        )
        return tool_name

    return None


def get_operation_stack() -> list:
    """
    Get the current operation stack.

    Returns:
        List of tool names currently in the operation stack
    """
    if not hasattr(_operation_context, "operation_stack"):
        _operation_context.operation_stack = []

    return _operation_context.operation_stack.copy()


def clear_operation_stack() -> None:
    """Clear the operation stack."""
    if hasattr(_operation_context, "operation_stack"):
        _operation_context.operation_stack.clear()
    logger.debug("Operation stack cleared")


def get_internal_tools() -> Set[str]:
    """
    Get the set of internal tools that should not be captured.

    Returns:
        Set of internal tool names
    """
    return INTERNAL_TOOLS.copy()


def add_internal_tool(tool_name: str) -> None:
    """
    Add a tool to the internal tools list.

    Args:
        tool_name: Name of the tool to mark as internal
    """
    INTERNAL_TOOLS.add(tool_name)
    logger.debug(f"Added {tool_name} to internal tools list")


def remove_internal_tool(tool_name: str) -> None:
    """
    Remove a tool from the internal tools list.

    Args:
        tool_name: Name of the tool to remove from internal list
    """
    INTERNAL_TOOLS.discard(tool_name)
    logger.debug(f"Removed {tool_name} from internal tools list")
