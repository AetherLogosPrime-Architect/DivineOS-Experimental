# MCP Event Capture Server

The DivineOS MCP Event Capture Server provides automatic tool event emission for the Kiro IDE.

## Overview

The server exposes three MCP tools that allow the IDE to automatically emit TOOL_CALL and TOOL_RESULT events when tools are executed:

- `emit_tool_call` - Emit a TOOL_CALL event before tool execution
- `emit_tool_result` - Emit a TOOL_RESULT event after tool execution  
- `get_session_id` - Get the current session ID for correlation

## Configuration

The MCP server is configured in `.kiro/settings/mcp.json`:

```json
{
  "mcpServers": {
    "divineos-event-capture": {
      "command": "python",
      "args": ["-m", "divineos.mcp_event_capture_server"],
      "env": {
        "PYTHONPATH": "."
      },
      "disabled": false,
      "autoApprove": [
        "emit_tool_call",
        "emit_tool_result",
        "get_session_id"
      ]
    }
  }
}
```

## Usage

### Before Tool Execution

Call `emit_tool_call` with the tool name and input parameters:

```json
{
  "method": "emit_tool_call",
  "params": {
    "tool_name": "readFile",
    "tool_input": {
      "path": "src/main.py"
    }
  }
}
```

Response:
```json
{
  "status": "success",
  "event_id": "evt-123...",
  "tool_name": "readFile",
  "session_id": "sess-456..."
}
```

### After Tool Execution

Call `emit_tool_result` with the tool name, result, and duration:

```json
{
  "method": "emit_tool_result",
  "params": {
    "tool_name": "readFile",
    "result": "file contents...",
    "duration_ms": 150,
    "failed": false
  }
}
```

Response:
```json
{
  "status": "success",
  "event_id": "evt-789...",
  "tool_name": "readFile",
  "session_id": "sess-456...",
  "duration_ms": 150
}
```

### Get Current Session ID

Call `get_session_id` to get the current session ID:

```json
{
  "method": "get_session_id",
  "params": {}
}
```

Response:
```json
{
  "status": "success",
  "session_id": "sess-456..."
}
```

## IDE Integration

The Kiro IDE should:

1. Before executing any tool, call `emit_tool_call` with the tool name and input
2. After the tool completes, call `emit_tool_result` with the result and duration
3. Use the same session ID for all events in a session

This ensures all tool executions are automatically captured in the DivineOS ledger with proper session tracking and timing information.

## Error Handling

If event emission fails, the MCP server returns:

```json
{
  "status": "error",
  "error": "error message",
  "tool_name": "readFile"
}
```

The IDE should handle these errors gracefully and continue tool execution even if event emission fails.
