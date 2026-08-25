#!/bin/bash
# PreToolUse — fire bypass_rate_scan on substrate-modifying tool calls.
# Wires the EvidenceBearingStopGate CrossTurnScan concrete instance
# (bypass_rate_scan) into actual enforcement, closing the loop that
# Andrew flagged 2026-07-15: "if they are not wired how do you expect
# them to work?"
#
# Fires when:
#   - Bypass rate exceeds threshold in the recent window AND
#   - No investigation-shape action (GATE_CLEARANCE for bypass_rate_scan,
#     AUDIT_ROUND_CREATED, or CLAIM_FILED) has occurred since the most
#     recent GATE_FIRE for this gate.
#
# Clearing:
#   - divineos audit submit-round '<focus>' --actor external-auditor
#   - divineos claim '<statement>'
#   - Any GATE_CLEARANCE event for bypass_rate_scan
#
# Fail-open: any hook failure exits 0 so the gate cannot break work.
#
# Kill-switch (requires >=20 char reason in marker file). The path comes from
# member_home(), which for aether is the DEFAULT ~/.divineos/ -- this comment
# used to hand-write ~/.divineos-aether/ and that is where a marker sat unseen
# for forty days holding this gate off. The code was fixed 2026-08-25 and this
# line with it, because a doc that teaches the wrong path reinstalls the bug
# every time someone reads it:
#   echo "why this bypass is needed and root-cause plan" > "$(member_home aether)/bypass-rate-scan.disabled"

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

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0

PYTHON_BIN="$(find_divineos_python)"
if [ -z "$PYTHON_BIN" ]; then
    exit 0
fi

# THE SIXTH SITE THAT REBUILT THE HOME RULE. (2026-08-25.)
#
# This was `$HOME/.divineos-aether/bypass-rate-scan.disabled`, hand-built.
# core/paths.py:member_home() is the one place that knows the convention and
# special-cases aether to the default `~/.divineos/`; its docstring ends
# "Callers ask here; nobody rebuilds the rule." The 2026-08-18 consolidation
# swept three shell hooks. It missed this one, family/letter_seen.py, and
# ear-surface.sh -- the sweep was scoped by directory, the defect by
# behaviour.
#
# The consequence was not cosmetic. A marker written here 2026-07-16 held
# this gate off for forty days in a home nothing else reads, and retiring it
# today is what re-armed the gate. A kill-switch nobody can see is worse than
# one nobody honours.
# shellcheck disable=SC1091
. "$(dirname "$0")/lib/member_home.sh"
MEMBER="${DIVINEOS_MEMBER:-aether}"
MARKER="$(member_home "$MEMBER" "$PYTHON_BIN")/bypass-rate-scan.disabled"
if [ -f "$MARKER" ]; then
    REASON=$(tr -d '\r' < "$MARKER")
    if [ ${#REASON} -ge 20 ]; then
        exit 0
    fi
fi

TOOL_NAME=$(printf '%s' "$INPUT" | "$PYTHON_BIN" -c "import json,sys; d=json.loads(sys.stdin.read() or '{}'); print(d.get('tool_name',''))" 2>/dev/null)

case "$TOOL_NAME" in
    Write|Edit|MultiEdit|NotebookEdit)
        ;;
    Bash)
        COMMAND=$(printf '%s' "$INPUT" | "$PYTHON_BIN" -c "import json,sys; d=json.loads(sys.stdin.read() or '{}'); print(d.get('tool_input',{}).get('command',''))" 2>/dev/null)
        case "$COMMAND" in
            *"git commit"*|*"git push"*)
                ;;
            *)
                exit 0
                ;;
        esac
        ;;
    *)
        exit 0
        ;;
esac

OUTPUT=$(printf '%s' "$INPUT" | "$PYTHON_BIN" -m divineos.hooks.bypass_rate_hook 2>&1)
EXIT_CODE=$?

if [ "$EXIT_CODE" -eq 2 ]; then
    printf '%s\n' "$OUTPUT" >&2
    exit 2
fi

exit 0
