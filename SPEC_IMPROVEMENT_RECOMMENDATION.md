# Real IDE Integration Spec - Improvement Recommendation

## Issue Identified

The current Real IDE Integration spec captures:
- ✓ USER_INPUT events (user messages)
- ✓ TOOL_CALL events (tool invocations)
- ✓ TOOL_RESULT events (tool results)
- ✓ SESSION_END events (session metadata)

But it does NOT capture:
- ✗ ASSISTANT_OUTPUT events (AI explanations and responses)

## Impact

This design gap causes:
1. **Clarity Analysis Failure** - Quality analysis shows "0 explanations" even when AI provides explanations
2. **Incomplete Fidelity** - The ledger doesn't capture the complete conversation
3. **Missing Context** - Analysis can't correlate explanations with tool calls

## Example

Current session analysis shows:
```
Work vs Talk: 100% doing things, 0% explaining
The AI made 1 tool calls and wrote 0 explanations
```

But the AI actually provided explanations before each tool call using the 4-step clarity pattern.

## Recommendation

Add ASSISTANT_OUTPUT event capture to the spec to capture AI explanations and responses.

## Status

- **Issue Identified**: ✓
- **Root Cause**: Design gap - ASSISTANT_OUTPUT not in spec
- **Recommendation**: Add ASSISTANT_OUTPUT event capture
- **Priority**: High (affects clarity analysis accuracy)
- **Effort**: Medium (similar to existing event capture implementation)

