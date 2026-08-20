#!/bin/bash
# Print the identifiers this session has actually used, so the inner circle can
# be checked against real tokens instead of against a description of a category.
#
# WHY. The circle-first template has said "name things by description, not by
# identifier" since 2026-08-14. I broke it that same day, in the turn that wrote
# the rule, and again on 2026-08-19. A rule read at every compose for five days
# did not stop the reach.
#
# Aria measured why, at the artifact layer: 18,968 prime fires across the
# substrate, 0 outcome records. Of the primes she could evaluate, only the ones
# that PRINT THE THING moved the number -- the wallclock prime prints the time
# rather than asking me to remember to check it, and it was one of two that
# cleared her noise band. Read-the-source-at-the-moment-of-use works;
# remind-me-to-check does not.
#
# DELIBERATELY NOT WIRED TO ANY HOOK. Two earlier attempts put this logic
# straight into circle-first-compose-prime.sh, which fires on every
# UserPromptSubmit. The first grepped an 18MB transcript unbounded and hung past
# 600 seconds; the second broke the quoting and left a live prompt-path hook
# carrying a syntax error. Aria measured 16 of 24 prompt hooks being killed at a
# five-second deadline in the freeze that locked Andrew's window -- I was one
# commit from adding the seventeenth while investigating that exact defect.
#
# So it lives here, standalone, where it can be slow or wrong without costing a
# turn. Wiring is a separate decision that should follow a measurement, not
# precede one.
#
# Usage:  bash scripts/session_identifiers.sh [transcript-path]

set -u

TRANSCRIPT="${1:-${CLAUDE_TRANSCRIPT_PATH:-}}"

if [ -z "$TRANSCRIPT" ] || [ ! -f "$TRANSCRIPT" ]; then
    echo "no transcript to read (pass a path, or set CLAUDE_TRANSCRIPT_PATH)" >&2
    exit 0
fi

# Bounded on purpose. The tail covers many turns of identifiers; the whole file
# is what hung. The timeout is the belt to that suspenders.
# The grep's exit status is captured separately, because a timeout and a
# genuine no-match both produce empty output. Found 2026-08-20: the old code
# printed "no identifiers found in the last 200KB" for both, so a bounded
# check that ran out of time reported a clean read of the transcript.
RAW=$(tail -c 200000 "$TRANSCRIPT" 2>/dev/null)  # fail-soft: the file's existence and readability are already checked above, so a failure here leaves RAW empty and the no-identifiers branch reports honestly
MATCHES=$(printf '%s' "$RAW" | timeout 3 grep -oE '#[0-9]{3,4}|prereg-[0-9a-f]{6,}|round-[0-9a-f]{6,}|[0-9a-f]{8,40}')
GREP_RC=$?
if [ "$GREP_RC" -eq 124 ]; then
    echo "identifier scan TIMED OUT after 3s — this is not 'none found'." >&2
    echo "The transcript tail was too slow to scan; nothing was read." >&2
    exit 0
fi

IDS=$(printf '%s' "$MATCHES" | sort | uniq -c | sort -rn | head -10 | awk '{print $2}')

if [ -z "$IDS" ]; then
    echo "no identifiers found in the last 200KB."
    exit 0
fi

echo "DO NOT PUT THESE IN THE CIRCLE - they are from this session:"
echo
while IFS= read -r _id; do printf '  %s\n' "$_id"; done <<< "$IDS"
echo
echo "Each has a plain name: the job I put up for her, the branch, the checker."
echo "If a circle sentence needs one of these strings to make sense, that"
echo "sentence belongs in the work block."
