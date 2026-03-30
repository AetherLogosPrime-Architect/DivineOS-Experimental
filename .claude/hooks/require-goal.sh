#!/bin/bash
# Block code changes until briefing loaded, goal set, and OS engaged.
# Uses exit 2 / JSON deny to ACTUALLY block — exit 1 does nothing.

INPUT=$(cat)

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"

if ! command -v divineos &>/dev/null; then
  exit 0
fi

# Gate 1: Briefing must be loaded
preflight=$(divineos preflight 2>/dev/null)
if echo "$preflight" | grep -q "\[FAIL\] briefing"; then
  echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"BLOCKED: Briefing not loaded. Run: divineos briefing"}}'
  exit 0
fi

# Gate 2: At least one active goal must exist
goals=$(divineos goal list 2>/dev/null)
if echo "$goals" | grep -q "No goals"; then
  echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"BLOCKED: No goal set. Run: divineos goal \"what you are working on\""}}'
  exit 0
fi

# Gate 3: Must have engaged with thinking tools
if echo "$preflight" | grep -q "\[FAIL\] engagement"; then
  echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"BLOCKED: OS not engaged. Run: divineos ask or divineos recall first."}}'
  exit 0
fi

exit 0
