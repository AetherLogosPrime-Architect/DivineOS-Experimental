"""
Tool Execution Wrapper Module — Wraps tool execution to capture events.

This module provides functions to wrap tool execution with automatic
TOOL_CALL and TOOL_RESULT event capture.

Key Features:
- Intercept tool execution before and after
- Emit TOOL_CALL events before execution
- Measure execution duration
- Emit TOOL_RESULT events after execution
- Handle tool failures with error messages
- Preserve original tool behavior and exceptions
- Skip internal tools to prevent infinite loops

Requirements:
- Requirement 2.1-2.8: Capture TOOL_CALL events
- Requirement 3.1-3.9: Capture TOOL_RESULT events
- Requirement 6.1-6.7: Wrap tool execution transparently
"""

import time
import json
import uuid
from typing import Any, Callable, Dict, Optional
from functools import wraps
from loguru import logger

from divineos.core.loop_prevention import should_capture_tool
from divineos.event.event_emission import emit_tool_call, emit_tool_result


def get_tool_input_string(tool_input: Dict[str, Any]) -> str:
    """
    Convert tool input to string for logging.

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
    except Exception as e:
        logger.warning(f"Failed to serialize tool input: {e}")
        return str(tool_input)


def get_tool_result_string(result: Any) -> str:
    """
    Convert tool result to string for logging.

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
    except Exception as e:
        logger.warning(f"Failed to serialize tool result: {e}")
        return str(result)


def wrap_tool_execution(
    tool_name: str,
    tool_func: Callable,
    tool_use_id: Optional[str] = None,
) -> Callable:
    """
    Create a wrapper for tool execution that captures events.

    This wrapper:
    1. Checks if tool should be captured (not internal)
    2. Emits TOOL_CALL event before execution
    3. Measures execution duration
    4. Executes the tool
    5. Emits TOOL_RESULT event after execution
    6. Preserves original return value and exceptions

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
    """

    @wraps(tool_func)
    def wrapper(*args, **kwargs) -> Any:
        # Check if tool should be captured
        if not should_capture_tool(tool_name):
            logger.debug(f"Skipping event capture for internal tool: {tool_name}")
            return tool_func(*args, **kwargs)

        # Generate tool_use_id if not provided
        use_id = tool_use_id or str(uuid.uuid4())

        # Prepare tool input
        tool_input = {
            "args": args,
            "kwargs": kwargs,
        }

        try:
            # Emit TOOL_CALL event
            logger.debug(f"Emitting TOOL_CALL event for {tool_name}")
            emit_tool_call(
                tool_name=tool_name,
                tool_input=tool_input,
                tool_use_id=use_id,
            )
        except Exception as e:
            logger.error(f"Failed to emit TOOL_CALL event: {e}")
            # Continue execution even if event capture fails

        # Measure execution time
        start_time = time.time()
        result = None
        failed = False
        error_message = None

        try:
            # Execute the tool
            result = tool_func(*args, **kwargs)
            return result

        except Exception as e:
            # Tool execution failed
            failed = True
            error_message = str(e)
            logger.error(f"Tool {tool_name} failed: {error_message}")

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
            except Exception as e2:
                logger.error(f"Failed to emit TOOL_RESULT event: {e2}")

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
                except Exception as e:
                    logger.error(f"Failed to emit TOOL_RESULT event: {e}")
                    # Continue execution even if event capture fails

    return wrapper


def is_internal_tool(tool_name: str) -> bool:
    """
    Check if a tool is internal and should not be captured.

    Args:
        tool_name: Name of the tool to check

    Returns:
        bool: True if tool is internal, False otherwise

    Requirements:
        - Requirement 11.6: Do not emit events for internal tools
    """
    return not should_capture_tool(tool_name)


def create_tool_wrapper_decorator(tool_name: str) -> Callable:
    """
    Create a decorator to wrap a tool function.

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

    def decorator(func: Callable) -> Callable:
        return wrap_tool_execution(tool_name, func)

    return decorator
