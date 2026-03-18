"""
Tool Event Wrapper - Automatically emit TOOL_CALL and TOOL_RESULT events.

This module provides decorators and wrappers to automatically capture tool
execution events without requiring manual calls.
"""

import functools
import time
from typing import Any, Callable
from loguru import logger

from divineos.event.event_emission import emit_tool_call, emit_tool_result


def capture_tool_execution(tool_name: str):
    """
    Decorator to automatically emit TOOL_CALL and TOOL_RESULT events.

    Usage:
        @capture_tool_execution("readFile")
        def my_tool(path: str) -> str:
            return open(path).read()
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Emit TOOL_CALL
            tool_input = {
                "args": args,
                "kwargs": kwargs,
            }

            try:
                tool_call_id = emit_tool_call(
                    tool_name=tool_name,
                    tool_input=tool_input,
                )
                logger.debug(f"Emitted TOOL_CALL: {tool_call_id}")
            except Exception as e:
                logger.warning(f"Failed to emit TOOL_CALL: {e}")
                tool_call_id = None

            # Execute tool
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration_ms = int((time.time() - start_time) * 1000)
                failed = False
                error_message = None
                result_str = str(result)[:5000]
            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)
                failed = True
                error_message = str(e)
                result_str = f"Error: {error_message}"
                result = None

            # Emit TOOL_RESULT
            try:
                tool_result_id = emit_tool_result(
                    tool_name=tool_name,
                    tool_use_id=tool_call_id or "unknown",
                    result=result_str,
                    duration_ms=duration_ms,
                    failed=failed,
                    error_message=error_message,
                )
                logger.debug(f"Emitted TOOL_RESULT: {tool_result_id}")
            except Exception as e:
                logger.warning(f"Failed to emit TOOL_RESULT: {e}")

            # Re-raise if tool failed
            if failed:
                raise Exception(error_message)

            return result

        return wrapper

    return decorator
