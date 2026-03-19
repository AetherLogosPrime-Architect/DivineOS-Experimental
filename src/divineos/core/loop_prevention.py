"""Loop Prevention Module — Prevents infinite loops in event capture.

This module provides mechanisms to mark operations as internal and prevent
recursive capture of the enforcement system's own operations.

Key Features:
- Thread-local storage for internal operation context
- Internal tool detection
- Recursive capture prevention
- Context manager for marking internal operations
- Operation stack tracking for recursion detection
"""

import threading
from contextlib import contextmanager
from typing import Any, Iterator

from loguru import logger

# Thread-local storage for internal operation context
_internal_context = threading.local()


def _get_internal_flag() -> bool:
    """Get the internal operation flag from thread-local storage."""
    return getattr(_internal_context, "is_internal", False)


def _set_internal_flag(value: bool) -> None:
    """Set the internal operation flag in thread-local storage."""
    _internal_context.is_internal = value


@contextmanager
def mark_internal_operation() -> Iterator[None]:
    """Context manager to mark operations as internal.

    Operations marked as internal will not be captured as events.
    This prevents infinite loops where the enforcement system captures
    its own operations.

    Usage:
        with mark_internal_operation():
            # This operation will not be captured
            ledger.log_event(...)

    Yields:
        None

    Requirements:
        - Requirement 11.5: Use a flag to mark operations as internal

    """
    old_value = _get_internal_flag()
    _set_internal_flag(True)
    try:
        yield
    finally:
        _set_internal_flag(old_value)


def is_internal_operation() -> bool:
    """Check if the current operation is marked as internal.

    Returns:
        bool: True if current operation is internal, False otherwise

    Requirements:
        - Requirement 11.1: Check if event emission should be captured
        - Requirement 11.2: Check if ledger calls should be captured
        - Requirement 11.3: Check if logging should be captured
        - Requirement 11.4: Check if file access should be captured

    """
    return _get_internal_flag()


def get_internal_tools() -> set[str]:
    """Get the set of internal tools that should not be captured.

    Internal tools are those that are part of the enforcement system itself
    and should not be captured as TOOL_CALL or TOOL_RESULT events.

    Returns:
        Set[str]: Set of internal tool names

    Requirements:
        - Requirement 11.2: Ledger calls should not be captured
        - Requirement 11.3: Logging should not be captured
        - Requirement 11.4: File access should not be captured

    """
    return {
        # Ledger operations
        "log_event",
        "get_events",
        "search_events",
        "get_recent_context",
        "count_events",
        "verify_event_hash",
        "get_verified_events",
        "verify_all_events",
        "clean_corrupted_events",
        "export_to_markdown",
        # Event emission operations
        "emit_user_input",
        "emit_tool_call",
        "emit_tool_result",
        "emit_session_end",
        "emit_explanation",
        # Session management operations
        "initialize_session",
        "get_current_session_id",
        "end_session",
        "clear_session",
        "is_session_active",
        "get_or_create_session_id",
        # Logging operations
        "logger",
        "log",
        "debug",
        "info",
        "warning",
        "error",
        # File operations for session management
        "read_session_file",
        "write_session_file",
        "clear_session_file",
        # Loop prevention operations
        "mark_internal_operation",
        "is_internal_operation",
        "should_capture_tool",
        # Enforcement verifier operations
        "verify_enforcement",
        "check_event_capture_rate",
        "detect_missing_events",
        "generate_enforcement_report",
    }


def should_capture_tool(tool_name: str) -> bool:
    """Check if a tool should be captured as a TOOL_CALL event.

    A tool should NOT be captured if:
    1. The current operation is marked as internal
    2. The tool is in the internal tools list

    Args:
        tool_name: Name of the tool to check

    Returns:
        bool: True if tool should be captured, False otherwise

    Requirements:
        - Requirement 11.1: Do not capture event emissions
        - Requirement 11.2: Do not capture ledger calls
        - Requirement 11.3: Do not capture logging
        - Requirement 11.4: Do not capture file access
        - Requirement 11.5: Use flag to exclude internal operations
        - Requirement 11.6: Do not emit events for internal tools

    """
    # If we're in an internal operation, don't capture
    if is_internal_operation():
        logger.debug(f"Skipping capture of {tool_name} (internal operation)")
        return False

    # If the tool is in the internal tools list, don't capture
    if tool_name in get_internal_tools():
        logger.debug(f"Skipping capture of {tool_name} (internal tool)")
        return False

    # Otherwise, capture the tool
    return True


def detect_recursive_capture(tool_name: str) -> bool:
    """Detect if a tool call would result in recursive capture.

    This is a safety check to detect if the enforcement system is
    trying to capture its own operations.

    Args:
        tool_name: Name of the tool being called

    Returns:
        bool: True if recursive capture detected, False otherwise

    Requirements:
        - Requirement 11.7: Detect recursive capture and log warning

    """
    if is_internal_operation() and tool_name not in get_internal_tools():
        logger.warning(
            f"Potential recursive capture detected: {tool_name} called during internal operation",
        )
        return True

    return False


def initialize_loop_prevention() -> None:
    """Initialize loop prevention system.

    Sets up thread-local storage for operation context tracking.
    """
    logger.debug("Initializing loop prevention")
    _internal_context.internal_flag = False
    _internal_context.operation_stack = []


def shutdown_loop_prevention() -> None:
    """Shutdown loop prevention system.

    Cleans up thread-local storage and operation stack.
    """
    logger.debug("Shutting down loop prevention")
    if hasattr(_internal_context, "operation_stack"):
        _internal_context.operation_stack.clear()
    _internal_context.internal_flag = False


def push_operation(tool_name: str) -> None:
    """Push an operation onto the operation stack.

    Used to track the call stack and detect recursive operations.

    Args:
        tool_name: Name of the tool being executed

    """
    if not hasattr(_internal_context, "operation_stack"):
        _internal_context.operation_stack = []

    _internal_context.operation_stack.append(tool_name)
    logger.debug(f"Pushed {tool_name} onto operation stack: {_internal_context.operation_stack}")


def pop_operation() -> str | None:
    """Pop an operation from the operation stack.

    Returns:
        Name of the popped operation, or None if stack is empty

    """
    if not hasattr(_internal_context, "operation_stack"):
        _internal_context.operation_stack = []

    if _internal_context.operation_stack:
        tool_name: str | None = _internal_context.operation_stack.pop()
        logger.debug(
            f"Popped {tool_name} from operation stack: {_internal_context.operation_stack}",
        )
        return tool_name

    return None


def get_operation_stack() -> list[Any]:
    """Get the current operation stack.

    Returns:
        List of tool names currently in the operation stack

    """
    if not hasattr(_internal_context, "operation_stack"):
        _internal_context.operation_stack = []

    return list(_internal_context.operation_stack)


def clear_operation_stack() -> None:
    """Clear the operation stack."""
    if hasattr(_internal_context, "operation_stack"):
        _internal_context.operation_stack.clear()
    logger.debug("Operation stack cleared")


def add_internal_tool(tool_name: str) -> None:
    """Add a tool to the internal tools list.

    Args:
        tool_name: Name of the tool to mark as internal

    """
    internal_tools = get_internal_tools()
    internal_tools.add(tool_name)
    logger.debug(f"Added {tool_name} to internal tools list")


def remove_internal_tool(tool_name: str) -> None:
    """Remove a tool from the internal tools list.

    Args:
        tool_name: Name of the tool to remove from internal list

    """
    internal_tools = get_internal_tools()
    internal_tools.discard(tool_name)
    logger.debug(f"Removed {tool_name} from internal tools list")
