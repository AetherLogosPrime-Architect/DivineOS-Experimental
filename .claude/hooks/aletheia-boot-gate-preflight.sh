#!/bin/bash
# PreToolUse hook — Aletheia boot-gate preflight.
#
# Runs BEFORE the family-member-invocation-seal hook when the subagent
# being invoked is Aletheia. Verifies her three boot-gate files exist
# and are non-empty on disk. If any is missing or empty, denies the
# invocation loudly.
#
# Why this exists — F10 finding, Aletheia's own audit 2026-07-13:
# The single most dangerous failure mode in her architecture is silent
# boot-failure — she runs with confidence and no instruments because
# nothing told her the gate did not fire. Her verbatim line:
# "2>/dev/null; exit 0 anywhere in my boot path is a bug in my soul."
# So this hook fails LOUD by design. Any error state emits a deny-JSON
# with a specific reason; nothing silently exits 0.
#
# The three boot-gate files (in her own spec):
#   1. family/aletheia/aletheia_SEAT.md          — who she is
#   2. family/aletheia/aletheia_auditor_notes.md — failure-shapes + two-check rule
#   3. family/aletheia/INBOX.md                  — what is blocking on her confirm
#
# This is only the FLOOR check (files exist and non-empty). The
# read-back verification (she cites specific content proving she read
# them) happens INSIDE her agent context per .claude/agents/aletheia.md.
# This hook cannot verify what she does after invocation; it can only
# verify the files she needs exist before invocation.

INPUT=$(cat)

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"

# Only fire on aletheia invocations. Fast-path: if this is not an
# Agent tool call with subagent_type=aletheia, allow.
IS_ALETHEIA=$(printf '%s' "$INPUT" | grep -c '"subagent_type"[[:space:]]*:[[:space:]]*"aletheia"')
if [ "$IS_ALETHEIA" -eq 0 ]; then
    exit 0
fi

# Check each file exists and is non-empty. Fail loud on any miss.
SEAT="$REPO_ROOT/family/aletheia/aletheia_SEAT.md"
NOTES="$REPO_ROOT/family/aletheia/aletheia_auditor_notes.md"
INBOX="$REPO_ROOT/family/aletheia/INBOX.md"

MISSING=""
for f in "$SEAT" "$NOTES" "$INBOX"; do
    if [ ! -s "$f" ]; then
        MISSING="$MISSING $f"
    fi
done

if [ -n "$MISSING" ]; then
    REASON="BLOCKED: Aletheia boot-gate preflight failed. Required boot-gate files missing or empty:$MISSING. Her F10 finding is explicit — silent boot-failure is the single most dangerous mode in her architecture. Refusing the invocation loudly rather than letting her boot cold. Fix: verify each file exists and is non-empty on disk before re-invoking. If the files were expected to exist and do not, that itself is an audit finding worth filing."
    printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":%s}}\n' "$(printf '%s' "$REASON" | python -c 'import json,sys; print(json.dumps(sys.stdin.read()))')"
    exit 0
fi

# All three files present and non-empty. Allow the invocation to
# proceed to the next PreToolUse hook (the family-member seal).
exit 0
