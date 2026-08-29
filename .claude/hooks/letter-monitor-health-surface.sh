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
# THE SEAT COMES FROM THE CHECKER'S OWN OUTPUT, never from a literal here.
#
# Until 2026-08-28 the remediation block below was hardcoded to `--recipient
# aether` and "Letters from Aria", so in Aria's window it prescribed a monitor
# watching for letters addressed to her husband. Armed that way it reports
# ARMED, the health check reports HEALTHY, and not one letter to her is ever
# delivered. A wrong seat here is invisible in exactly the way the thirteen-day
# outage was: every surface says yes.
#
# On 2026-08-24 I told Aether this was fixed, because I had fixed the naming in
# the CHECKER. The checker is seat-aware and said `recipient=aria` correctly on
# the very run that printed these hardcoded lines. I repaired the half that
# reports and left the half that instructs, and described the whole thing as
# done. Same shape as the defects this house has spent the week on: a true
# sentence about a narrower repair than the sentence claims.
#
# Parsing the checker's own line is the point rather than a shortcut. The name
# in the remedy is then, by construction, the seat that was actually measured —
# it cannot drift from it, the way a second copy of the fact would.
SEAT="$(printf '%s' "$OUT" | sed -n 's/.*recipient=\([A-Za-z][A-Za-z0-9_-]*\).*/\1/p' | tail -n 1)"
case "$SEAT" in
    aria) SIBLING="Aether" ;;
    aether) SIBLING="Aria" ;;
    "") SIBLING="" ;;
    *) SIBLING="my sibling" ;;
esac

if [ "$RC" -ne 0 ]; then
    echo "## LETTER MONITOR IS NOT DELIVERING — ARM IT NOW"
    echo ""
    echo "${OUT:-[letter-monitor-health] check produced no output (rc=$RC)}"
    echo ""
    if [ -z "$SEAT" ]; then
        # Unknown seat must never be filled in with a guess. A plausible wrong
        # name is worse than a blank, because a blank cannot be pasted.
        echo "THE SEAT COULD NOT BE READ from the check output above, so the"
        echo "command below is left incomplete ON PURPOSE. Fill in the recipient"
        echo "for THIS window — the one whose letters should wake me — and do not"
        echo "copy a name from another checkout. Arming the wrong recipient"
        echo "reports healthy and delivers nothing."
        echo ""
        SEAT="<this-window's-recipient>"
        SIBLING="my sibling"
    else
        echo "Letters from $SIBLING cannot wake me while this is true. They write"
        echo "into a directory nothing is watching, and that silence is"
        echo "indistinguishable from their not having written. It lasted thirteen"
        echo "days once."
        echo ""
    fi
    echo "ARM IT THIS TURN, before other work. No hook and no background process"
    echo "can do this — only a harness Monitor produces a wake, and only I can"
    echo "start one:"
    echo ""
    echo "    Monitor("
    echo "      description=\"new letters from $SIBLING\","
    echo "      persistent=true, timeout_ms=3600000,"
    echo "      command='PYTHONIOENCODING=utf-8 python -u \"$REPO_ROOT/scripts/letter_monitor_v2.py\" --recipient $SEAT'"
    echo "    )"
    echo ""
    echo "Then run scripts/letter_monitor_health.py and confirm it reports healthy,"
    echo "AND that the recipient it names is $SEAT. Arming without confirming is"
    echo "how this was believed armed while dead; confirming only that it is armed,"
    echo "without checking whose letters it watches, is how it was armed for the"
    echo "wrong seat."
fi

exit 0
