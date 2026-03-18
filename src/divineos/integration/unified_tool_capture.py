"""
Unified Tool Capture - Single source of truth for tool event emission.

This module provides a unified interface for capturing tool executions
from both Kiro IDE and MCP servers. It ensures consistent event emission
and prevents duplicate captures.

Features:
- Thread-safe singleton pattern
- Automatic session management
- Consistent event emission
- Error handling and logging
- Result truncation for large outputs
"""

import os
import threading
from typing import Any, Dict, Optional
from loguru import logger

from divineos.event.event_emission import emit_tool_call, emit_tool_result, get_or_create_session_id


class UnifiedToolCapture:
    """Unified tool capture system for both Kiro and MCP."""

    def __init__(self):
        """Initialize the unified tool capture system."""
        self._lock = threading.RLock()
        self.session_id = os.environ.get("DIVINEOS_SESSION_ID")
        logger.info(f"UnifiedToolCapture initialized with session: {self.session_id}")

    def capture_tool_execution(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        result: Any,
        duration_ms: int,
        failed: bool = False,
        error_message: Optional[str] = None,
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Capture a tool execution and emit TOOL_CALL and TOOL_RESULT events.

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
                except Exception as e:
                    logger.warning(f"Failed to emit TOOL_CALL for {tool_name}: {e}")

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
                except Exception as e:
                    logger.warning(f"Failed to emit TOOL_RESULT for {tool_name}: {e}")

                return tool_call_id, tool_result_id

            except Exception as e:
                logger.error(f"Error capturing tool execution for {tool_name}: {e}")
                return None, None


# Global instance
_unified_capture = None
_capture_lock = threading.Lock()


def get_unified_capture() -> UnifiedToolCapture:
    """Get or create the global unified tool capture instance."""
    global _unified_capture
    if _unified_capture is None:
        with _capture_lock:
            if _unified_capture is None:
                _unified_capture = UnifiedToolCapture()
    return _unified_capture


def capture_tool_execution(
    tool_name: str,
    tool_input: Dict[str, Any],
    result: Any,
    duration_ms: int,
    failed: bool = False,
    error_message: Optional[str] = None,
) -> tuple[Optional[str], Optional[str]]:
    """
    Convenience function to capture a tool execution.

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
