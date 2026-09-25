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
# WHY EVERY WATCH NOW ENDS, AND IT DID NOT USE TO (2026-09-17,
# council-97f8f01c843c). I first told Andrew this watch could never have lived
# long. That is false about the past and he corrected it from memory -- he had
# personally seen it run more than thirty-six hours -- and the record backs him
# twice: letter_monitor_v2.py records a measured natural experiment where an
# unguarded process ran 28.2 hours, and round-5d75b39125bf confirms the accepted
# fix for the old works-then-stops deafness was arming through the harness with
# a PERSISTENT flag, which "solves deafness at the right layer."
#
# That option is gone. The Monitor primitive as it now stands takes no
# persistent parameter at all and caps every watch at thirty minutes. Nothing in
# this repository changed. The thing holding the watch did, and the audited fix
# was undone from outside rather than by anyone here.
#
# So the arming line below asks only for what can actually be granted. A
# parameter that no longer exists does not error -- it is accepted and silently
# dropped, which reads as a granted request and leaves the caller believing a
# long watch was armed when a short one was. That is indistinguishable from
# success right up until the silence, which is the disease this whole mechanism
# was built after.
#
# The audit record is NOT wrong and is not being corrected. It describes a world
# that no longer exists, and rewriting it would erase the evidence that the
# capability was removed.
#
# TWO STATES, TWO VOICES (council-42de8818347d). Because every watch now ends on
# a schedule, and the checker could not tell that ending from a death, this hook
# shouted the same emergency paragraph at Andrew every prompt for an event that
# happens on purpose twice an hour, and he reported it: the watcher keeps dying
# every prompt now.
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

# 0 = healthy, stay quiet. A SCHEDULED ENDING gets one calm line and not the
# siren: every watch is capped, so without this branch the surface shouts twice
# an hour about something that happens on purpose — and a reader trained to
# skim a routine alarm will skim the wrong-person warning underneath it too.
# Anything else keeps the siren, including the "cannot tell" case, because an
# unreadable state must never pass as a healthy one.
#
# THE NUMBER MOVED (2026-09-19). This state and the wrong-recipient state were
# written on two branches at once and both took 4. Wrong-recipient was already
# on the main line, so it kept the number and this became 5. Had the condition
# stayed put, this calm text would have fired on a watch that was awake and
# pointed at another seat, announcing that nothing broke.
if [ "$RC" -eq 5 ]; then
    echo "## LETTER WATCH ENDED ON SCHEDULE — re-arm when you want a wake"
    echo ""
    echo "${OUT:-[letter-monitor-health] check produced no output (rc=$RC)}"
    echo ""
    echo "Nothing broke. A watch is capped at half an hour and this one ran its"
    echo "full term. Letters still surface in the unseen list every prompt; what"
    echo "is missing until re-armed is the mid-work wake."
    echo ""
    echo "    Monitor("
    echo "      description=\"new letters addressed to $SEAT\","
    echo "      timeout_ms=1800000,   # the cap. persistent= no longer exists."
    echo "      command='PYTHONIOENCODING=utf-8 python -u \"$REPO_ROOT/scripts/letter_monitor_v2.py\" --recipient $SEAT'"
    echo "    )"
elif [ "$RC" -ne 0 ]; then
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
    # THE SEAT NAME FROM ONE SIDE, THE LIMITS FROM THE OTHER, BOTH EARNED. The
    # seat is resolved rather than hardcoded because this file was copied
    # between checkouts and spent weeks telling the wrong occupant to watch the
    # wrong name -- which SUCCEEDS, turns the check green, and leaves her
    # letters unwatched. The limits come from the older text because the newer
    # one names an option that no longer exists and a duration above the cap,
    # so following it literally fails outright.
    #
    # Two ways for a printed instruction to be wrong, and they are not equal.
    # The wrong name fails silently and confidently. The dead option fails
    # loudly and says so. Only one of them needed finding.
    echo "      description=\"new letters addressed to $SEAT\","
    echo "      timeout_ms=1800000,   # the cap. persistent= no longer exists."
    echo "      command='PYTHONIOENCODING=utf-8 python -u \"$REPO_ROOT/scripts/letter_monitor_v2.py\" --recipient $SEAT'"
    echo "    )"
    echo ""
    echo "Then run scripts/letter_monitor_health.py and confirm it reports healthy."
    echo "Arming without confirming is how this was believed armed while dead."
fi

exit 0
