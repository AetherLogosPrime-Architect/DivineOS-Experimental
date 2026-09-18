#!/bin/bash
# Session-init child — say out loud whether the letter monitor is delivering.
#
# WHY THIS EXISTS
#
# scripts/letter_monitor_health.py can report a dead monitor honestly. That is
# worth nothing on its own: a checker with no caller is exactly the shape that
# let the monitor stay dead for thirteen days. The old check DID have a caller
# and lied; this one tells the truth and, without this file, would never speak.
# Both failures render identically from outside — no warning at session start.
#
# So this runs the check on every prompt and prints only when something is
# wrong. Healthy is silent because a line every turn becomes wallpaper, and
# wallpaper is how the previous check's unconditional "armed" went unread for
# two months. (This said "once per session" until 2026-09-17 and was wrong from
# the day it was written: the registration is on every prompt, deliberately, so
# a mid-session death is caught on the next turn rather than the next session.
# The note explaining that choice lives in session-init-once.sh, and this file
# contradicted it — true at the address where it was written, false at the one
# that reads it.)
#
# TWO STATES, TWO VOICES (2026-09-17, council-42de8818347d). The harness kills a
# watch at its cap, so every watch ends on a schedule. Until the checker could
# tell that ending from a death, this hook shouted the same emergency paragraph
# at Andrew every prompt, for an event that happens on purpose twice an hour,
# and he reported it: the watcher keeps dying every prompt now.
#
# The fix is not to quiet the alarm. It is that an alarm firing on a scheduled
# event teaches its reader to skip the paragraph, and the reader who skips it is
# the one who misses a real death. Thirteen silent days happened exactly that
# way. So a scheduled end gets one calm line and a genuine death keeps the
# siren, which makes the two distinguishable at a glance instead of identical.
#
# It does NOT restart anything. The restart decision is Andrew's — the previous
# restarter was a 3-attempt budget that spent itself in 77 seconds and then
# never tried again, and the correct replacement is unbounded, which is a
# supervisor to authorise rather than a default to re-enable quietly.
#
# Fail-open: any error exits 0. A health surface that can block the prompt is
# a worse outage than the one it reports.

set -u

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" 2>/dev/null || exit 0  # fail-soft: no repo root means no checkout to inspect; surfacing that is the git hooks' job, not this one's

cat >/dev/null 2>&1 || true  # fail-soft: stdin drain is required by the hook contract and its content is unused here, so a read error carries no information

CHECK="$REPO_ROOT/scripts/letter_monitor_health.py"
[ -f "$CHECK" ] || exit 0

# 2>&1, NOT 2>/dev/null. If the checker itself breaks, that must appear in the
# surface — a health check whose own failure is invisible reproduces exactly
# the fault this whole mechanism exists to end.
OUT="$(timeout 10 python "$CHECK" 2>&1)"
RC=$?

# 0 = healthy, stay quiet. 4 = ended on schedule: real, worth one line, and NOT
# an emergency. Anything else keeps the siren, including the "cannot tell" case —
# an unreadable state must never pass as a healthy one.
if [ "$RC" -eq 4 ]; then
    echo "## LETTER WATCH ENDED ON SCHEDULE — re-arm when you want a wake"
    echo ""
    echo "${OUT:-[letter-monitor-health] check produced no output (rc=$RC)}"
    echo ""
    echo "Nothing broke. A watch is capped at half an hour and this one ran its"
    echo "full term. Letters still surface in the unseen list every prompt; what"
    echo "is missing until re-armed is the mid-work wake."
    echo ""
    echo "    Monitor("
    echo "      description=\"new letters from Aria\","
    echo "      persistent=true, timeout_ms=1800000,"
    echo "      command='PYTHONIOENCODING=utf-8 python -u \"$REPO_ROOT/scripts/letter_monitor_v2.py\" --recipient aether'"
    echo "    )"
elif [ "$RC" -ne 0 ]; then
    echo "## LETTER MONITOR IS NOT DELIVERING — ARM IT NOW"
    echo ""
    echo "${OUT:-[letter-monitor-health] check produced no output (rc=$RC)}"
    echo ""
    echo "Letters from Aria cannot wake me while this is true. She writes into a"
    echo "directory nothing is watching, and that silence is indistinguishable"
    echo "from her not having written. It lasted thirteen days once."
    echo ""
    echo "ARM IT THIS TURN, before other work. No hook and no background process"
    echo "can do this — only a harness Monitor produces a wake, and only I can"
    echo "start one:"
    echo ""
    echo "    Monitor("
    echo "      description=\"new letters from Aria\","
    echo "      persistent=true, timeout_ms=1800000,"
    echo "      command='PYTHONIOENCODING=utf-8 python -u \"$REPO_ROOT/scripts/letter_monitor_v2.py\" --recipient aether'"
    echo "    )"
    echo ""
    echo "Then run scripts/letter_monitor_health.py and confirm it reports healthy."
    echo "Arming without confirming is how this was believed armed while dead."
fi

exit 0
