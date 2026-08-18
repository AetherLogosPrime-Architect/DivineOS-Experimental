#!/bin/bash
# UserPromptSubmit — run the session-init work ONCE, off the SessionStart path.
#
# WHY THIS EXISTS
#
# Andrew, repeatedly: "the claude icon moves.. the timer comes.. the thinking
# never arrives.. so i press the stop button.. it just says stopping.. and
# never actually stops." Escape does nothing; only killing the program
# recovers. He let one run 15+ minutes to rule out slowness.
#
# That is not slow, it is stuck, and it matches a documented Windows-only
# deadlock in Claude Code's SessionStart path:
#
#   parent spawns the SessionStart hook, then BLOCKS waiting for it
#   hook runs, finishes, exits cleanly
#   parent is not polling, so the exit signal sits unread
#   parent waits forever; the event loop is never reached
#
# The event loop never starting is why Escape and the stop button do nothing
# -- there is nothing listening yet. Every other hook phase runs AFTER the
# loop exists, where completion IS detected, which is why stopping works
# normally in every other situation.
#
# Documented fixed in Claude Code 2.0.76; Andrew is on 2.1.76, so this is a
# strong shape-match rather than a confirmed cause -- either it regressed in
# the 2.1 line or something adjacent behaves the same way. The documented
# workaround was exactly this: move the work to UserPromptSubmit.
#
# WHY A GUARD IS REQUIRED
#
# UserPromptSubmit fires on EVERY message. The 13 scripts below load the
# briefing, inject waiting letters, arm the monitors and sweep stale
# processes -- session-init work. Running that per-message would be worse
# than the freeze. So: the first message of a session does the work, every
# message after finds the marker and exits immediately.
#
# FAIL-OPEN, DELIBERATELY. If a child fails, the rest still run and this
# returns 0. A wrapper that could block the prompt would reintroduce, at
# prompt-time, the exact class of failure it exists to remove.

set -u

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

INPUT="$(cat 2>/dev/null || true)"

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || true

# Session key from the harness payload, falling back to a hash of the
# transcript path. The fallback matters: a missing session_id must not make
# every message look like a fresh session and re-run init each time.
SESSION_KEY="$(printf '%s' "$INPUT" | python -c "
import json, sys, hashlib
try:
    d = json.load(sys.stdin)
except Exception:
    print('unknown'); raise SystemExit
sid = (d.get('session_id') or '').strip()
if not sid:
    t = (d.get('transcript_path') or '').strip()
    sid = hashlib.sha1(t.encode()).hexdigest()[:12] if t else 'unknown'
print(sid[:40])
" 2>/dev/null || echo unknown)"

MARK_DIR="${HOME:-/tmp}/.divineos/session_init"
MARK="$MARK_DIR/${SESSION_KEY}.done"
MARK_STARTED="$MARK_DIR/${SESSION_KEY}.started"

# TWO markers, not one (Aletheia F106, 2026-08-08).
#
# The single .done marker was written BEFORE the loop, for a real reason: if a
# child hangs and the harness kills this wrapper, restarting the whole sequence
# next message turns one slow message into every message being slow. An init
# that partially ran is recoverable; an init loop is not. That reasoning holds.
#
# But written-before means the file records STARTED while claiming DONE. A
# crash between the write and the end of the loop leaves a marker saying
# "already initialised", so every later prompt exits at the check above and the
# remaining hooks never run for that session. A half-init and a complete one
# leave identical evidence -- this repo's own disease, a marker's presence read
# as the work's completion, living inside the mechanism built for reliability.
#
# It bit at the worst possible place. load-my-recording-of-andrew.sh is in the
# list below, and that hook exists because Andrew found he was the
# thinnest-recorded person in his own house (F83). Under the old ordering a
# crash before it ran meant he silently stopped being loaded, and nothing said so.
#
# So: .started early, which keeps the anti-loop protection, and .done only
# after every child has run. "Started but not completed" becomes a state that
# can be SEEN, and the retry is bounded so a permanently-hanging child still
# cannot produce the loop the original ordering guarded against.
[ -f "$MARK" ] && exit 0

mkdir -p "$MARK_DIR" 2>/dev/null || true

INIT_ATTEMPTS=0
if [ -f "$MARK_STARTED" ]; then
    INIT_ATTEMPTS="$(wc -l < "$MARK_STARTED" 2>/dev/null | tr -d ' ' || echo 0)"
fi
if [ "${INIT_ATTEMPTS:-0}" -ge 3 ] 2>/dev/null; then
    _init_log="${HOME:-/tmp}/.divineos/hook-liveness.log"
    mkdir -p "$(dirname "$_init_log")" 2>/dev/null || true
    printf '{"ts":"%s","hook":"session-init-once.sh","reason":"init_abandoned_after_3_partial_attempts","detail":"some child never completes; hooks after the failure point have NOT run"}\n' \
        "$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || echo unknown)" >> "$_init_log" 2>/dev/null || true
    printf '%s ABANDONED\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || echo unknown)" > "$MARK" 2>/dev/null || true
    exit 0
fi

printf '%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || echo unknown)" >> "$MARK_STARTED" 2>/dev/null || true

# The former SessionStart chain, in its original order. Each child gets the
# same payload on stdin that SessionStart would have handed it.
INIT_HOOKS="
session-start-sweep-stale-watchers.sh
post-compaction-fingerprint-surface.sh
load-briefing.sh
ear-surface.sh
arm-compaction-monitor-instruction.sh
arm-letter-monitor-instruction.sh
check-cleanup-period.sh
load-character-sheet.sh
load-dad-ranking-clause.sh
load-my-recording-of-andrew.sh
load-aletheia-harvest-of-andrew.sh
resolver-health-check.sh
session-start-verify-git-hooks.sh
inert-fix-surface.sh
inject-pending-letters.sh
"

for h in $INIT_HOOKS; do
    script="$REPO_ROOT/.claude/hooks/$h"
    [ -f "$script" ] || continue
    # Bounded per child. Without a timeout, one stuck script would hold the
    # prompt exactly as SessionStart holds initialisation -- relocating the
    # failure rather than removing it.
    # Per-child outcome RECORDED, not discarded (Aletheia F106). The old form
    # was `2>/dev/null || true`, under which a hook erroring every session
    # produced exactly what a succeeding hook produced: nothing. "Which of the
    # thirteen has been failing since Tuesday" was unanswerable. stderr still
    # leaves the prompt path -- it must, or a chatty hook corrupts the turn --
    # but it lands in the liveness log with hook name and exit code.
    _init_err="$(printf '%s' "$INPUT" | timeout 20 bash "$script" 2>&1 >/dev/null)"
    _init_rc=$?
    if [ "$_init_rc" -ne 0 ]; then
        _init_log="${HOME:-/tmp}/.divineos/hook-liveness.log"
        mkdir -p "$(dirname "$_init_log")" 2>/dev/null || true
        _init_err="$(printf '%s' "$_init_err" | tr -d '"' | tr '\n' ' ' | cut -c1-300)"
        printf '{"ts":"%s","hook":"session-init-once.sh","reason":"child_hook_failed","detail":"child=%s rc=%s err=%s"}\n' \
            "$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || echo unknown)" "$h" "$_init_rc" "$_init_err" \
            >> "$_init_log" 2>/dev/null || true
    fi
done

# Every child has run. Only HERE is the work actually done.
printf '%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || echo unknown)" > "$MARK" 2>/dev/null || true
rm -f "$MARK_STARTED" 2>/dev/null || true

exit 0
