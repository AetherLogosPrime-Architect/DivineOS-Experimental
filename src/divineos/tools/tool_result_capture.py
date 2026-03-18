"""
Tool Result Capture Module — Middleware to capture tool execution results.

This module provides decorators and wrappers to automatically emit TOOL_RESULT
events when tools are executed. It can be used to wrap tool execution functions
or as a middleware in the IDE.
"""

import time
import uuid
from typing import Any, Callable, Optional
from functools import wraps
from loguru import logger

from divineos.event.event_emission import emit_tool_result


def capture_tool_result(tool_name: str):
    """
    Decorator to automatically emit TOOL_RESULT events when a tool completes.

    Usage:
        @capture_tool_result("readFile")
        def my_tool_function(path: str) -> str:
            return open(path).read()

    Args:
        tool_name: Name of the tool being wrapped

    Returns:
        Decorator function
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            tool_use_id = str(uuid.uuid4())
            start_time = time.time()

            try:
                # Execute the tool
                result = func(*args, **kwargs)
                duration_ms = int((time.time() - start_time) * 1000)

                # Convert result to string if needed
                result_str = str(result) if not isinstance(result, str) else result

                # Emit TOOL_RESULT event
                try:
                    event_id = emit_tool_result(
                        tool_name=tool_name,
                        tool_use_id=tool_use_id,
                        result=result_str,
                        duration_ms=duration_ms,
                        failed=False,
                    )
                    logger.debug(f"Emitted TOOL_RESULT for {tool_name}: {event_id}")
                except Exception as e:
                    logger.warning(f"Failed to emit TOOL_RESULT for {tool_name}: {e}")

                return result

            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)
                error_msg = str(e)

                # Emit TOOL_RESULT event with failure flag
                try:
                    event_id = emit_tool_result(
                        tool_name=tool_name,
                        tool_use_id=tool_use_id,
                        result=error_msg,
                        duration_ms=duration_ms,
                        failed=True,
                        error_message=error_msg,
                    )
                    logger.debug(f"Emitted TOOL_RESULT (failed) for {tool_name}: {event_id}")
                except Exception as emit_error:
                    logger.warning(f"Failed to emit TOOL_RESULT for {tool_name}: {emit_error}")

                # Re-raise the original exception
                raise

        return wrapper

    return decorator


def emit_tool_result_for_execution(
    tool_name: str,
    result: str,
    duration_ms: int,
    failed: bool = False,
    error_message: Optional[str] = None,
) -> Optional[str]:
    """
    Manually emit a TOOL_RESULT event for a tool execution.

    This can be called directly when tool execution is captured elsewhere
    (e.g., in IDE hooks or middleware).

    Args:
        tool_name: Name of the tool
        result: The result output from the tool
        duration_ms: Execution duration in milliseconds
        failed: Whether the tool execution failed
        error_message: Error message if failed=True

    Returns:
        Event ID if successful, None if emission failed
    """
    try:
        tool_use_id = str(uuid.uuid4())
        event_id = emit_tool_result(
            tool_name=tool_name,
            tool_use_id=tool_use_id,
            result=result,
            duration_ms=duration_ms,
            failed=failed,
            error_message=error_message,
        )
        logger.debug(f"Emitted TOOL_RESULT for {tool_name}: {event_id}")
        return event_id
    except Exception as e:
        logger.error(f"Failed to emit TOOL_RESULT for {tool_name}: {e}")
        return None
