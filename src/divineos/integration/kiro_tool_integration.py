"""
Kiro Tool Integration - Automatic event capture for Kiro IDE tools.

This module provides automatic TOOL_CALL and TOOL_RESULT event emission
for all Kiro IDE tool executions (readFile, readCode, executePwsh, etc.).

The integration works by:
1. Intercepting tool execution at the Kiro IDE level
2. Emitting TOOL_CALL events before execution
3. Emitting TOOL_RESULT events after execution
4. Capturing both success and failure cases

This module now uses the unified tool capture system for consistency.
"""

import os
from typing import Any, Dict, Optional
from loguru import logger

from divineos.integration.unified_tool_capture import get_unified_capture


class KiroToolCapture:
    """Captures Kiro tool executions and emits events to the ledger."""

    def __init__(self):
        """Initialize the Kiro tool capture system."""
        self.session_id = os.environ.get("DIVINEOS_SESSION_ID")
        self.unified_capture = get_unified_capture()
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
        call_id, result_id = self.unified_capture.capture_tool_execution(
            tool_name=tool_name,
            tool_input=tool_input,
            result=result,
            duration_ms=duration_ms,
            failed=failed,
            error_message=error_message,
        )
        return call_id, result_id


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
