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
- IDE tool executor for IDE integration
- Decorator-based tool wrapping
- Manual event emission for workarounds
- Unified tool capture with singleton pattern
- Thread-safe capture operations
- Result truncation for large outputs

Requirements:
- Requirement 2.1-2.8: Capture TOOL_CALL events
- Requirement 3.1-3.9: Capture TOOL_RESULT events
- Requirement 6.1-6.7: Wrap tool execution transparently
"""

import json
import os
import threading
import time
import uuid
from collections.abc import Callable
from functools import wraps
from typing import Any

from loguru import logger

from divineos.core.error_handling import (
    EventCaptureError,
    handle_error,
)
from divineos.core.guardrails import GuardrailConfig, GuardrailState
from divineos.core.loop_prevention import should_capture_tool
from divineos.core.session_manager import get_or_create_session_id
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
    except Exception as e:
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
    except Exception as e:
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
        except Exception as e:
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
            # Tool execution failed
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
            except Exception as e2:
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
                except Exception as e:
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


class IDEToolExecutor:
    """Middleware for IDE tool execution that captures events.

    This class provides a unified interface for IDE tools to emit
    TOOL_CALL and TOOL_RESULT events.

    Usage:
        executor = IDEToolExecutor()
        result = executor.execute_tool("readFile", {"path": "file.py"})
    """

    def __init__(self) -> None:
        """Initialize the IDE tool executor."""
        self.active_tools: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()

    def start_tool_execution(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        tool_use_id: str | None = None,
    ) -> str:
        """Record the start of a tool execution and emit TOOL_CALL event.

        Args:
            tool_name: Name of the tool being executed
            tool_input: Input parameters for the tool
            tool_use_id: Optional unique ID for this tool use

        Returns:
            tool_use_id: The ID for this tool execution (for later reference)

        """
        if tool_use_id is None:
            tool_use_id = str(uuid.uuid4())

        with self._lock:
            # Record tool execution start
            self.active_tools[tool_use_id] = {
                "tool_name": tool_name,
                "tool_input": tool_input,
                "start_time": time.time(),
                "tool_use_id": tool_use_id,
            }

        # Emit TOOL_CALL event
        try:
            event_id = emit_tool_call(
                tool_name=tool_name,
                tool_input=tool_input,
                tool_use_id=tool_use_id,
            )
            logger.debug(f"Emitted TOOL_CALL for {tool_name}: {event_id}")
        except ValueError as e:
            logger.error(f"Validation error during TOOL_CALL event emission: {e}")
        except Exception as e:
            logger.error(f"Failed to emit TOOL_CALL event for {tool_name}: {e}", exc_info=True)

        return tool_use_id

    def end_tool_execution(
        self,
        tool_use_id: str,
        result: str,
        failed: bool = False,
        error_message: str | None = None,
    ) -> str | None:
        """Record the end of a tool execution and emit TOOL_RESULT event.

        Args:
            tool_use_id: The ID returned from start_tool_execution
            result: The result output from the tool
            failed: Whether the tool execution failed
            error_message: Error message if failed=True

        Returns:
            event_id: The ID of the emitted TOOL_RESULT event, or None if failed

        """
        with self._lock:
            if tool_use_id not in self.active_tools:
                logger.warning(f"Tool execution {tool_use_id} not found in active tools")
                return None

            tool_info = self.active_tools.pop(tool_use_id)

        duration_ms = int((time.time() - tool_info["start_time"]) * 1000)

        # Emit TOOL_RESULT event
        try:
            event_id = emit_tool_result(
                tool_name=tool_info["tool_name"],
                tool_use_id=tool_use_id,
                result=result,
                duration_ms=duration_ms,
                failed=failed,
                error_message=error_message,
            )
            logger.debug(f"Emitted TOOL_RESULT for {tool_info['tool_name']}: {event_id}")
            return event_id
        except ValueError as e:
            logger.error(f"Validation error during TOOL_RESULT event emission: {e}")
            return None
        except Exception as e:
            logger.error(
                f"Failed to emit TOOL_RESULT event for {tool_info['tool_name']}: {e}",
                exc_info=True,
            )
            return None

    def execute_tool(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        tool_function: Callable[..., Any],
        tool_use_id: str | None = None,
    ) -> Any:
        """Execute a tool and automatically capture TOOL_CALL and TOOL_RESULT events.

        Args:
            tool_name: Name of the tool
            tool_input: Input parameters for the tool
            tool_function: The actual tool function to execute
            tool_use_id: Optional unique ID for this tool use

        Returns:
            The result from tool_function

        Raises:
            Exception: Re-raises any exception from tool_function

        """
        # Start tool execution and emit TOOL_CALL
        tool_use_id = self.start_tool_execution(tool_name, tool_input, tool_use_id)

        try:
            # Execute the tool
            result = tool_function(**tool_input)
            result_str = str(result) if not isinstance(result, str) else result

            # End tool execution and emit TOOL_RESULT
            self.end_tool_execution(tool_use_id, result_str, failed=False)

            return result

        except Exception as e:
            # End tool execution with failure and emit TOOL_RESULT
            error_msg = str(e)
            self.end_tool_execution(tool_use_id, error_msg, failed=True, error_message=error_msg)
            raise


# Global executor instance
_executor: IDEToolExecutor | None = None
_executor_lock = threading.Lock()


def get_ide_tool_executor() -> IDEToolExecutor:
    """Get the global IDE tool executor instance."""
    global _executor
    if _executor is None:
        with _executor_lock:
            if _executor is None:
                _executor = IDEToolExecutor()
    return _executor


def emit_tool_call_for_ide(
    tool_name: str,
    tool_input: dict[str, Any],
    tool_use_id: str | None = None,
) -> str:
    """Emit a TOOL_CALL event for IDE tool execution.

    This is called by the IDE when a tool is about to be executed.

    Args:
        tool_name: Name of the tool
        tool_input: Input parameters
        tool_use_id: Optional unique ID

    Returns:
        tool_use_id: The ID for this tool execution

    """
    executor = get_ide_tool_executor()
    return executor.start_tool_execution(tool_name, tool_input, tool_use_id)


def emit_tool_result_for_ide(
    tool_use_id: str,
    result: str,
    failed: bool = False,
    error_message: str | None = None,
) -> str | None:
    """Emit a TOOL_RESULT event for IDE tool execution.

    This is called by the IDE when a tool has completed execution.

    Args:
        tool_use_id: The ID returned from emit_tool_call_for_ide
        result: The result output from the tool
        failed: Whether the tool execution failed
        error_message: Error message if failed=True

    Returns:
        event_id: The ID of the emitted TOOL_RESULT event

    """
    executor = get_ide_tool_executor()
    return executor.end_tool_execution(tool_use_id, result, failed, error_message)


class UnifiedToolCapture:
    """Unified tool capture system for both Kiro and MCP.

    This class provides a thread-safe singleton pattern for capturing tool
    executions from both Kiro IDE and MCP servers. It ensures consistent
    event emission and prevents duplicate captures.

    Features:
    - Thread-safe singleton pattern
    - Automatic session management
    - Consistent event emission
    - Error handling and logging
    - Result truncation for large outputs
    """

    def __init__(self) -> None:
        """Initialize the unified tool capture system."""
        self._lock = threading.RLock()
        self.session_id = os.environ.get("DIVINEOS_SESSION_ID")
        logger.info(f"UnifiedToolCapture initialized with session: {self.session_id}")

    def capture_tool_execution(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        result: Any,
        duration_ms: int,
        failed: bool = False,
        error_message: str | None = None,
    ) -> tuple[str | None, str | None]:
        """Capture a tool execution and emit TOOL_CALL and TOOL_RESULT events.

        Args:
            tool_name: Name of the tool (e.g., "readFile", "executePwsh")
            tool_input: Input parameters to the tool
            result: The result returned by the tool
            duration_ms: Execution duration in milliseconds
            failed: Whether the tool execution failed
            error_message: Error message if failed=True

        Returns:
            Tuple of (tool_call_event_id, tool_result_event_id)

        """
        with self._lock:
            tool_call_id = None
            tool_result_id = None

            try:
                # Get or create session ID
                session_id = self.session_id or get_or_create_session_id()

                # Emit TOOL_CALL event
                try:
                    tool_call_id = emit_tool_call(
                        tool_name=tool_name,
                        tool_input=tool_input,
                        session_id=session_id,
                    )
                    logger.debug(f"Emitted TOOL_CALL for {tool_name}: {tool_call_id}")
                except EventCaptureError as e:
                    handle_error(e, "emit_tool_call_unified", {"tool_name": tool_name})
                except Exception as e:
                    handle_error(e, "emit_tool_call_unified", {"tool_name": tool_name})

                # Convert result to string and truncate if needed
                result_str = str(result) if not isinstance(result, str) else result
                if len(result_str) > 5000:
                    result_str = result_str[:5000] + "... [truncated]"

                # Emit TOOL_RESULT event
                try:
                    tool_result_id = emit_tool_result(
                        tool_name=tool_name,
                        tool_use_id=tool_call_id or "unknown",
                        result=result_str,
                        duration_ms=duration_ms,
                        failed=failed,
                        error_message=error_message,
                        session_id=session_id,
                    )
                    logger.debug(f"Emitted TOOL_RESULT for {tool_name}: {tool_result_id}")
                except EventCaptureError as e:
                    handle_error(e, "emit_tool_result_unified", {"tool_name": tool_name})
                except Exception as e:
                    handle_error(e, "emit_tool_result_unified", {"tool_name": tool_name})

                return tool_call_id, tool_result_id

            except EventCaptureError as e:
                handle_error(e, "capture_tool_execution_unified", {"tool_name": tool_name})
                return None, None
            except Exception as e:
                handle_error(e, "capture_tool_execution_unified", {"tool_name": tool_name})
                return None, None


# Global unified capture instance
_unified_capture: UnifiedToolCapture | None = None
_capture_lock = threading.Lock()


def get_unified_capture() -> UnifiedToolCapture:
    """Get or create the global unified tool capture instance.

    Returns:
        UnifiedToolCapture: The global singleton instance

    """
    global _unified_capture
    if _unified_capture is None:
        with _capture_lock:
            if _unified_capture is None:
                _unified_capture = UnifiedToolCapture()
    return _unified_capture


def capture_tool_execution(
    tool_name: str,
    tool_input: dict[str, Any],
    result: Any,
    duration_ms: int,
    failed: bool = False,
    error_message: str | None = None,
) -> tuple[str | None, str | None]:
    """Convenience function to capture a tool execution.

    This function uses the global unified capture singleton to emit
    TOOL_CALL and TOOL_RESULT events for a tool execution.

    Args:
        tool_name: Name of the tool
        tool_input: Input parameters
        result: Tool result
        duration_ms: Execution duration in milliseconds
        failed: Whether execution failed
        error_message: Error message if failed

    Returns:
        Tuple of (tool_call_event_id, tool_result_event_id)

    """
    capture = get_unified_capture()
    return capture.capture_tool_execution(
        tool_name=tool_name,
        tool_input=tool_input,
        result=result,
        duration_ms=duration_ms,
        failed=failed,
        error_message=error_message,
    )
