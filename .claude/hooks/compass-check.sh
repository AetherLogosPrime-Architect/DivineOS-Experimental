#!/bin/bash
# PreToolUse hook: Compass rudder for Task (subagent spawn).
#
# The moral compass was a mirror until 2026-04-16. This hook makes it a
# rudder: when any spectrum is drifting toward excess at or above the
# threshold and no ``divineos decide`` mentioning the drifting spectrum
# was emitted in the last 5 minutes, the hook blocks the Task tool call
# and asks for a justification.
#
# Scope: narrow on purpose. Only Task is gated in this first version.
# The spectrum that motivated the rudder (``initiative: excess``) was
# caused by subagent-spawn cascades. Gating that one operation is the
# cleanest test of whether decision-time justification actually changes
# behavior. Widen if it works.
#
# Fail-open design: any infrastructure error (missing DB, import failure,
# timeout) exits 0 without blocking. A compass rudder that breaks the
# agent when the compass DB is empty is worse than one that occasionally
# misses a drift event.

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo ".")" || exit 0

INPUT=$(cat)

if ! command -v divineos &>/dev/null; then
  exit 0
fi

tool_name=$(echo "$INPUT" | python -c "import sys,json; print(json.load(sys.stdin).get('tool_name',''))" 2>/dev/null || echo "")

# Only the gated tool names trigger the rudder. Anything else exits
# immediately — no compass query, no decision-journal scan, no latency.
if [ "$tool_name" != "Task" ] && [ "$tool_name" != "Agent" ]; then
  exit 0
fi

result=$(python -c "
import json, sys

try:
    from divineos.core.compass_rudder import check_tool_use

    payload = json.load(sys.stdin)
    verdict = check_tool_use(
        tool_name=payload.get('tool_name', ''),
        tool_input=payload.get('tool_input', {}),
    )
    if verdict.blocked:
        print(json.dumps({
            'hookSpecificOutput': {
                'hookEventName': 'PreToolUse',
                'permissionDecision': 'deny',
                'permissionDecisionReason': verdict.reason,
            }
        }))
except Exception:
    pass  # fail-open — never let an infrastructure error block work
" <<< "$INPUT" 2>/dev/null)

if [ -n "$result" ]; then
  echo "$result"
fi

exit 0
