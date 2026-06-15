#!/bin/bash
# PreToolUse hook — block `gh pr merge` on guardrail-touching PRs without
# an External-Review trailer in the merge body.
#
# Root cause (Andrew 2026-05-28): PR #50 modified moral_compass.py (a
# guardrail file) and merged without a trailer, producing a permanent
# red Integrity Audit badge on main. The pre-merge CI check fired red
# but GitHub didn't refuse the merge button.
#
# This gate moves the discipline into the OS itself so a fresh DivineOS
# install inherits guardrail protection at clone-time without any
# Andrew-side GitHub branch-protection configuration. Same shape as
# deletion-discipline.sh: thin doorman; logic in core.pr_merge_gate.
#
# Fail-open: any error exits 0 (this hook must not break workflows when
# gh is unavailable, the network is down, or the OS module is unreachable).

INPUT=$(cat)

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

echo "$INPUT" | "$PYTHON_BIN" -c "
import json, sys

try:
    data = json.loads(sys.stdin.read() or '{}')
except Exception:
    sys.exit(0)

if (data.get('tool_name') or '') != 'Bash':
    sys.exit(0)
cmd = (data.get('tool_input') or {}).get('command') or ''
if not cmd.strip():
    sys.exit(0)

try:
    from divineos.core.pr_merge_gate import block_reason
except Exception:
    sys.exit(0)  # fail-open if OS module unavailable

try:
    reason = block_reason(cmd)
except Exception:
    sys.exit(0)

if not reason:
    sys.exit(0)

print(json.dumps({
    'hookSpecificOutput': {
        'hookEventName': 'PreToolUse',
        'permissionDecision': 'deny',
        'permissionDecisionReason': reason,
    }
}))
" 2>/dev/null

exit 0
