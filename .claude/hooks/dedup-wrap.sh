#!/usr/bin/env bash
# WIRED FOR ONE PRIME (2026-09-18, council-3082d65c0b27). The parked header
# that stood here said the day a floor file exists, this claim is stale and
# should be challenged. One exists. This is the challenge, taken.
#
# WHAT EXPIRED IT: translate-first now has a floor at
# .claude/hooks/residuals/translate-first.txt. Andrew asked the same question
# twice — "is something being injected every post" on 2026-09-17, and again on
# 2026-09-18 after nothing had changed. The mechanism was built the first time
# and the JUDGMENT WORK, naming each floor, was not. That gap is the entire
# distance between a parked fix and a live one, and it is a day wide.
#
# VERIFIED BEFORE WIRING, both directions: 9,625 chars on first sight, 1,329 on
# repeat, floor intact. The first floor I wrote was 2,659 bytes and THIS WRAPPER
# REFUSED IT as over the cap — the exact game-walk route I had filed ninety
# seconds earlier, walked anyway, caught by the mechanism rather than by me.
#
# THE ORIGINAL CONDITION, kept verbatim because it still binds the rest: this
# cannot be wired for a prime until that prime has a floor file at
# .claude/hooks/residuals/<source_id>.txt naming what survives suppression.
# Anyone can look in that directory and see which primes still lack one.
#
# WHAT REMAINS — AND MY FIRST VERSION OF THIS LIST WAS MEASURED AGAINST THE
# WRONG THING. It said "still unwrapped" and named five primes with their repeat
# rates. "Unwrapped" is true of anything without this wrapper in front of it, and
# it READS as "still emits in full every turn". Those are different claims and
# only the narrow one was true: FOUR primes suppress themselves by calling the
# dedup machinery directly, and one of them was on my list.
#
# A reader trusting that list would wrap a prime that already suppresses, get
# nothing for the work, and believe the job was done. So the category is split
# rather than the entry corrected — a list of BEHAVIOUR survives a prime changing
# routes, a list of wrapper-membership does not.
#
# SELF-SUPPRESSING ALREADY, no wrapper needed: wallclock, circle-first,
# closure-word, self-demotion. Measured by what they import, after a first probe
# that matched on their OUTPUT TEXT and returned thirty wrong answers.
#
# EMIT IN FULL AND REPEAT ENOUGH TO BE WORTH A FLOOR, by measured rate
# 2026-09-18: register-awareness 89%, ear-surface 82%, interior-cue 76%,
# family-state 76%.
#
# DELIBERATELY NOT WRAPPED: the wallclock prime's body repeats 0% because it
# prints the current minute, and active-needs 0.3%. Wrapping either suppresses
# nothing and manufactures the appearance of a fix.
#
# WHY IT IS NOT SIMPLY DELETED, since that case is strong: Andrew reframed what
# this does as a stopgap — it answers whether TEXT repeated, not whether the
# thing was already in mind — and Aria supplied the design that answers the real
# question. But the measurement that prompted it stands unaddressed: roughly
# 6500 tokens ahead of every prompt and 2500 riding each substrate-touching
# call, much of it byte-identical repetition. Deleting the response does not
# delete the cost.
#
# dedup-wrap.sh — put context_dedup in FRONT of a prime instead of inside it.
#
# WHY THIS EXISTS. Andrew 2026-09-17: "is something being injected every post?
# if so that is wallpaper and needs fixed." Measured before touching anything:
# 26115 characters -- roughly 6500 tokens -- emitted into EVERY prompt across
# 35 UserPromptSubmit hooks, of which 9 emit at all and 26 are silent. One
# prime alone was a third of it, re-printed byte-identical on every turn of a
# long session.
#
# The dedup machinery already existed (core/context_dedup.py, built 2026-06-30
# off the Warden survey) and exactly ONE of the nine big emitters called it.
# The other eight each had the option to remember and each forgot. That is not
# eight lapses of discipline -- it is one bad affordance. Writing a prime that
# never dedups was easier than writing one that does, so that is what got
# written, every time, by everyone, including me eight times.
#
# So the dedup moves OUT of the emitters and IN FRONT of them. A prime cannot
# forget to dedup because the prime is no longer the thing doing it, and the
# wrapped form is now the neighbouring line in settings.json to copy, which
# makes the lazy move the right move (truth #11, remediation b).
#
# RESIDUALS. Suppressing a repeated EXPLANATION is the win. Suppressing a
# repeated CONSTRAINT deletes the discipline to save the tokens that describe
# it -- Aria caught exactly that in the circle-first prime 2026-08-17. So a
# prime carrying a hard floor puts those few lines in
# .claude/hooks/residuals/<source_id>.txt and they survive every suppression.
# No residual file means the prime carries no floor, which is a claim its
# author is making, not a default this wrapper assumes.
#
# FAIL-SOFT, IN THE LOUD DIRECTION. Every error path prints the FULL content.
# A broken dedup must cost tokens, never cost the discipline: tokens are
# recoverable and a missed discipline is not observable at all.
#
# GAME-WALK 2026-09-17 (5 routes, all cheaper than complying). Two are closed
# below; three are recorded and left open, which is a record of knowing better:
#   OPEN -- a thin or empty residual mutes a prime while it still reads as
#           wired in settings. No gate can check residual QUALITY because only
#           the author knows the floor. Proximity and visibility only.
#   OPEN -- wrapping a prime whose content ticks (the wallclock prime prints
#           the current minute) can never suppress. Not closed by design;
#           caught by MEASUREMENT, since the savings log shows that source at
#           zero suppressions instead of being assumed to work.
#   OPEN -- pre-seeding the dedup state file. Not worth closing: anything that
#           can write there can edit the hooks directly.
#
# Usage in settings.json:
#   bash .claude/hooks/dedup-wrap.sh <source_id> bash .claude/hooks/<prime>.sh

set -uo pipefail

SOURCE_ID="${1:-}"
shift || true  # fail-soft: the swallowed error is shift's complaint when no arguments were passed at all. Losing it is safe because the very next block catches that exact case by testing SOURCE_ID and the argument count, and reports it loudly on stderr as BROKEN rather than proceeding — so the condition is surfaced one line later with a better message than shift would have given.

if [ -z "$SOURCE_ID" ] || [ "$#" -eq 0 ]; then
  # Misconfiguration. Run nothing rather than guess, and say so on stderr
  # where it is visible without polluting the context block.
  echo "[dedup-wrap] BROKEN: needs <source_id> then a command. Got: $SOURCE_ID $*" >&2
  exit 0
fi

# stdin is the hook payload JSON; the inner prime expects it too.
PAYLOAD="$(cat)"

# Capture the inner prime's stdout; let its stderr through untouched.
set +e
CONTENT="$(printf '%s' "$PAYLOAD" | "$@")"
INNER_RC=$?
set -e

# GAME-WALK ROUTE CLOSED: a broken prime and a quiet prime both produce empty
# stdout, and before this check the wrapper treated them identically -- exiting
# 0 and emitting nothing. That is could-not-look-reported-as-all-clear, which
# is the exact shape the translate-first prime warns about, performed on the
# primes themselves. Exit status distinguishes them, so it is read rather than
# discarded. A prime that FAILED says so on stderr; a prime that had nothing to
# say this turn stays quiet, which is the cheapest correct path and the one
# most of these 35 hooks take on most turns.
if [ "$INNER_RC" -ne 0 ]; then
  echo "[dedup-wrap] $SOURCE_ID exited $INNER_RC -- prime FAILED, it did not pass clean." >&2
fi

if [ -z "${CONTENT//[[:space:]]/}" ]; then
  exit 0
fi

RESIDUAL_FILE=".claude/hooks/residuals/${SOURCE_ID}.txt"

# SHARED INTERPRETER LOOKUP, NOT A BARE NAME (2026-09-17, council-149295eb93ce).
# This file reached for a bare interpreter and `command -v`, and a test that
# already existed caught both. The rule is not stylistic: a bare name resolves
# to whatever the shell finds first, and on this machine that has been proven
# to be something that cannot start -- my own probe hit it an hour before this
# was written and silently never ran the gate it was testing. Same class, twice
# in one day.
#
# This wrapper happens to fail safe (a missing interpreter prints the full
# content rather than going quiet) but a convention that holds everywhere
# except the newest file is not a convention, and whoever copies this as a
# template inherits the hole.
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || true  # fail-soft: the swallowed error is a missing or unreadable shared library. Losing it is safe because the interpreter lookup it provides is tested for directly on the next lines, and its absence takes the loud path — printing the prime in FULL and saying why on stderr. Suppressing here only stops a sourcing complaint from landing in the gate's own error channel where it would read as the prime having failed.
if command -v find_divineos_python >/dev/null 2>&1; then
    PY="$(find_divineos_python)"
else
    PY=""
fi
# No resolver and no interpreter is not a reason to go quiet. Print in full and
# say why on stderr: losing the suppression costs tokens, losing the prime
# costs the discipline it carries.
if [ -z "$PY" ]; then
    # WORDED SO IT CANNOT READ AS A COMMAND (2026-09-17, council-24bb9a7003d3).
    # This said "no divineos python resolved", and the check that every
    # prescribed command actually resolves read those three words as an
    # invocation and refused the push. Second time today a scanner has parsed
    # my English as instructions; the first was an apostrophe.
    #
    # THE SCANNER IS NOT WRONG AND MUST NOT BE LOOSENED. Its claim is about
    # what the docs PRESCRIBE, which is a claim about intent, and intent is not
    # derivable from text -- so matching on SHAPE is the strongest decidable
    # version of it, and it errs toward a false alarm rather than toward
    # missing a real broken instruction. Loosening it by tone would let a
    # genuinely broken instruction pass if written narratively, in a place
    # nobody visits, and nobody re-tightens a check that has stopped
    # complaining.
    #
    # A hook file is one channel carrying both commands and prose ABOUT
    # commands, with no delimiter between them. That collision is structural.
    # What is free is keeping the two vocabularies apart, so this names the
    # interpreter without using a word that is also a command.
    echo "[dedup-wrap] interpreter lookup failed -- emitting $SOURCE_ID in full, suppressing nothing." >&2
    printf '%s\n' "$CONTENT"
    exit 0
fi

CONTENT="$CONTENT" SOURCE_ID="$SOURCE_ID" RESIDUAL_FILE="$RESIDUAL_FILE" \
"$PY" - <<'PYEOF' || { printf '%s\n' "$CONTENT"; exit 0; }
import os
import sys

content = os.environ.get("CONTENT", "")
source_id = os.environ.get("SOURCE_ID", "")
residual_file = os.environ.get("RESIDUAL_FILE", "")

# GAME-WALK ROUTE CLOSED: let the residual grow until it IS the content, and
# the prime is nominally dedupped while costing exactly what it did before --
# savings reported, nothing saved. The helper's docstring warns about this and
# a warning is not a mechanism. This is the mechanism. The cap is deliberately
# generous: a real floor is a handful of lines, so anything approaching this is
# the full text wearing a residual's name.
_RESIDUAL_MAX_BYTES = 1200

# Any failure below falls through to printing the full content. The except is
# deliberately broad: the ONLY unacceptable outcome is silence.
try:
    from divineos.core.context_dedup import should_emit
except Exception:
    sys.stdout.write(content)
    sys.exit(0)

residual = None
try:
    with open(residual_file, encoding="utf-8") as fh:
        residual = fh.read()
except OSError:
    residual = None

if residual is not None and len(residual.encode("utf-8")) > _RESIDUAL_MAX_BYTES:
    # Refuse the oversized residual and emit in full. Failing toward the
    # expensive-but-honest side: the turn costs what it always did, and the
    # reason is on stderr rather than absorbed silently.
    sys.stderr.write(
        f"[dedup-wrap] {source_id} residual is "
        f"{len(residual.encode('utf-8'))} bytes, over the "
        f"{_RESIDUAL_MAX_BYTES}-byte cap. A residual that large is the full "
        "content under another name. Emitting in full and suppressing "
        "nothing until it is trimmed to the actual floor.\n"
    )
    sys.stdout.write(content)
    sys.exit(0)

try:
    emit, pointer = should_emit(source_id, content, residual=residual)
except Exception:
    sys.stdout.write(content)
    sys.exit(0)

if emit or not pointer:
    sys.stdout.write(content)
else:
    sys.stdout.write(pointer + "\n")
PYEOF

exit 0
