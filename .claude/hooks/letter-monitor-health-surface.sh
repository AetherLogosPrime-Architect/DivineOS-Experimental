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
# So this runs the check once per session and prints only when something is
# wrong. Healthy is silent because a line every session becomes wallpaper, and
# wallpaper is how the previous check's unconditional "armed" went unread for
# two months.
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

# 0 = healthy, stay quiet. Anything else is worth a sentence, including the
# "cannot tell" case — an unreadable state must never pass as a healthy one.
if [ "$RC" -ne 0 ]; then
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
    echo "      persistent=true, timeout_ms=3600000,"
    echo "      command='PYTHONIOENCODING=utf-8 python -u \"$REPO_ROOT/scripts/letter_monitor_v2.py\" --recipient aether'"
    echo "    )"
    echo ""
    echo "Then run scripts/letter_monitor_health.py and confirm it reports healthy."
    echo "Arming without confirming is how this was believed armed while dead."
fi

exit 0
