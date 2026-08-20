#!/bin/bash
# PostToolUse — flags a verification command whose OUTPUT cannot distinguish
# "all clear" from "did not measure what you think".
#
# Andrew 2026-08-20: "go over all of your failures you ran into tonight and if
# they werent already fixed think of solutions of how they can be."
#
# ## The class, with the four instances that produced it
#
# Each of these ran green, or ran silent, and I read the result as evidence.
# None measured what I believed it measured.
#
#   1. `printf '%s' "$board" | python - "$arg" <<'PYEOF'`
#      A heredoc already occupies python's stdin, so the pipe delivers 0
#      bytes. The isolated test passed because it fed input by REDIRECT,
#      which is not how the caller invokes it. Green, and meaningless.
#
#   2. `python scripts/push_queued.py "$branch" 2>&1 | tail -30`
#      A pipeline's exit status is the LAST stage's. The push was BLOCKED by
#      a failing test, `tail` exited 0, and the harness reported exit 0.
#
#   3. `pytest tests/test_event_verifier.py tests/`
#      Collection collapsed to the first path: 112 tests, not 11,200. Four
#      runs of "no reproduction" proved nothing about the full suite, and
#      `112 passed` was printed in front of me every time.
#
#   4. `pytest tests/ ... | grep -A40 "fuzz hash verify failed"`
#      grep emits nothing when the test PASSES, so the empty capture was
#      ambiguous between "passed" and "never ran".
#
# ## Why a detector and not a discipline
#
# I knew all four rules already. Knowing them did not fire at the moment the
# output arrived, because the output looked like the answer I wanted. Aria's
# measurement of this substrate's primes is the governing evidence: the only
# remedy shape that moved a number was read-the-source-at-the-moment-of-use;
# remind-me-to-check did not move one. So this fires ON the tool result, next
# to the output about to be misread, and names the specific ambiguity.
#
# ## Why PostToolUse
#
# PreToolUse would warn before the output exists — one beat too early to be
# read against the thing it concerns. PreToolUse also already carries 26
# hooks against a p90 hook duration of 4.2s (measured this session), so
# adding there worsens the freeze class this session opened with.
#
# Advisory only. It never blocks: a wrong warning should cost a glance, not
# a turn.

set -uo pipefail

INPUT="$(cat 2>/dev/null || true)"
[ -z "$INPUT" ] && exit 0

CMD="$(printf '%s' "$INPUT" | python -c "
import json,sys
try: d=json.load(sys.stdin)
except Exception: print(''); raise SystemExit
print(((d.get('tool_input') or {}).get('command') or ''))
" 2>/dev/null || echo "")"  # fail-soft: unparseable hook stdin means there is no command to inspect, and an advisory hook must never block on its own input
[ -z "$CMD" ] && exit 0

WARNINGS=""
add() { WARNINGS="${WARNINGS}
  - $1"; }

# --- 1. pipeline masking a verification command's exit status ---------------
# pipefail is not in effect for ad-hoc commands, so the status observed is the
# last stage's. Only flag when the FIRST stage is a command whose exit status
# IS the result being sought.
FIRST_STAGE="${CMD%%|*}"
if [ "$FIRST_STAGE" != "$CMD" ]; then
    case "$FIRST_STAGE" in
        *pytest*|*push_queued*|*"git push"*|*shellcheck*|*mypy*|*ruff*|*"bash -n"*|*precommit*)
            case "$CMD" in
                *pipefail*) ;;   # deliberately handled
                *) add "EXIT STATUS IS THE PIPE'S, NOT THE COMMAND'S. The first stage is a check whose status is the answer, but \$? will belong to the last stage. 2026-08-20: a BLOCKED push read as exit 0 through \`| tail\`. Verify the EFFECT (did the ref move, did the file change), not the status." ;;
            esac ;;
    esac
fi

# --- 2. pytest handed a path nested inside another path --------------------
# Collection collapses and the reported count silently covers less than
# intended. The count is printed; hundreds-vs-thousands is exactly the
# difference that reads past.
case "$CMD" in
    *pytest*)
        PATHS="$(printf '%s' "$CMD" | tr ' ' '\n' | grep -E '^tests(/|$)' || true)"  # fail-soft: no test paths on the line is the ordinary case and means there is nothing to check
        if [ "$(printf '%s' "$PATHS" | grep -c . || true)" -gt 1 ]; then  # fail-soft: an empty path list counts as 0 and skips the check, which is the quiet-correct direction
            if printf '%s' "$PATHS" | grep -qE '^tests/?$'; then
                add "PYTEST COLLECTION MAY COLLAPSE. A directory and a path inside it were both passed; pytest can collect only one. 2026-08-20: \`pytest tests/test_event_verifier.py tests/\` collected 112, not 11,200, and four 'no reproduction' runs proved nothing. READ THE COLLECTED COUNT before trusting the verdict."
            fi
        fi ;;
esac

# --- 3. a test run filtered through grep, where silence is ambiguous -------
case "$CMD" in
    *pytest*"|"*grep*)
        case "$CMD" in
            *" -c "*|*--count*) ;;   # counting resolves the ambiguity
            *) add "GREP IS SILENT ON PASS. Filtering a test run through grep makes empty output ambiguous between 'passed' and 'never ran'. 2026-08-20: an empty capture file was read as 'no information' when the suite had passed. Capture full output to a file, grep the FILE, and read the summary line." ;;
        esac ;;
esac

[ -z "$WARNINGS" ] && exit 0

{
    echo "[ambiguous-verification] this command's output cannot separate 'clear' from 'did not measure':"
    printf '%s\n' "$WARNINGS"
    echo "  (advisory, nothing blocked. The rule: no verdict without its denominator.)"
} >&2

exit 0
