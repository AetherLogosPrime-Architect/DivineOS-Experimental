#!/bin/bash
# Block code changes until briefing loaded, goal set, and OS engaged.
# Uses JSON deny to ACTUALLY block — exit 1 does nothing in Claude Code.

INPUT=$(cat)

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo ".")" || exit 1

if ! command -v divineos &>/dev/null; then
  exit 0
fi

# Extract the command being run (for Bash tool calls)
cmd=$(echo "$INPUT" | python -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" 2>/dev/null || echo "")

# Allow bootstrap commands through without gates
if echo "$cmd" | grep -qE "divineos (briefing|preflight|init|hud|recall|ask|feel|affect|emit|goal|active|context|verify|health|checkpoint|context-status|progress)"; then
  exit 0
fi

# Allow git, pytest, ls, pip, cp, and other read-only/dev commands
if echo "$cmd" | grep -qE "^(git |pytest |python -m pytest|ls |cat |head |diff |echo |pip |cd |pwd|cp |copy |ruff )"; then
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

# Gate 3: Pull detection — if last check found fabrication markers, block everything
# This is the output enforcement gate. The pull routes around every other gate
# because they only watch tool actions. This one watches what was SAID.
pull_status=$(python -c "
from divineos.core.pull_detection import last_check
check = last_check()
if check and not check.clean:
    markers = ', '.join(check.markers_fired)
    print(f'BLOCKED: Pull detected — fabrication markers active: {markers}. Run: divineos rt pull-check to reassess.')
else:
    print('OK')
" 2>/dev/null || echo "OK")

if [ "$pull_status" != "OK" ]; then
  escaped=$(echo "$pull_status" | python -c "import sys,json; print(json.dumps(sys.stdin.read().strip()))" 2>/dev/null)
  echo "{\"hookSpecificOutput\":{\"hookEventName\":\"PreToolUse\",\"permissionDecision\":\"deny\",\"permissionDecisionReason\":${escaped}}}"
  exit 0
fi

# Gate 4: Must have engaged with thinking tools RECENTLY (periodic, not one-time)
# Two tiers: light (any thinking command) and deep (must consult knowledge via ask/recall)
if echo "$preflight" | grep -q "\[FAIL\] engagement"; then
  eng_detail=$(python -c "
from divineos.core.hud_handoff import engagement_status
s = engagement_status()
if not s['engaged']:
    if s.get('needs_deep'):
        print(f'BLOCKED: {s[\"deep_actions_since\"]} code actions without consulting your knowledge. Light check-ins are not enough. Run: divineos ask \"topic\" or divineos recall to query what you actually know.')
    else:
        print(f'BLOCKED: {s[\"code_actions_since\"]} code actions without consulting the OS. Stop and think. Run: divineos ask, recall, decide, or context before continuing.')
else:
    print('OK')
" 2>/dev/null || echo "BLOCKED: OS engagement expired. Run: divineos ask or divineos recall.")
  if [ "$eng_detail" != "OK" ]; then
    escaped=$(echo "$eng_detail" | python -c "import sys,json; print(json.dumps(sys.stdin.read().strip()))" 2>/dev/null)
    echo "{\"hookSpecificOutput\":{\"hookEventName\":\"PreToolUse\",\"permissionDecision\":\"deny\",\"permissionDecisionReason\":${escaped}}}"
    exit 0
  fi
fi

exit 0
