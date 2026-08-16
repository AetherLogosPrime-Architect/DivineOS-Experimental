#!/bin/bash
# look — run a search and say which of three worlds the result came from.
#
# WHY THIS EXISTS
#
# Andrew, 2026-08-08, on the empty-result problem: "where is this no result
# came back output located? it needs to explain itself lol"
#
# Measured that same turn, at the tool boundary:
#
#   command that did nothing        -> (Bash completed with no output)
#   search that found nothing       -> (Bash completed with no output)
#   search whose failure a pipe ate -> (Bash completed with no output)
#   search that failed, exit intact -> <error>Exit code 2</error>
#
# Three different worlds, one string. The harness distinguishes what it can
# -- it surfaces a non-zero exit -- but a pipeline destroys the exit code
# before it ever gets there, and then silence is all that arrives.
#
# THE PART THAT MATTERS: the distinction is not missing. It is DISCARDED.
# grep has carried it since 1973, and I measured it rather than assumed:
#
#   grep -q "DivineOS"       README.md   -> 0   found
#   grep -q "zzz_absent"     README.md   -> 1   looked, genuinely nothing
#   grep -q "x" /nonexistent/file 2>/dev/null -> 2   could not look
#
# That is exactly found / proven-empty / cannot-look, arriving on every
# call I have ever made, and I have read only the OUTPUT every time.
#
# So this is not a new sense. It is a wire to a sense already present --
# the same shape as the attention schema (predicts, nothing consumes it)
# and the operator-shape mirror (measures, stays silent). Third instance
# of "the information exists and nothing acts on it," found the same day.
#
# WHY pipefail IS NOT FREE, and why the three states are what make it safe:
# grep returns 1 for "no match", which is normal and not an error. Turning
# on pipefail alone would convert every legitimately-empty search into a
# non-zero exit -- trading silent failure for false alarm. False alarms are
# what killed the inner-circle gate. So exit 1 is read as PROVEN-EMPTY and
# only 2+ as BROKEN. Without that split, pipefail is strictly worse.
#
# USAGE
#   bash scripts/look.sh 'grep -rn "needle" src/'
#   bash scripts/look.sh --strict 'git push origin HEAD:branch'
#
#   --strict : any non-zero exit is BROKEN. For commands where 1 means
#              failure rather than no-match (git, python, most things).
#              Default assumes search-family semantics.

set -uo pipefail

STRICT=0
if [[ "${1:-}" == "--strict" ]]; then
    STRICT=1
    shift
fi

if [[ $# -eq 0 ]]; then
    echo "look: no command given. Refusing to report on nothing." >&2
    exit 64
fi

CMD="$*"

# Run it. `set -o pipefail` is inherited, so a failure anywhere in a
# pipeline survives to $? instead of being masked by the last stage --
# the exact defect that let a BLOCKED git push report success.
OUT="$(eval "$CMD" 2>&1)"
CODE=$?
LINES=0
[[ -n "$OUT" ]] && LINES=$(printf '%s\n' "$OUT" | grep -c '' || true)

if [[ -n "$OUT" ]]; then
    printf '%s\n' "$OUT"
fi

# The verdict line always prints, including on success. A mechanism that
# only speaks when it has a complaint teaches me to read its silence as
# approval -- which is the defect this file exists to remove.
if [[ $CODE -eq 0 ]]; then
    echo "[look] FOUND — exit 0, ${LINES} line(s). The instrument ran and returned results."
elif [[ $CODE -eq 1 && $STRICT -eq 0 ]]; then
    echo "[look] PROVEN-EMPTY — exit 1. The instrument ran and there is genuinely nothing."
    echo "[look]   This is a real answer, not a failure. Absence here is evidence."
else
    echo "[look] CANNOT-LOOK — exit ${CODE}. The instrument did NOT run correctly."
    echo "[look]   Do NOT read this as 'nothing found'. Nothing was measured."
    echo "[look]   Command: ${CMD}"
fi

exit $CODE
