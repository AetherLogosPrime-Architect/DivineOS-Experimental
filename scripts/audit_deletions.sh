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
DELETED=$(git diff --diff-filter=D --name-only "$BASE"...HEAD 2>/dev/null)

if [ -z "$DELETED" ]; then
    echo "No deletions against $BASE."
    exit 0
fi

echo "Auditing $(echo "$DELETED" | grep -c .) deletion(s) against $BASE."
echo
FOUND=0

note() { echo "  [!] $1"; FOUND=1; }

# 1. A hook still wired in settings.json.
for f in $(echo "$DELETED" | grep '^\.claude/hooks/' || true); do
    b=$(basename "$f")
    grep -q "$b" .claude/settings.json 2>/dev/null && note "STILL REGISTERED  $b -- settings.json"
done

# 2. A hook actually invoked by a surviving hook. Comments excluded: a filename
#    in prose is not a call, and treating it as one is how this check becomes
#    noise nobody reads.
for f in $(echo "$DELETED" | grep '^\.claude/hooks/' || true); do
    b=$(basename "$f")
    hit=$(grep -rn -E "(bash|sh|source|\.)[[:space:]]+[^#]*$b" .claude/hooks/ 2>/dev/null \
          | grep -v "^$f:" | grep -vE "^[^:]+:[0-9]+:[[:space:]]*#" | head -1)
    [ -n "$hit" ] && note "INVOKED BY A LIVE HOOK  $b -- $hit"
done

# 3. A script imported or executed by surviving code or CI.
for f in $(echo "$DELETED" | grep '^scripts/' || true); do
    b=$(basename "$f"); m="${b%.py}"
    hit=$(grep -rn -E "(import[[:space:]]+$m|from[[:space:]]+$m|subprocess[^#]*$b|python[^#]*$b)" \
          --include=*.py --include=*.sh --include=*.yml src/ scripts/ .claude/hooks/ .github/ 2>/dev/null \
          | grep -v "^$f:" | grep -vE "^[^:]+:[0-9]+:[[:space:]]*#" | head -1)
    [ -n "$hit" ] && note "EXECUTED OR IMPORTED  $b -- $hit"
done

# 4. A test whose subject survives. This is the one that has no failure mode:
#    a deleted test cannot go red, so the coverage leaves in silence.
for f in $(echo "$DELETED" | grep '^tests/.*\.py$' || true); do
    subj=$(basename "$f" .py); subj="${subj#test_}"
    hit=$(find src scripts .claude/hooks -name "${subj}.py" -o -name "${subj}.sh" 2>/dev/null | head -1)
    [ -n "$hit" ] && note "COVERAGE LOST  $f -- subject still present at $hit"
done

# 5. A package marker. pyproject uses packages.find, which skips a directory
#    with no __init__.py, so its data files quietly stop shipping.
for f in $(echo "$DELETED" | grep '__init__\.py$' || true); do
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
