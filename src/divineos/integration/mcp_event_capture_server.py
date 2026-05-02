"""MCP Event Capture Server - Automatic tool event emission.

# AGENT_RUNTIME — Not wired into CLI pipeline. Runs as a standalone
# MCP server that an AI IDE (Claude Code, Cursor, etc.) connects to.
# Intentionally not Python-imported from any CLI module: the MCP
# protocol IS the integration surface. Launched via the IDE's MCP
# config, not via `divineos <command>`.

This MCP server provides tools that an AI IDE can use to automatically
emit TOOL_CALL and TOOL_RESULT events when tools are executed.

The server exposes:
- emit_tool_call: Emit a TOOL_CALL event before tool execution
- emit_tool_result: Emit a TOOL_RESULT event after tool execution
- get_session_id: Get the current session ID for correlation

This server uses the unified tool capture system for consistency.
"""

import json
import sqlite3
from typing import Any

from divineos.core.error_handling import (
    EventCaptureError,
    SessionError,
    handle_error,
)
from divineos.core.session_manager import get_or_create_session_id
from divineos.core.tool_wrapper import capture_tool_execution

_MEC_ERRORS = (
    ImportError,
    sqlite3.OperationalError,
    OSError,
    KeyError,
    TypeError,
    ValueError,
    json.JSONDecodeError,
)


def emit_tool_call_mcp(
    tool_name: str,
    tool_input: dict[str, Any],
    session_id: str | None = None,
) -> dict[str, Any]:
    """MCP tool to emit a TOOL_CALL event.

    Args:
        tool_name: Name of the tool being called
        tool_input: Input parameters as a dictionary
        session_id: Optional session ID (uses current if not provided)

    Returns:
        Dictionary with event_id and status

    """
    try:
        session_id = get_or_create_session_id(session_id)
        # Use unified capture to emit both TOOL_CALL and TOOL_RESULT
        # For MCP, we just emit the TOOL_CALL part
        tool_call_id, _ = capture_tool_execution(
            tool_name=tool_name,
            tool_input=tool_input,
            result="",
            duration_ms=0,
        )
        return {
            "status": "success",
            "event_id": tool_call_id,
            "tool_name": tool_name,
            "session_id": session_id,
        }
    except (EventCaptureError, SessionError) as e:
        handle_error(e, "emit_tool_call_mcp", {"tool_name": tool_name})
        return {
            "status": "error",
            "error": str(e),
            "tool_name": tool_name,
        }
    except _MEC_ERRORS as e:
        handle_error(e, "emit_tool_call_mcp", {"tool_name": tool_name})
        return {
            "status": "error",
            "error": str(e),
            "tool_name": tool_name,
        }


def emit_tool_result_mcp(
    tool_name: str,
    tool_use_id: str,
    result: str,
    duration_ms: int,
    failed: bool = False,
    error_message: str | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    """MCP tool to emit a TOOL_RESULT event.

    Args:
        tool_name: Name of the tool
        tool_use_id: Unique ID matching the TOOL_CALL event
        result: The result output from the tool
        duration_ms: Execution duration in milliseconds
        failed: Whether the tool execution failed
        error_message: Error message if failed=True
        session_id: Optional session ID (uses current if not provided)

    Returns:
        Dictionary with event_id and status

    """
    try:
        session_id = get_or_create_session_id(session_id)
        # Use unified capture to emit TOOL_RESULT
        _, tool_result_id = capture_tool_execution(
            tool_name=tool_name,
            tool_input={"tool_use_id": tool_use_id},
            result=result,
            duration_ms=duration_ms,
            failed=failed,
            error_message=error_message,
        )
        return {
            "status": "success",
            "event_id": tool_result_id,
            "tool_name": tool_name,
            "session_id": session_id,
            "duration_ms": duration_ms,
        }
    except (EventCaptureError, SessionError) as e:
        handle_error(
            e,
            "emit_tool_result_mcp",
            {"tool_name": tool_name, "tool_use_id": tool_use_id},
        )
        return {
            "status": "error",
            "error": str(e),
            "tool_name": tool_name,
        }
    except _MEC_ERRORS as e:
        handle_error(
            e,
            "emit_tool_result_mcp",
            {"tool_name": tool_name, "tool_use_id": tool_use_id},
        )
        return {
            "status": "error",
            "error": str(e),
            "tool_name": tool_name,
        }


def get_session_id_mcp() -> dict[str, Any]:
    """MCP tool to get the current session ID.

    Returns:
        Dictionary with session_id

    """
    try:
        session_id = get_or_create_session_id()
        return {
            "status": "success",
            "session_id": session_id,
        }
    except SessionError as e:
        handle_error(e, "get_session_id_mcp")
        return {
            "status": "error",
            "error": str(e),
        }
    except _MEC_ERRORS as e:
        handle_error(e, "get_session_id_mcp")
        return {
            "status": "error",
            "error": str(e),
        }


# MCP Server implementation
if __name__ == "__main__":
    """
    This script can be run as an MCP server.

    To use as an MCP server, configure your IDE:

    {
      "mcpServers": {
        "divineos-event-capture": {
          "command": "python",
          "args": ["-m", "divineos.integration.mcp_event_capture_server"],
          "env": {
            "PYTHONPATH": "/path/to/divineos"
          }
        }
      }
    }
    """
    import sys
    from typing import Any

    # Simple stdio-based MCP server
    def handle_request(request: dict[str, Any]) -> dict[str, Any]:
        """Handle MCP requests."""
        method = request.get("method")
        params = request.get("params", {})

        if method == "emit_tool_call":
            return emit_tool_call_mcp(**params)
        if method == "emit_tool_result":
            return emit_tool_result_mcp(**params)
        if method == "get_session_id":
            return get_session_id_mcp()
        return {"status": "error", "error": f"Unknown method: {method}"}

    # Read requests from stdin and write responses to stdout
    for line in sys.stdin:
        try:
            request = json.loads(line)
            response = handle_request(request)
            print(json.dumps(response))  # noqa: T201
            sys.stdout.flush()
        except json.JSONDecodeError as e:
            handle_error(e, "mcp_server_json_decode")
            print(json.dumps({"status": "error", "error": f"Invalid JSON: {e!s}"}))  # noqa: T201
            sys.stdout.flush()
        except _MEC_ERRORS as e:
            handle_error(e, "mcp_server_request_handling")
            print(json.dumps({"status": "error", "error": str(e)}))  # noqa: T201
            sys.stdout.flush()
