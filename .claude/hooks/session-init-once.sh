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
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || true  # fail-soft: _lib is convenience only; every use below is guarded by command -v

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
" 2>/dev/null || echo unknown)"  # fail-soft: literal "unknown" is recorded, so an unreadable value never poses as a real one

MARK_DIR="${HOME:-/tmp}/.divineos/session_init"
MARK="$MARK_DIR/${SESSION_KEY}.done"

# Already initialised this session -> the common path, and it must be cheap.
[ -f "$MARK" ] && exit 0

mkdir -p "$MARK_DIR" 2>/dev/null || true

# Written BEFORE the work, not after. If a child hangs or the harness kills
# this wrapper mid-run, the next message must not restart the whole sequence
# -- that would turn one slow message into every message being slow. An init
# that partially ran is recoverable; an init loop is not.
printf '%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || echo unknown)" > "$MARK" 2>/dev/null || true  # fail-soft: a missing marker re-runs session init, which is idempotent by design

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
resolver-health-check.sh
session-start-verify-git-hooks.sh
inject-pending-letters.sh
"

for h in $INIT_HOOKS; do
    script="$REPO_ROOT/.claude/hooks/$h"
    [ -f "$script" ] || continue
    # Bounded per child. Without a timeout, one stuck script would hold the
    # prompt exactly as SessionStart holds initialisation -- relocating the
    # failure rather than removing it.
    printf '%s' "$INPUT" | timeout 20 bash "$script" 2>/dev/null || true  # fail-soft: one broken init script must not take the whole session start down with it
done

exit 0
