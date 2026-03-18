"""
Manual Event Capture - Workaround for automatic tool event emission.

Since the Kiro IDE doesn't automatically call the MCP event capture server,
this module provides a way to manually emit events after tool execution.

Usage:
    from divineos.tools.manual_event_capture import capture_tool_execution

    # After a tool executes
    capture_tool_execution(
        tool_name="readFile",
        tool_input={"path": "src/main.py"},
        result="file contents...",
        duration_ms=150,
    )
"""

import subprocess
import json
from typing import Any, Dict, Optional
from loguru import logger


def capture_tool_execution(
    tool_name: str,
    tool_input: Dict[str, Any],
    result: str,
    duration_ms: int,
    failed: bool = False,
    error_message: Optional[str] = None,
) -> tuple[Optional[str], Optional[str]]:
    """
    Manually emit TOOL_CALL and TOOL_RESULT events for a tool execution.

    This is a workaround for when the IDE doesn't automatically capture events.

    Args:
        tool_name: Name of the tool
        tool_input: Input parameters
        result: The result from the tool
        duration_ms: Execution duration
        failed: Whether the tool failed
        error_message: Error message if failed

    Returns:
        Tuple of (tool_call_event_id, tool_result_event_id)
    """
    tool_call_id = None
    tool_result_id = None

    try:
        # Emit TOOL_CALL
        try:
            cmd = [
                "divineos",
                "emit",
                "TOOL_CALL",
                "--tool-name",
                tool_name,
                "--tool-input",
                json.dumps(tool_input),
            ]
            result_call = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if result_call.returncode == 0:
                # Extract event ID from output
                for line in result_call.stdout.split("\n"):
                    if "Event ID:" in line:
                        tool_call_id = line.split("Event ID:")[1].strip()
                        logger.debug(f"Emitted TOOL_CALL: {tool_call_id}")
                        break
        except Exception as e:
            logger.warning(f"Failed to emit TOOL_CALL: {e}")

        # Truncate result if too long
        result_str = str(result) if isinstance(result, str) else str(result)
        if len(result_str) > 5000:
            result_str = result_str[:5000] + "... [truncated]"

        # Emit TOOL_RESULT
        try:
            cmd = [
                "divineos",
                "emit",
                "TOOL_RESULT",
                "--tool-name",
                tool_name,
                "--result",
                result_str,
                "--duration-ms",
                str(duration_ms),
            ]
            if failed:
                cmd.extend(["--failed"])
            if error_message:
                cmd.extend(["--error-message", error_message])

            result_result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if result_result.returncode == 0:
                # Extract event ID from output
                for line in result_result.stdout.split("\n"):
                    if "Event ID:" in line:
                        tool_result_id = line.split("Event ID:")[1].strip()
                        logger.debug(f"Emitted TOOL_RESULT: {tool_result_id}")
                        break
        except Exception as e:
            logger.warning(f"Failed to emit TOOL_RESULT: {e}")

        return tool_call_id, tool_result_id

    except Exception as e:
        logger.error(f"Error capturing tool execution: {e}")
        return None, None


def emit_tool_call_manual(
    tool_name: str,
    tool_input: Dict[str, Any],
) -> Optional[str]:
    """Manually emit a TOOL_CALL event."""
    try:
        cmd = [
            "divineos",
            "emit",
            "TOOL_CALL",
            "--tool-name",
            tool_name,
            "--tool-input",
            json.dumps(tool_input),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            for line in result.stdout.split("\n"):
                if "Event ID:" in line:
                    return line.split("Event ID:")[1].strip()
    except Exception as e:
        logger.warning(f"Failed to emit TOOL_CALL: {e}")
    return None


def emit_tool_result_manual(
    tool_name: str,
    result: str,
    duration_ms: int,
    failed: bool = False,
    error_message: Optional[str] = None,
) -> Optional[str]:
    """Manually emit a TOOL_RESULT event."""
    try:
        cmd = [
            "divineos",
            "emit",
            "TOOL_RESULT",
            "--tool-name",
            tool_name,
            "--result",
            result,
            "--duration-ms",
            str(duration_ms),
        ]
        if failed:
            cmd.append("--failed")
        if error_message:
            cmd.extend(["--error-message", error_message])

        result_obj = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if result_obj.returncode == 0:
            for line in result_obj.stdout.split("\n"):
                if "Event ID:" in line:
                    return line.split("Event ID:")[1].strip()
    except Exception as e:
        logger.warning(f"Failed to emit TOOL_RESULT: {e}")
    return None
