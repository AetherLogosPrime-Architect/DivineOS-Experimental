# Hook Research Findings

## Key Discovery

Through online research, I discovered that **Kiro IDE hooks receive JSON on stdin**, not through environment variables.

### How Hooks Work

According to official Claude Code documentation and community implementations:

1. **Hook Lifecycle**:
   - PreToolUse fires BEFORE tool execution (can block or modify)
   - PostToolUse fires AFTER tool execution (can react/log)

2. **Hook Input Format**:
   - Hooks receive JSON on stdin: `{"tool_name":"...", "tool_input":{...}, "result":"...", "duration_ms":...}`
   - NOT through environment variables like `$CLAUDE_TOOL_NAME` (these are broken)

3. **Hook Handler Types**:
   - `command`: Runs a shell command (deterministic)
   - `prompt`: Sends prompt to LLM (judgment calls)
   - `agent`: Spawns multi-turn agent (complex verification)

### What This Means for Event Capture

The postToolUse hook CAN access tool execution details through stdin JSON, which means:

1. **Potential Solution**: Create a hook that:
   - Reads JSON from stdin
   - Extracts tool_name, tool_input, result, duration_ms
   - Calls `divineos emit TOOL_CALL` and `divineos emit TOOL_RESULT` with actual data

2. **Implementation Challenge**: 
   - Hook command must parse stdin JSON
   - Must call divineos CLI with extracted data
   - Must handle errors gracefully

### Current Status

- ✅ Discovered hook input mechanism (JSON on stdin)
- ✅ Identified that environment variables don't work
- ❌ Hook implementation still failing (needs debugging)
- ❌ Event capture still not working end-to-end

### Next Steps

1. Create a proper hook script that reads stdin JSON
2. Parse the JSON to extract tool context
3. Emit TOOL_CALL and TOOL_RESULT events with actual tool data
4. Test that events are captured in the ledger

### References

- [Claude Code Hooks Tutorial](https://paul-schick.com/posts/claude-code-hooks-pretooluse-posttooluse/)
- [Hook Input Format](https://lobehub.com/skills/0xdarkmatter-claude-mods-claude-code-hooks)
- [GitHub Issue on Environment Variables](https://github.com/anthropics/claude-code/issues/5489)
