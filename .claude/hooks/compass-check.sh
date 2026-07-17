#!/bin/bash
# PreToolUse hook — thin doorbell for the compass-rudder gate.
#
# All judgment lives in `divineos.core.compass_rudder.check_tool_use()`.
# On block: emit Claude Code deny JSON so the tool call is actually
# stopped. On allow / non-gated tool / any error: exit 0 (allow).
#
# History (Marc external audit 2026-07-16, finding #1): this hook
# previously imported a `main` function that has never existed in
# compass_rudder.py — `check_tool_use` has always been the real entry.
# The ImportError was swallowed by `except: pass`, making the moral
# compass rudder a permanent silent no-op. Fixed 2026-07-16 in the
# same commit that adds a wiring test.

set +e
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
[ -z "$REPO_ROOT" ] && exit 0
# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)"
if [ -z "$PYTHON_BIN" ]; then
    # Fail-LOUD per Aletheia audit 2026-07-09 Deep Truck 1: a silently-
    # skipped enforcement gate is indistinguishable from a gate that ran
    # clean. Record the skip to stderr so a resolver-drift is
    # investigable, not invisible.
    echo "  [compass-check] SKIPPED: find_divineos_python returned nothing - gate did NOT run" >&2
    exit 0
fi

INPUT=$(cat)

PY_STDERR=$(mktemp)
RESULT=$(echo "$INPUT" | "$PYTHON_BIN" -c "
import json, sys

try:
    data = json.loads(sys.stdin.read() or '{}')
except Exception as exc:
    print(f'PARSE_ERROR:{exc}', file=sys.stderr)
    sys.exit(0)

tool_name = data.get('tool_name') or ''
tool_input = data.get('tool_input') or {}

try:
    from divineos.core.compass_rudder import check_tool_use
except Exception as exc:
    print(f'IMPORT_ERROR:{exc}', file=sys.stderr)
    sys.exit(0)

try:
    verdict = check_tool_use(tool_name, tool_input)
except Exception as exc:
    print(f'GATE_ERROR:{exc}', file=sys.stderr)
    sys.exit(0)

if verdict.decision != 'block':
    sys.exit(0)

print(json.dumps({
    'hookSpecificOutput': {
        'hookEventName': 'PreToolUse',
        'permissionDecision': 'deny',
        'permissionDecisionReason': verdict.reason,
    }
}))
" 2>"$PY_STDERR")

if [ -s "$PY_STDERR" ]; then
    echo "  [compass-check] GATE ERROR (failed open, see below):" >&2
    cat "$PY_STDERR" >&2
fi
rm -f "$PY_STDERR"

echo "$RESULT"
exit 0
