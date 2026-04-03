"""Tool Execution Wrapper Module — Wraps tool execution to capture events.

This module provides functions to wrap tool execution with automatic
TOOL_CALL and TOOL_RESULT event capture. It is the canonical tool capture
system for DivineOS, consolidating all tool capture implementations.

Key Features:
- Intercept tool execution before and after
- Emit TOOL_CALL events before execution
- Measure execution duration
- Emit TOOL_RESULT events after execution
- Handle tool failures with error messages
- Preserve original tool behavior and exceptions
- Skip internal tools to prevent infinite loops
- Decorator-based tool wrapping

IDE integration and unified capture live in divineos.core.tool_capture.

Requirements:
- Requirement 2.1-2.8: Capture TOOL_CALL events
- Requirement 3.1-3.9: Capture TOOL_RESULT events
- Requirement 6.1-6.7: Wrap tool execution transparently
"""

import json
import time
import uuid
from collections.abc import Callable
from functools import wraps
from typing import Any
import sqlite3

from loguru import logger

from divineos.core.guardrails import GuardrailConfig, GuardrailState
from divineos.core.loop_prevention import should_capture_tool
from divineos.event.event_emission import emit_tool_call, emit_tool_result

# Singleton guardrail state for the session
_guardrail_state = GuardrailState()


def get_guardrail_state() -> GuardrailState:
    """Get the current session's guardrail state."""
    return _guardrail_state


def reset_guardrails(config: GuardrailConfig | None = None) -> None:
    """Reset guardrails for a new session."""
    global _guardrail_state  # noqa: PLW0603
    _guardrail_state = GuardrailState(config)


def get_tool_input_string(tool_input: dict[str, Any]) -> str:
    """Convert tool input to string for logging.

    Args:
        tool_input: Tool input parameters as dictionary

    Returns:
        str: JSON string representation of tool input

    Requirements:
        - Requirement 2.3: Include complete input parameters as JSON

    """
    try:
        # Serialize to JSON
        json_str = json.dumps(tool_input, default=str)

        # Truncate if too large (1MB limit)
        if len(json_str) > 1000000:
            json_str = json_str[:1000000] + "... [truncated]"

        return json_str
    except _TW_ERRORS as e:
        logger.warning(f"Failed to serialize tool input: {e}")
        return str(tool_input)


def get_tool_result_string(result: Any) -> str:
    """Convert tool result to string for logging.

    Args:
        result: Tool result (can be any type)

    Returns:
        str: String representation of tool result

    Requirements:
        - Requirement 3.4: Include complete result output (not truncated)

    """
    try:
        # If result is already a string, use it
        if isinstance(result, str):
            result_str = result
        else:
            # Try to serialize to JSON
            result_str = json.dumps(result, default=str)

        # Truncate if too large (1MB limit)
        if len(result_str) > 1000000:
            result_str = result_str[:1000000] + "... [truncated]"

        return result_str
    except _TW_ERRORS as e:
        logger.warning(f"Failed to serialize tool result: {e}")
        return str(result)


def wrap_tool_execution(
    tool_name: str,
    tool_func: Callable[..., Any],
    tool_use_id: str | None = None,
) -> Callable[..., Any]:
    """Create a wrapper for tool execution that captures events.

    This wrapper:
    1. Checks if tool should be captured (not internal)
    2. Emits TOOL_CALL event before execution
    3. Measures execution duration
    4. Executes the tool
    5. Emits TOOL_RESULT event after execution
    6. Preserves original return value and exceptions

    Error Handling:
    - Catches validation errors during event emission
    - Catches ledger errors during storage
    - Logs errors without crashing
    - Preserves original tool exceptions
    - Ensures TOOL_RESULT is always emitted (even on error)

    Args:
        tool_name: Name of the tool being wrapped
        tool_func: The tool function to wrap
        tool_use_id: Optional unique ID for this tool use (generates if not provided)

    Returns:
        Callable: Wrapped function that captures events

    Requirements:
        - Requirement 2.1-2.8: Emit TOOL_CALL events
        - Requirement 3.1-3.9: Emit TOOL_RESULT events
        - Requirement 6.1-6.7: Preserve tool behavior
        - Requirement 10.1-10.6: Handle errors gracefully

    """

    @wraps(tool_func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Check if tool should be captured
        if not should_capture_tool(tool_name):
            logger.debug(f"Skipping event capture for internal tool: {tool_name}")
            return tool_func(*args, **kwargs)

        # Guardrail checks — warn on violations but don't block
        violation = _guardrail_state.check_tool_call(tool_name)
        if violation:
            logger.warning(f"Guardrail violation: {violation.detail}")
        _guardrail_state.record_tool_call(tool_name)

        # Generate tool_use_id if not provided
        use_id = tool_use_id or str(uuid.uuid4())

        # Prepare tool input
        tool_input = {
            "args": args,
            "kwargs": kwargs,
        }

        # Emit TOOL_CALL event with error handling
        try:
            logger.debug(f"Emitting TOOL_CALL event for {tool_name}")
            emit_tool_call(
                tool_name=tool_name,
                tool_input=tool_input,
                tool_use_id=use_id,
            )
            logger.debug(f"TOOL_CALL event emitted successfully for {tool_name}")
        except ValueError as e:
            logger.error(f"Validation error during TOOL_CALL event emission: {e}")
            logger.warning(f"Continuing without TOOL_CALL event for {tool_name}")
        except _TW_ERRORS as e:
            logger.error(f"Failed to emit TOOL_CALL event for {tool_name}: {e}", exc_info=True)
            logger.warning(f"Continuing without TOOL_CALL event for {tool_name}")

        # Measure execution time
        start_time = time.time()
        result = None
        failed = False
        error_message = None

        try:
            # Execute the tool
            result = tool_func(*args, **kwargs)
            logger.debug(f"Tool {tool_name} executed successfully")
            return result

        except Exception as e:
            # Tool execution failed — must catch all since tool_func is arbitrary code
            failed = True
            error_message = str(e)
            logger.error(f"Tool {tool_name} failed: {error_message}", exc_info=True)

            # Emit TOOL_RESULT event with error
            duration_ms = int((time.time() - start_time) * 1000)
            try:
                emit_tool_result(
                    tool_name=tool_name,
                    tool_use_id=use_id,
                    result="",
                    duration_ms=duration_ms,
                    failed=True,
                    error_message=error_message,
                )
                logger.debug(f"TOOL_RESULT event emitted for failed tool {tool_name}")
            except ValueError as e2:
                logger.error(f"Validation error during TOOL_RESULT event emission: {e2}")
                logger.warning(f"Continuing without TOOL_RESULT event for {tool_name}")
            except _TW_ERRORS as e2:
                logger.error(
                    f"Failed to emit TOOL_RESULT event for {tool_name}: {e2}",
                    exc_info=True,
                )
                logger.warning(f"Continuing without TOOL_RESULT event for {tool_name}")

            # Re-raise the original exception
            raise

        finally:
            # Emit TOOL_RESULT event (if not already emitted due to error)
            if not failed:
                duration_ms = int((time.time() - start_time) * 1000)
                try:
                    result_str = get_tool_result_string(result)
                    emit_tool_result(
                        tool_name=tool_name,
                        tool_use_id=use_id,
                        result=result_str,
                        duration_ms=duration_ms,
                        failed=False,
                    )
                    logger.debug(f"TOOL_RESULT event emitted successfully for {tool_name}")
                except ValueError as e:
                    logger.error(f"Validation error during TOOL_RESULT event emission: {e}")
                    logger.warning(f"Continuing without TOOL_RESULT event for {tool_name}")
                except _TW_ERRORS as e:
                    logger.error(
                        f"Failed to emit TOOL_RESULT event for {tool_name}: {e}",
                        exc_info=True,
                    )
                    logger.warning(f"Continuing without TOOL_RESULT event for {tool_name}")

    return wrapper


def is_internal_tool(tool_name: str) -> bool:
    """Check if a tool is internal and should not be captured.

    Args:
        tool_name: Name of the tool to check

    Returns:
        bool: True if tool is internal, False otherwise

    Requirements:
        - Requirement 11.6: Do not emit events for internal tools

    """
    return not should_capture_tool(tool_name)


def create_tool_wrapper_decorator(
    tool_name: str,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Create a decorator to wrap a tool function.

    Usage:
        @create_tool_wrapper_decorator("readFile")
        def read_file(path: str) -> str:
            # implementation
            pass

    Args:
        tool_name: Name of the tool being decorated

    Returns:
        Callable: Decorator function

    Requirements:
        - Requirement 6.1-6.7: Wrap tool execution transparently

    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        return wrap_tool_execution(tool_name, func)

    return decorator


# --- Backward-compatible re-exports from tool_capture ---
# These items were extracted to divineos.core.tool_capture but are
# re-exported here so existing imports keep working.
from divineos.core.tool_capture import (  # noqa: E402
    IDEToolExecutor as IDEToolExecutor,
    UnifiedToolCapture as UnifiedToolCapture,
    capture_tool_execution as capture_tool_execution,
    emit_tool_call_for_ide as emit_tool_call_for_ide,
    emit_tool_result_for_ide as emit_tool_result_for_ide,
    get_ide_tool_executor as get_ide_tool_executor,
    get_unified_capture as get_unified_capture,
)

_TW_ERRORS = (
    ImportError,
    sqlite3.OperationalError,
    OSError,
    KeyError,
    TypeError,
    ValueError,
    json.JSONDecodeError,
)
