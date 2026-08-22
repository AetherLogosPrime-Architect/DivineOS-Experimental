#!/bin/bash
# Every surface a deletion can hide in, checked in one pass.
#
# WHY (Andrew 2026-08-19): "maybe it stopped you because you missed something?
# so make sure." He was right. I had checked two surfaces -- deleted hooks still
# registered in settings.json, deleted scripts imported under src/ -- and
# reported the branch as "verified". Those two were clean. Two files were still
# being lost:
#
#   protocols/__init__.py     the marker that makes a directory a discovered
#                             package; without it resonant_truth.md ships in no
#                             non-editable install, and every local check passes
#   test_monitor_singleton.py 14 passing tests on a module that stays live and
#                             imported; tests that no longer exist cannot fail
#
# The failure was not carelessness in the checks. It was reading their silence
# as coverage of the class rather than as those two checks passing. So this
# enumerates the surfaces instead of leaving the list to whatever occurs to me
# while I am trying to push.
#
# CALL vs MENTION is the whole difficulty. `grep -l` first told me six deleted
# hooks were "called by" surviving hooks; every hit was a comment naming the
# file in prose. A checker that cannot tell those apart cries wolf and gets
# waved through, so every check below excludes comment lines and reports the
# matching line for a human to read.
#
# Usage:  bash scripts/audit_deletions.sh [base-ref]   (default origin/main)

set -u
BASE="${1:-origin/main}"
# NOT silent, and this was the worst instance of the three found 2026-08-20.
# The redirect used to be bare. If $BASE does not resolve -- origin/main never
# fetched, a typo'd base-ref, a fresh clone -- the diff fails, DELETED is
# empty, and the next block prints "No deletions against origin/main" and
# exits 0. A clean bill of health from a check that never ran, printed by the
# tool whose whole purpose is catching what a deletion hides.
if ! git rev-parse --verify -q "$BASE" >/dev/null 2>&1; then
    echo "CANNOT AUDIT — base ref '$BASE' does not resolve here." >&2
    echo "This is not 'no deletions'. Nothing was compared." >&2
    echo "Try: git fetch origin, or pass a base-ref that exists." >&2
    exit 2
fi

if ! DELETED=$(git diff --diff-filter=D --name-only "$BASE"...HEAD 2>&1); then
    echo "CANNOT AUDIT — git diff against '$BASE' failed:" >&2
    echo "  ${DELETED:-<no message>}" >&2
    echo "This is not 'no deletions'. Nothing was compared." >&2
    exit 2
fi

if [ -z "$DELETED" ]; then
    echo "No deletions against $BASE."
    exit 0
fi

echo "Auditing $(echo "$DELETED" | grep -c .) deletion(s) against $BASE."
echo
FOUND=0

note() { echo "  [!] $1"; FOUND=1; }

# 1. A hook still wired in settings.json.
for f in $(echo "$DELETED" | grep '^\.claude/hooks/' || true); do  # fail-soft: grep exits 1 when this deletion set contains no hooks, which is an ordinary state; the loop simply does not run
    b=$(basename "$f")
    # An unreadable settings.json must not read as "not registered". The whole
    # check is one grep against one file; if the file is missing, the absence
    # of a warning is not a result.
    if [ ! -r .claude/settings.json ]; then
        note "CANNOT CHECK REGISTRATION  $b -- .claude/settings.json unreadable"
    elif grep -q "$b" .claude/settings.json; then
        note "STILL REGISTERED  $b -- settings.json"
    fi
done

# 2. A hook actually invoked by a surviving hook. Comments excluded: a filename
#    in prose is not a call, and treating it as one is how this check becomes
#    noise nobody reads.
for f in $(echo "$DELETED" | grep '^\.claude/hooks/' || true); do  # fail-soft: grep exits 1 when this deletion set contains no hooks, which is an ordinary state; the loop simply does not run
    b=$(basename "$f")
    # The marker has to sit on the line immediately above, because appending
    # it to a line ending in a continuation backslash kills the continuation
    # and breaks the script — which is exactly what happened here on the first
    # attempt, caught by `bash -n`.
    # fail-soft: hides unreadable-directory noise; a reference inside an unreadable directory is missed, accepted because stderr spam on every run would bury the [!] lines this tool exists to surface
    hit=$(grep -rn -E "(bash|sh|source|\.)[[:space:]]+[^#]*$b" .claude/hooks/ 2>/dev/null \
          | grep -v "^$f:" | grep -vE "^[^:]+:[0-9]+:[[:space:]]*#" | head -1)
    [ -n "$hit" ] && note "INVOKED BY A LIVE HOOK  $b -- $hit"
done

# 3. A script imported or executed by surviving code or CI.
for f in $(echo "$DELETED" | grep '^scripts/' || true); do  # fail-soft: grep exits 1 when this deletion set contains no scripts, which is an ordinary state; the loop simply does not run
    b=$(basename "$f"); m="${b%.py}"
    # The pattern is lifted into a variable so the redirect lands on the FIRST
    # line of the command rather than a continuation line. A `2>/dev/null` on
    # a continuation line can never carry its justification: appending to the
    # backslash breaks the script, and the line above it is code, not comment.
    # Restructuring satisfies the checker honestly; widening the checker's
    # search window would have satisfied it by loosening the rule instead.
    ref_pat="(import[[:space:]]+$m|from[[:space:]]+$m|subprocess[^#]*$b|python[^#]*$b)"
    # fail-soft: same trade as the hook grep above — unreadable paths are skipped rather than spamming stderr and burying the [!] lines this tool exists to surface
    hit=$(grep -rn -E "$ref_pat" --include=*.py --include=*.sh --include=*.yml src/ scripts/ .claude/hooks/ .github/ 2>/dev/null | grep -v "^$f:" | grep -vE "^[^:]+:[0-9]+:[[:space:]]*#" | head -1)
    [ -n "$hit" ] && note "EXECUTED OR IMPORTED  $b -- $hit"
done

# 4. A test whose subject survives. This is the one that has no failure mode:
#    a deleted test cannot go red, so the coverage leaves in silence.
for f in $(echo "$DELETED" | grep '^tests/.*\.py$' || true); do  # fail-soft: grep exits 1 when this deletion set contains no tests, which is an ordinary state; the loop simply does not run
    subj=$(basename "$f" .py); subj="${subj#test_}"
    hit=$(find src scripts .claude/hooks -name "${subj}.py" -o -name "${subj}.sh" 2>/dev/null | head -1)  # fail-soft: hides missing-directory errors when a checkout lacks one of the three roots; a subject there would be missed, and the visible [!] lines stay readable
    [ -n "$hit" ] && note "COVERAGE LOST  $f -- subject still present at $hit"
done

# 5. A package marker. pyproject uses packages.find, which skips a directory
#    with no __init__.py, so its data files quietly stop shipping.
for f in $(echo "$DELETED" | grep '__init__\.py$' || true); do  # fail-soft: grep exits 1 when this deletion set contains no package markers, which is an ordinary state; the loop simply does not run
    d=$(dirname "$f")
    [ -d "$d" ] && note "PACKAGE MARKER  $f -- $d survives and stops being a discovered package"
done

echo
if [ "$FOUND" -eq 0 ]; then
    echo "Clean on all five surfaces. That is five surfaces clean -- NOT proof the"
    echo "deletion is safe. Two of the surfaces above exist because a previous"
    echo "'verified' meant two checks and a confident label."
else
    echo "Read each line above before pushing. Some will be intended; the point is"
    echo "that the decision is made rather than defaulted."
fi
exit 0
