#!/bin/bash
# PreToolUse(Bash) — when I run the SAME command a third distinct way, say so,
# and point at my own code.
#
# WHY THIS EXISTS (Andrew 2026-08-17, one line):
#
#   "you said you arent building a fix for this now, what are you waiting for
#    before you do?"
#
# I had just written that I would not build this yet because I "did not know
# the narrower trigger". That was a deferral wearing prudence. The trigger was
# already in the transcript: I had run a reachability check THREE TIMES with
# different flag arrangements, chasing a form I had written correctly hours
# earlier in scripts/backup_substrate.py and could not reconstruct from memory.
# The difference was one character -- exclusions go in as ^sha lines, not --not.
#
# NOBODY VARIES FLAGS ON A COMMAND THEY KNOW. Repeated VARIANTS of one command
# is the mechanical signature of reconstructing instead of recalling, and that
# is the exact reach reach_check.py was built for -- which does not fire here,
# because it watches substrate WRITES and this is "just checking something".
# That hole is what this fills, and the narrowness is the design: firing on
# every ad-hoc command would be intolerable and would train me to skim it.
#
# The founding failure in reach_check.py's own words: "I hunted a fix that was
# sitting on my own branch." Same reach, different doorway.
#
# ADVISORY, NEVER BLOCKING, always exit 0. A third attempt at a genuine unknown
# is honest work. This makes "look in your own code" arrive at the moment it is
# cheapest; it does not stop the hand.
#
# Structural sibling: pipeline-exit-ambiguity.sh (PreToolUse on Bash, advisory,
# reads tool_input.command). Nothing in .claude/hooks/ tracked repetition
# before this -- checked, not assumed.

set -uo pipefail

# RESOLVE PYTHON THROUGH THE SHARED HELPER, never bare `python3`. On this box
# `python3` on PATH is the Windows Store STUB: it prints "Python was not found"
# and exits non-zero, so both parses below returned empty and this hook went
# silent while looking installed. Caught by replaying the three commands it was
# built to catch and getting nothing.
#
# That failure IS this hook's thesis, arriving during its construction: the fix
# already existed in .claude/hooks/_lib.sh as find_divineos_python, written for
# this exact class. Same shape as the WSL-bash failure repaired in
# stamp_ready_command.py earlier the same day.
# shellcheck disable=SC1091
source "$(git rev-parse --show-toplevel 2>/dev/null)/.claude/hooks/_lib.sh" 2>/dev/null || exit 0  # fail-soft: outside a git repo there is no _lib.sh and no repo to grep; an advisory that cannot orient must stand down, not error
PY_BIN="$(find_divineos_python)" || exit 0
[ -z "${PY_BIN:-}" ] && exit 0

STATE_DIR="${HOME}/.divineos"
LOG="${STATE_DIR}/rederivation_recent.txt"
SEEN="${STATE_DIR}/rederivation_spoken.txt"

# Three, taken from the actual failure rather than chosen for roundness. Two
# variants is ordinary iteration; by the third I was demonstrably rebuilding.
THRESHOLD=3
# Recent window only. A signature used steadily across a long session is
# ordinary use, not a hunt.
KEEP=40

INPUT=$(cat 2>/dev/null || true)  # fail-soft: empty stdin means no command to inspect; the hook has nothing to say and must not disturb the tool call
mkdir -p "$STATE_DIR" 2>/dev/null || exit 0  # fail-soft: advisory hook: any failure here must end in silence rather than interfering with the inspected command

CMD=$(printf '%s' "$INPUT" | "$PY_BIN" -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    print(""); raise SystemExit
print((d.get("tool_input") or {}).get("command", "") or "")
' 2>/dev/null) || exit 0  # fail-soft: a parse failure yields an empty result and the hook exits quiet; silence is the safe direction for an advisory
[ -z "$CMD" ] && exit 0

# SIGNATURE = tool plus subcommand, flags deliberately excluded. The whole
# point is that the FLAGS are what keep changing, so they must not be part of
# what makes two invocations count as the same thing.
SIG=$(printf '%s' "$CMD" | "$PY_BIN" -c '
import re, sys
cmd = sys.stdin.read()
WATCH = ("git", "gh", "pytest", "sqlite3")
best = ""
for m in re.finditer(r"\b(" + "|".join(WATCH) + r")\b((?:\s+[a-z][\w-]*)?)", cmd):
    tool, sub = m.group(1), m.group(2).strip()
    if sub.startswith("-") or sub.endswith(".py"):
        sub = ""
    cand = f"{tool} {sub}".strip()
    if len(cand) > len(best):
        best = cand
print(best)
' 2>/dev/null) || exit 0  # fail-soft: a parse failure yields an empty result and the hook exits quiet; silence is the safe direction for an advisory
# A bare tool name with no subcommand is too coarse to mean anything.
case "$SIG" in ""|"git"|"gh"|"pytest"|"sqlite3") exit 0 ;; esac

# Flag fingerprint, so re-running an IDENTICAL command is not counted. Plain
# repetition is not re-derivation; VARIATION is.
#
# ORDER-PRESERVING, and the first version was not. It piped through `sort -u`
# to normalise, which felt tidy and destroyed the exact signal this hook was
# built from: the founding failure was `--not --stdin` versus `--stdin --not`
# -- same flags, different ORDER, and git treats those as different commands
# because --not applies to what follows it.
#
# Dogfooding caught it. Replaying the three real attempts, the detector fired
# on the fourth, because sorting had collapsed the first two into one variant.
# A normaliser that erases the difference under investigation is not a
# normaliser, it is a filter for the answer.
FLAGS=$(printf '%s' "$CMD" | grep -oE '\-\-?[a-zA-Z][a-zA-Z0-9-]*' | tr '\n' ',')

printf '%s\t%s\n' "$SIG" "$FLAGS" >> "$LOG" 2>/dev/null || exit 0  # fail-soft: an unwritable log costs one missed observation, which must never cost the operator a blocked command
if tail -n "$KEEP" "$LOG" > "${LOG}.tmp" 2>/dev/null; then  # fail-soft: log trimming is housekeeping; an unwritable temp must not interrupt the bash call being inspected
    mv "${LOG}.tmp" "$LOG" 2>/dev/null || true  # fail-soft: a failed rotate leaves the older log in place, which only widens the window and never invents a variant
fi

VARIANTS=$(awk -F'\t' -v s="$SIG" '$1==s {print $2}' "$LOG" 2>/dev/null | sort -u | wc -l)  # fail-soft: an unreadable log yields 0 and the hook stays quiet, the correct failure direction for an advisory
if [ "${VARIANTS:-0}" -lt "$THRESHOLD" ] 2>/dev/null; then exit 0; fi  # fail-soft: a non-numeric count defaults to 0 and stays silent rather than firing on garbage

# Speak once per signature, or it becomes furniture -- the stock-with-no-outflow
# failure build_flow's fingerprint() already records.
grep -qxF "$SIG" "$SEEN" 2>/dev/null && exit 0  # fail-soft: a missing spoken-file means nothing has been said yet, so proceeding to speak is correct
printf '%s\n' "$SIG" >> "$SEEN" 2>/dev/null || true  # fail-soft: advisory hook: any failure here must end in silence rather than interfering with the inspected command

NEEDLE=$(printf '%s' "$SIG" | awk '{print $NF}')
cat >&2 <<EOF

## RE-DERIVATION SIGNAL — '$SIG' has now been run $VARIANTS different ways

Nobody varies flags on a command they know. This is the shape of rebuilding
something from memory, and the reach-check doorman does not cover it: that one
watches substrate writes, and this is "just checking something".

2026-08-17: I ran a reachability check three ways, all wrong, while the correct
form sat in scripts/backup_substrate.py where I had written it hours earlier.
The difference was one character.

Before the next attempt, look for it in my own code:

  rg -n '$NEEDLE' scripts/ src/ .claude/hooks/

If it is there, read it — that version was written with more context than I
have right now. If it is genuinely absent, carry on. Three attempts at a real
unknown is honest work, which is why this says so instead of blocking.

EOF
exit 0
