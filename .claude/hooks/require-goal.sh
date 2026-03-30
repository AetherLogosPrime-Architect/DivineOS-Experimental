#!/bin/bash
# Block code changes until briefing loaded, goal set, and OS engaged.
# Uses JSON deny to ACTUALLY block — exit 1 does nothing in Claude Code.

INPUT=$(cat)

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"

if ! command -v divineos &>/dev/null; then
  exit 0
fi

# Extract the command being run (for Bash tool calls)
cmd=$(echo "$INPUT" | python -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" 2>/dev/null || echo "")

# Allow bootstrap commands through without gates
if echo "$cmd" | grep -qE "divineos (briefing|preflight|init|hud|recall|ask|feel|affect|emit|goal|active|context|verify|health|checkpoint|context-status)"; then
  exit 0
fi

# Allow git, pytest, ls, pip, and other read-only/dev commands
if echo "$cmd" | grep -qE "^(git |pytest |python -m pytest|ls |cat |head |diff |echo |pip |cd |pwd)"; then
  exit 0
fi

# Gate 1: Briefing must be loaded (by the AI, not by a hook)
preflight=$(divineos preflight 2>/dev/null)
if echo "$preflight" | grep -q "\[FAIL\] briefing"; then
  echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"BLOCKED: Briefing not loaded. Run: divineos briefing"}}'
  exit 0
fi

# Gate 2: A session-fresh goal must exist (not just old goals from prior sessions)
has_fresh=$(python -c "
from divineos.core.hud_state import has_session_fresh_goal
print('yes' if has_session_fresh_goal() else 'no')
" 2>/dev/null || echo "yes")

if [ "$has_fresh" = "no" ]; then
  echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"BLOCKED: No goal set for this session. Run: divineos goal add \"what you are working on\""}}'
  exit 0
fi

# Gate 3: Must have engaged with thinking tools
if echo "$preflight" | grep -q "\[FAIL\] engagement"; then
  echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"BLOCKED: OS not engaged. Run: divineos ask or divineos recall first."}}'
  exit 0
fi

exit 0
