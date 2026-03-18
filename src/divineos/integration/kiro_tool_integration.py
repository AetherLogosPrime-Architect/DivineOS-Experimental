"""
Kiro Tool Integration - Automatic event capture for Kiro IDE tools.

This module provides automatic TOOL_CALL and TOOL_RESULT event emission
for all Kiro IDE tool executions (readFile, readCode, executePwsh, etc.).

The integration works by:
1. Intercepting tool execution at the Kiro IDE level
2. Emitting TOOL_CALL events before execution
3. Emitting TOOL_RESULT events after execution
4. Capturing both success and failure cases
"""

import os
from typing import Any, Dict, Optional
from loguru import logger

from divineos.event.event_emission import emit_tool_call, emit_tool_result


class KiroToolCapture:
    """Captures Kiro tool executions and emits events to the ledger."""

    def __init__(self):
        """Initialize the Kiro tool capture system."""
        self.session_id = os.environ.get("DIVINEOS_SESSION_ID")
        logger.info(f"KiroToolCapture initialized with session: {self.session_id}")

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
        tool_call_id = None
        tool_result_id = None

        try:
            # Emit TOOL_CALL event
            try:
                tool_call_id = emit_tool_call(
                    tool_name=tool_name,
                    tool_input=tool_input,
                    session_id=self.session_id,
                )
                logger.debug(f"Emitted TOOL_CALL for {tool_name}: {tool_call_id}")
            except Exception as e:
                logger.warning(f"Failed to emit TOOL_CALL for {tool_name}: {e}")

            # Convert result to string
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
                    session_id=self.session_id,
                )
                logger.debug(f"Emitted TOOL_RESULT for {tool_name}: {tool_result_id}")
            except Exception as e:
                logger.warning(f"Failed to emit TOOL_RESULT for {tool_name}: {e}")

            return tool_call_id, tool_result_id

        except Exception as e:
            logger.error(f"Error capturing tool execution for {tool_name}: {e}")
            return None, None


# Global instance
_kiro_capture = None


def get_kiro_capture() -> KiroToolCapture:
    """Get or create the global Kiro tool capture instance."""
    global _kiro_capture
    if _kiro_capture is None:
        _kiro_capture = KiroToolCapture()
    return _kiro_capture


def capture_kiro_tool(
    tool_name: str,
    tool_input: Dict[str, Any],
    result: Any,
    duration_ms: int,
    failed: bool = False,
    error_message: Optional[str] = None,
) -> tuple[Optional[str], Optional[str]]:
    """
    Convenience function to capture a Kiro tool execution.

    Usage:
        from divineos.integration.kiro_tool_integration import capture_kiro_tool

        # After a tool executes
        capture_kiro_tool(
            tool_name="readFile",
            tool_input={"path": "src/main.py"},
            result="file contents...",
            duration_ms=150,
        )
    """
    capture = get_kiro_capture()
    return capture.capture_tool_execution(
        tool_name=tool_name,
        tool_input=tool_input,
        result=result,
        duration_ms=duration_ms,
        failed=failed,
        error_message=error_message,
    )
