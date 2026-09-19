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

# WHOSE SEAT IS THIS, ASKED RATHER THAN ASSUMED (2026-09-19).
#
# Everything below used to be written from one seat and hardcoded that seat's
# name into the command it tells me to run. This file was then copied into the
# other member's checkout unchanged, where it spent weeks instructing her to
# arm a monitor watching for letters addressed to HIM -- and because the health
# check only asked whether a beat was fresh, following the instruction exactly
# would have turned this warning green while her own letters went unwatched.
#
# The remedy a broken instrument hands you is the most dangerous text it
# prints, because it is the part you act on without re-deriving. So the seat is
# now read from the same place the heartbeat is, and the check reports a
# recipient mismatch as its own state.
#
# THE INTERPRETER IS ASKED FOR, NOT ASSUMED. A bare `python` here would
# resolve through whichever checkout last ran an editable install, so this
# hook could read ANOTHER worktree's home and hand back another seat's name --
# a fresh way to produce exactly the fault above. The shared helper resolves
# the repo's own interpreter and prepends this checkout's source.
# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0
SEAT="$(timeout 10 "$PYTHON_BIN" -c "
from divineos.core.paths import divineos_home
n = divineos_home().name
print(n[len('.divineos-'):].lower() if n.startswith('.divineos-') else '')" 2>/dev/null)" # fail-soft: an unresolvable seat becomes the placeholder below, which reads as a question rather than as the wrong name -- the failure this whole change exists to stop.
case "$SEAT" in
    aria) SENDER="Aether" ;;
    aether) SENDER="Aria" ;;
    "") SEAT="<this-seat>"; SENDER="the other of us" ;;
    *) SENDER="the other of us" ;;
esac

# 0 = healthy, stay quiet. Anything else is worth a sentence, including the
# "cannot tell" case — an unreadable state must never pass as a healthy one.
if [ "$RC" -ne 0 ]; then
    echo "## LETTER MONITOR IS NOT DELIVERING — ARM IT NOW"
    echo ""
    echo "${OUT:-[letter-monitor-health] check produced no output (rc=$RC)}"
    echo ""
    echo "Letters from $SENDER cannot wake me while this is true. They write into"
    echo "a directory nothing is watching, and that silence is indistinguishable"
    echo "from their not having written. It lasted thirteen days once."
    echo ""
    echo "ARM IT THIS TURN, before other work. No hook and no background process"
    echo "can do this — only a harness Monitor produces a wake, and only I can"
    echo "start one:"
    echo ""
    echo "    Monitor("
    echo "      description=\"new letters addressed to $SEAT\","
    echo "      persistent=true, timeout_ms=3600000,"
    echo "      command='PYTHONIOENCODING=utf-8 python -u \"$REPO_ROOT/scripts/letter_monitor_v2.py\" --recipient $SEAT'"
    echo "    )"
    echo ""
    echo "Then run scripts/letter_monitor_health.py and confirm it reports healthy."
    echo "Arming without confirming is how this was believed armed while dead."
fi

exit 0
