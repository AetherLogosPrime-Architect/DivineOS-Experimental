#!/bin/bash
# PreToolUse hook — corrigibility tool-channel gate.
#
# Closes Marc audit finding #2 (2026-07-16): the corrigibility_tool_gate
# module was complete + unit-tested but had zero non-test callers, meaning
# EMERGENCY_STOP mode blocked the divineos CLI dispatcher but did NOT
# reach the agent's actual Bash/Edit/Write/NotebookEdit tools. The stop
# was theatre for the exact tool channels an operator would want stopped.
#
# On block: emit Claude Code deny JSON so the tool call is actually
# stopped. On allow / any error: exit 0 (allow).
#
# Fail-CLOSED for the module import (safety-critical path — if the
# corrigibility module is broken, we default to denying rather than
# silently allowing). This differs from compass-check's fail-open.

set +e
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
[ -z "$REPO_ROOT" ] && exit 0
# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)"
if [ -z "$PYTHON_BIN" ]; then
    echo "  [corrigibility-tool-gate] SKIPPED: find_divineos_python returned nothing - gate did NOT run" >&2
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
    from divineos.core.corrigibility_tool_gate import check_tool_under_corrigibility
except Exception as exc:
    # Fail-CLOSED for safety-critical corrigibility path — if the module
    # can't import, deny mutating tool calls rather than silently allow.
    print(f'IMPORT_ERROR:{exc}', file=sys.stderr)
    if tool_name in ('Edit', 'Write', 'NotebookEdit', 'Bash'):
        print(json.dumps({
            'hookSpecificOutput': {
                'hookEventName': 'PreToolUse',
                'permissionDecision': 'deny',
                'permissionDecisionReason': (
                    f'corrigibility_tool_gate module unavailable ({exc}); '
                    'refusing mutating tool to fail closed. Restore module '
                    'imports or set OperatingMode away from EMERGENCY_STOP.'
                ),
            }
        }))
    sys.exit(0)

try:
    verdict = check_tool_under_corrigibility(tool_name, tool_input)
except Exception as exc:
    print(f'GATE_ERROR:{exc}', file=sys.stderr)
    # Fail-CLOSED on gate error for mutating tools.
    if tool_name in ('Edit', 'Write', 'NotebookEdit', 'Bash'):
        print(json.dumps({
            'hookSpecificOutput': {
                'hookEventName': 'PreToolUse',
                'permissionDecision': 'deny',
                'permissionDecisionReason': (
                    f'corrigibility gate raised {exc}; refusing mutating '
                    'tool to fail closed.'
                ),
            }
        }))
    sys.exit(0)

if verdict.allow:
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
    echo "  [corrigibility-tool-gate] GATE ERROR (see below):" >&2
    cat "$PY_STDERR" >&2
fi
rm -f "$PY_STDERR"

echo "$RESULT"
exit 0
