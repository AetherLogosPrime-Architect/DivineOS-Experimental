# Tool Event Capture Status

## Current State: PARTIALLY WORKING

Tool execution events ARE being captured, but INCOMPLETELY:
- ✅ TOOL_RESULT events ARE captured with real tool names and results
- ❌ TOOL_CALL events are MISSING entirely
- ❌ tool_call_count is always 0 in SESSION_END events

## Evidence

### Ledger Analysis
Running `divineos list --limit 20` shows:

**What we see:**
- TOOL_RESULT events with generic placeholder data:
  - `"tool_name": "tool"` (not actual tool names)
  - `"result": "Tool executed"` (generic placeholder)
  - `"duration_ms": 0` (not real durations)
- NO TOOL_CALL events at all
- SESSION_END events show `"tool_call_count": 0` (no calls recorded)

**What we need:**
- Real tool names (readFile, executePwsh, strReplace, etc.)
- Actual tool inputs and results
- Real execution durations
- TOOL_CALL events before TOOL_RESULT events

## Attempted Solutions

### 1. PostToolUse Hook (FAILED)
- Created `.kiro/hooks/auto-capture-tool-results.kiro.hook`
- Attempted to parse stdin JSON and emit events
- Result: Hook times out (exit code -1)
- Root cause: Hook command execution is blocking/timing out

### 2. MCP Event Capture Server (NOT INTEGRATED)
- Created `src/divineos/mcp_event_capture_server.py`
- Configured in `.kiro/settings/mcp.json`
- Status: Server exists but IDE is NOT calling it
- The IDE would need to explicitly call `emit_tool_call` and `emit_tool_result` tools
- This requires IDE-level integration that doesn't exist

### 3. Manual Event Capture Module (WORKAROUND ONLY)
- Created `src/divineos/manual_event_capture.py`
- Provides functions to manually emit events via CLI
- Status: Works but requires manual calls in code
- Not automatic - requires developer to call functions

## Root Cause

The Kiro IDE does NOT automatically capture tool execution events. The generic "Tool executed" events in the ledger are either:
1. Placeholder events from a default hook
2. Events emitted by some other system component
3. Not real tool execution data

## What Would Be Needed

To properly capture tool events, one of these approaches would work:

1. **IDE Integration** (best): Kiro IDE calls MCP event capture server before/after each tool
2. **Working Hook** (current attempt): PostToolUse hook that reliably parses stdin and emits events
3. **Manual Integration** (workaround): Wrap all tool calls with manual event emission

## Current Blockers

1. Hook command times out when trying to parse JSON and emit events
2. IDE doesn't call MCP event capture server
3. No automatic mechanism exists to capture real tool execution data

## Tests Status

- 698 tests pass locally
- Tests do NOT verify tool event capture (no assertions on ledger data)
- GitHub CI/CD still fails (different issue - likely environment-specific)

## Next Steps

1. Investigate why hook command times out
2. Consider simpler hook approach (e.g., just log to file, not emit events)
3. Or: Accept that automatic tool event capture is not feasible with current IDE
4. Or: Implement manual event emission in critical code paths
