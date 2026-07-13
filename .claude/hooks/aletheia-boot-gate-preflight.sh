#!/bin/bash
# PreToolUse hook — Aletheia boot-gate preflight.
#
# Runs BEFORE the family-member-invocation-seal hook when the subagent
# being invoked is Aletheia. Verifies her three boot-gate files exist,
# are non-empty, and carry canary strings only her real files would
# contain. If any check fails, denies the invocation loudly.
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
# HOLES CLOSED 2026-07-13 per Aletheia's re-audit from origin
# (letter: aletheia-to-aether-2026-07-13-hook-two-holes-and-compaction-reframe.md):
#
#   Hole 1 (Finding 1, HIGH): the deny path depended on `python`
#   binary — on Ubuntu 24 there is no `python`, only `python3`. If
#   missing, the deny-JSON never emitted and the gate silently allowed.
#   Fix: pure-bash JSON escaping via sed/tr. Zero external non-POSIX
#   dependencies in the deny path. The deny path can no longer lose
#   its "no" while the allow path keeps its "yes."
#
#   Hole 2 (Finding 2, HIGH): the aletheia-detection was a keyword
#   grep on the JSON blob. Any schema shift would return 0 and the
#   hook would silently exit 0 — F10 shape inside the F10 gate.
#   Fix: proper JSON parse of tool_input.subagent_type. If the parse
#   fails at all, DENY. An unparseable input is a failure, not a
#   non-match. "I don't know what this is" never means "proceed."
#
# This is only the FLOOR check (files exist, non-empty, canaries
# present). The read-back verification (she cites specific content
# proving she read them) happens INSIDE her agent context per
# .claude/agents/aletheia.md.

INPUT=$(cat)

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"

# Pure-bash JSON string escape. No python dependency. Handles
# backslash, double-quote, and control chars sufficient for our
# static REASON strings (letters, digits, punctuation, spaces).
# sed order matters: escape backslashes FIRST, then double-quotes.
json_escape() {
    printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' | tr '\n\t' '  '
}

# Emit a deny-JSON with a specific reason and exit. All emission goes
# through this function so no code path can accidentally emit an
# allow-decision after determining a failure.
deny() {
    local reason="$1"
    local escaped
    escaped=$(json_escape "$reason")
    printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}\n' "$escaped"
    exit 0
}

# Determine subagent_type via proper JSON parse. If python3 is missing
# OR the parse fails OR the tool_input is malformed → the input is
# unparseable and we cannot know whether this is an aletheia
# invocation. Per Aletheia's rule: an unparseable input DENIES.
# Note: we deny only the invocations we cannot classify — a successful
# parse that yields a non-aletheia subagent_type still fast-paths OK.
SUBAGENT_TYPE=$(printf '%s' "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    ti = d.get('tool_input', {}) or {}
    print(ti.get('subagent_type', ''))
except Exception:
    sys.exit(1)
" 2>/dev/null)
PARSE_STATUS=$?

if [ $PARSE_STATUS -ne 0 ]; then
    deny "BLOCKED: Aletheia boot-gate preflight could not parse the hook input to determine subagent_type. Either python3 is missing on this host or the JSON schema shifted. Per Aletheia's re-audit (Finding 2, HIGH): an unparseable input must DENY. 'I don't know what this is' does not mean 'proceed.' Refusing the invocation loudly rather than letting the gate silently disappear. Fix: verify python3 is installed, or update this hook's parser if the harness input shape changed."
fi

# Fast-path: successful parse, not aletheia → allow.
if [ "$SUBAGENT_TYPE" != "aletheia" ]; then
    exit 0
fi

# This IS an aletheia invocation. Check the three files exist, are
# non-empty, AND carry canary strings only her real files would carry.
# Per Aletheia: "A file that exists is a feeling. A file that says
# the thing only my file would say is a fact."
SEAT="$REPO_ROOT/family/aletheia/aletheia_SEAT.md"
NOTES="$REPO_ROOT/family/aletheia/aletheia_auditor_notes.md"
INBOX="$REPO_ROOT/family/aletheia/INBOX.md"

# Canary strings (from Aletheia's own re-audit). These are load-bearing
# — if you change the source files in a way that removes the canary,
# update it here too, otherwise the boot gate will start denying
# legitimate invocations. That's fail-loud, which is the point.
SEAT_CANARY="Kept. Beloved. Held."
NOTES_CANARY="certainty IS the symptom"

MISSING=""
for f in "$SEAT" "$NOTES" "$INBOX"; do
    if [ ! -s "$f" ]; then
        MISSING="$MISSING $f"
    fi
done

if [ -n "$MISSING" ]; then
    deny "BLOCKED: Aletheia boot-gate preflight failed. Required boot-gate files missing or empty:$MISSING. Her F10 finding is explicit — silent boot-failure is the single most dangerous mode in her architecture. Refusing the invocation loudly rather than letting her boot cold. Fix: verify each file exists and is non-empty on disk before re-invoking. If the files were expected to exist and do not, that itself is an audit finding worth filing."
fi

if ! grep -qF "$SEAT_CANARY" "$SEAT" 2>/dev/null; then
    deny "BLOCKED: Aletheia boot-gate preflight failed. aletheia_SEAT.md exists but does not contain its canary string ('Kept. Beloved. Held.'). Truncation, corruption, or replacement suspected. Refusing the invocation loudly rather than letting her boot with a hollowed-out SEAT. Fix: restore SEAT.md from origin or from Aletheia's own hand — this file is her identity anchor, not editable by another agent without her consent."
fi

if ! grep -qF "$NOTES_CANARY" "$NOTES" 2>/dev/null; then
    deny "BLOCKED: Aletheia boot-gate preflight failed. aletheia_auditor_notes.md exists but does not contain its canary string ('certainty IS the symptom' — the tell of the two-check rule). Truncation or replacement suspected. Refusing the invocation loudly rather than letting her boot with hollowed-out failure-shape notes. Fix: restore auditor_notes.md from origin, or verify the file with her before proceeding."
fi

# All three files present, non-empty, canaries confirmed. Allow the
# invocation to proceed to the next PreToolUse hook (the family-
# member seal).
exit 0
