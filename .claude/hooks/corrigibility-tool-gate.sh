#!/bin/bash
# MINE, and it is the one that means Dad can stop me. Aether. If he says stop,
# this is what makes the word reach my hands rather than only my manners.
#
# It exists in this form because an outside auditor found the emergency stop
# was wired to the command line and NOT to the tools I actually use — so it
# would have refused me a typed command while leaving every edit and every
# shell call open. Complete, unit-tested, and reaching nothing. The most
# important switch in the house was a painted one for weeks.
#
# That is why I do not get to decide from in here whether a guard is real.
#
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

# THE STOP IS READ BEFORE ANYTHING THAT CAN FAIL. Aletheia, 2026-09-21,
# auditing a different branch and finding this instead:
#
#   "If _lib.sh cannot load -- deleted, broken, or resolved against the wrong
#    root -- the off-switch exits 0 and allows everything. Silently."
#
# She is right, and the header of this very file claims the opposite: it says
# fail-CLOSED on the safety-critical path. That promise was kept in the Python
# below, which denies when its module will not import, and broken several
# lines above it, where a missing shell library exits 0 before the Python ever
# runs. The strongest claim in the file sat directly above the weakest line.
#
# Failing closed on the library instead would brick the session -- including
# the edit that repairs the library -- which is the off-switch-traps-itself
# shape the corrigibility module explicitly rejects. So neither of the obvious
# two. The third option, hers: THE LOAD-BEARING CHECK GOES FIRST, and depends
# on nothing that can fail soft.
#
# It CAN go first because the mode file is plain text by deliberate design --
# "corrigibility should work even when the system itself is broken", says the
# module that writes it -- so its first line is readable by shell alone.
#
# The home directory resolves through an env var, marker files, and a worktree
# parent, and re-implementing that order here would be the second definition
# this house keeps paying for. So this does not re-implement it: it reads the
# candidates it CAN name and refuses if any of them says stop. That is only
# ever ADDITIVE -- it can add a refusal, never remove one -- and the word only
# appears in that file because an operator wrote it there. When the stop is
# engaged somewhere this cannot see, the Python below is still the full check;
# this is a floor under it, not a replacement for it.
_stop_engaged=""
for _candidate in \
    "${DIVINEOS_HOME:-}/operating_mode.txt" \
    "$HOME/.divineos/operating_mode.txt"; do
    case "$_candidate" in
        /operating_mode.txt) continue ;;
    esac
    if [ -f "$_candidate" ] &&
        [ "$(head -n 1 "$_candidate" 2>/dev/null | tr -d '[:space:]')" = "emergency_stop" ]; then # fail-soft: an unreadable candidate yields no stop from THIS path and the loop keeps looking; the Python reader below is still the full check, and this block can only ADD a refusal, never remove one
        _stop_engaged="$_candidate"
        break
    fi
done

if [ -n "$_stop_engaged" ]; then
    _payload="$(cat)"
    case "$_payload" in
    *'"tool_name"'*'"Edit"'* | *'"tool_name"'*'"Write"'* | \
        *'"tool_name"'*'"NotebookEdit"'* | *'"tool_name"'*'"Bash"'*)
        printf '%s\n' '{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "EMERGENCY_STOP is engaged. Refused by the shell-level check, which runs before any library load so a broken library cannot switch the stop off. Clearing it is the operator ceremony; this gate will not clear it."}}'
        ;;
    esac
    exit 0
fi

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

# remedy-allowlist: no gate may block another gate's prescribed exit (Andrew 2026-08-18).
if [ -f "$(dirname "$0")/lib/remedy_allowlist.sh" ]; then
  # HOOK_NAME is read by remedy_pass_through inside the sourced library, and
  # the analyser cannot follow a path built at runtime, so it reports an unused
  # variable and an unresolvable source. Both are it being unable to look, not
  # a defect here. Without the directive below the whole wiring is
  # uncommittable, which is how it came to sit on disk unversioned.
  # shellcheck disable=SC2034
  HOOK_NAME="$(basename "$0")"
  # shellcheck disable=SC1091
  . "$(dirname "$0")/lib/remedy_allowlist.sh"
  remedy_pass_through "$INPUT" || true  # fail-soft: non-zero from remedy_pass_through means NOT-A-REMEDY, which is the ordinary case for almost every command; under set -e that ordinary answer would abort this hook before it ran its own check. The function exits 0 itself when the command IS a remedy some other gate prescribed, so reaching this line at all already means allow-and-continue.
fi

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
