#!/bin/bash
# PreToolUse hook — block destructive deletions until justified.
#
# Deletion-discipline lesson (Andrew 2026-05-21): never pure-delete. Read +
# understand, investigate for anything worth saving, extract it, THEN delete.
# Proven the same day: investigating talk-to-wrapper-collapse before deleting
# found 47 files of needed work pure deletion would have destroyed.
#
# Thin doorman: the logic lives in core.deletion_discipline.block_reason.
# This hook reads the Bash command, asks the OS for a verdict, and denies
# with the OS's message if a destructive deletion lacks a fresh justification.
# Per [code-does-not-think]: the gate enforces that the judgment was recorded;
# it never decides the deletion is wise.
#
# Fail-open: any error exits 0 (this hook must not break the workflow).

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
    from divineos.core.deletion_discipline import block_reason
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
