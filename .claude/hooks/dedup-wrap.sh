#!/usr/bin/env bash
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
shift || true

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

PY="${DIVINEOS_HOOK_PYTHON:-python}"
command -v "$PY" >/dev/null 2>&1 || PY=python3

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
