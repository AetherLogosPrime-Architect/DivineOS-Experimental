"""
MCP Event Capture Server - Automatic tool event emission for Kiro IDE.

This MCP server provides tools that the Kiro IDE can use to automatically
emit TOOL_CALL and TOOL_RESULT events when tools are executed.

The server exposes:
- emit_tool_call: Emit a TOOL_CALL event before tool execution
- emit_tool_result: Emit a TOOL_RESULT event after tool execution
- get_session_id: Get the current session ID for correlation

This allows the IDE to integrate event capture without modifying tool execution.
"""

import json
from typing import Any, Dict, Optional
from loguru import logger

from divineos.event.event_emission import emit_tool_call, emit_tool_result, get_or_create_session_id


def emit_tool_call_mcp(
    tool_name: str,
    tool_input: Dict[str, Any],
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    MCP tool to emit a TOOL_CALL event.

    Args:
        tool_name: Name of the tool being called
        tool_input: Input parameters as a dictionary
        session_id: Optional session ID (uses current if not provided)

    Returns:
        Dictionary with event_id and status
    """
    try:
        session_id = get_or_create_session_id(session_id)
        event_id = emit_tool_call(
            tool_name=tool_name,
            tool_input=tool_input,
            session_id=session_id,
        )
        return {
            "status": "success",
            "event_id": event_id,
            "tool_name": tool_name,
            "session_id": session_id,
        }
    except Exception as e:
        logger.error(f"Failed to emit TOOL_CALL: {e}")
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
    error_message: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    MCP tool to emit a TOOL_RESULT event.

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
        event_id = emit_tool_result(
            tool_name=tool_name,
            tool_use_id=tool_use_id,
            result=result,
            duration_ms=duration_ms,
            failed=failed,
            error_message=error_message,
            session_id=session_id,
        )
        return {
            "status": "success",
            "event_id": event_id,
            "tool_name": tool_name,
            "session_id": session_id,
            "duration_ms": duration_ms,
        }
    except Exception as e:
        logger.error(f"Failed to emit TOOL_RESULT: {e}")
        return {
            "status": "error",
            "error": str(e),
            "tool_name": tool_name,
        }


def get_session_id_mcp() -> Dict[str, Any]:
    """
    MCP tool to get the current session ID.

    Returns:
        Dictionary with session_id
    """
    try:
        session_id = get_or_create_session_id()
        return {
            "status": "success",
            "session_id": session_id,
        }
    except Exception as e:
        logger.error(f"Failed to get session ID: {e}")
        return {
            "status": "error",
            "error": str(e),
        }


# MCP Server implementation
if __name__ == "__main__":
    """
    This script can be run as an MCP server.
    
    To use with Kiro IDE, add to ~/.kiro/settings/mcp.json:
    
    {
      "mcpServers": {
        "divineos-event-capture": {
          "command": "python",
          "args": ["-m", "divineos.mcp_event_capture_server"],
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
    def handle_request(request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP requests."""
        method = request.get("method")
        params = request.get("params", {})

        if method == "emit_tool_call":
            return emit_tool_call_mcp(**params)
        elif method == "emit_tool_result":
            return emit_tool_result_mcp(**params)
        elif method == "get_session_id":
            return get_session_id_mcp()
        else:
            return {"status": "error", "error": f"Unknown method: {method}"}

    # Read requests from stdin and write responses to stdout
    for line in sys.stdin:
        try:
            request = json.loads(line)
            response = handle_request(request)
            print(json.dumps(response))
            sys.stdout.flush()
        except Exception as e:
            print(json.dumps({"status": "error", "error": str(e)}))
            sys.stdout.flush()
