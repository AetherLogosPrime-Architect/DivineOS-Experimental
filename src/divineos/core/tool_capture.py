"""IDE Tool Capture Module — IDE integration and unified tool capture.

This module provides:
- IDEToolExecutor: Middleware for IDE tool execution event capture
- UnifiedToolCapture: Thread-safe singleton for Claude Code and MCP capture
- Convenience functions for emitting tool events from IDE contexts

Extracted from tool_wrapper.py to keep modules under 500 lines.
"""

import os
import threading
import time
import uuid
from typing import Any
import sqlite3

from loguru import logger

from divineos.core.error_handling import (
    EventCaptureError,
    handle_error,
)
from divineos.core.session_manager import get_or_create_session_id
from divineos.event.event_emission import emit_tool_call, emit_tool_result

_TC_ERRORS = (ImportError, sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError)


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
        except _TC_ERRORS as e:
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
        except _TC_ERRORS as e:
            logger.error(
                f"Failed to emit TOOL_RESULT event for {tool_info['tool_name']}: {e}",
                exc_info=True,
            )
            return None

    def execute_tool(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        tool_function: Any,
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

        except _TC_ERRORS as e:
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
    """Unified tool capture system for Claude Code and MCP.

    This class provides a thread-safe singleton pattern for capturing tool
    executions from Claude Code and MCP servers. It ensures consistent
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
                except _TC_ERRORS as e:
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
                except _TC_ERRORS as e:
                    handle_error(e, "emit_tool_result_unified", {"tool_name": tool_name})

                return tool_call_id, tool_result_id

            except EventCaptureError as e:
                handle_error(e, "capture_tool_execution_unified", {"tool_name": tool_name})
                return None, None
            except _TC_ERRORS as e:
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
