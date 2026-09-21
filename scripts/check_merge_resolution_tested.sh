#!/bin/bash
# A merge presents ONE comparison and it is not the one that matters.
#
# Resolving a conflict puts the two sides in front of me and invites me to
# decide between them. That comparison -- left against right -- is the one the
# tool offers, and it can be done thoroughly while being the wrong question.
# The comparison that decides correctness is each side against the BEHAVIOUR of
# the module it is about to live in, and nothing in a merge ever presents it.
#
# 2026-09-20: I spliced two versions of a message together having checked they
# asserted the same thing as text. My branch removes the limitation the longer
# version explains, so the spliced result would have told a reader that a real
# miss was an inapplicable question. I had compared the two sides carefully and
# neither of them to the code. An inherited test caught it; my reading did not.
#
# So this runs the tests that cover the resolved files, before the merge is
# committed. It is mechanical on purpose: the conflicted set is already known
# to the merge, so nothing depends on me remembering which files they were.
#
# WHAT IT CANNOT DO, said plainly so nobody relaxes on it: a resolved file with
# no test covering it passes here, and that is reported rather than hidden. The
# check proves that what IS covered still holds. It does not prove the
# resolution was right.
#
# REFUSES ONLY DURING A MERGE. Outside one it exits 0 in silence -- there is no
# conflicted set to reason about, and a check that fires on every commit would
# be noise rather than a guard.

set -u

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"  # fail-soft: run outside a repository there is no merge to check and nothing to refuse
if [[ -z "$REPO_ROOT" ]]; then
    exit 0
fi

if [[ ! -f "$REPO_ROOT/.git/MERGE_HEAD" ]] && [[ ! -f "$(git rev-parse --git-dir)/MERGE_HEAD" ]]; then
    exit 0
fi

# The conflicted set, from the merge itself rather than from memory. Files that
# conflicted are staged by the time a commit is attempted, so the unmerged list
# is empty here -- the record of WHICH files conflicted lives in the rerere
# index and in the merge's own output, neither of which is reliable at this
# point. So the set used is every path the merge touched, which is wider than
# the conflicted set and wrong in the safe direction.
mapfile -t CHANGED < <(git diff --name-only HEAD MERGE_HEAD 2>/dev/null)
if [[ "${#CHANGED[@]}" -eq 0 ]]; then
    echo "[merge-test] could not read the merge's changed paths -- NOT a clean pass" >&2
    exit 1
fi

# Map each changed source path to test files that name it. Lexical, and that is
# a real limit: a test exercising a module without naming it is invisible here.
# Reported in the output rather than assumed away.
declare -A TESTS=()
for path in "${CHANGED[@]}"; do
    case "$path" in
        tests/*) TESTS["$path"]=1 ; continue ;;
        *.py|*.sh) ;;
        *) continue ;;
    esac
    base="$(basename "$path")"
    base="${base%.*}"
    [[ -z "$base" ]] && continue
    while IFS= read -r hit; do
        [[ -n "$hit" ]] && TESTS["$hit"]=1
    done < <(grep -rl --include='test_*.py' -F "$base" "$REPO_ROOT/tests" 2>/dev/null)
done

if [[ "${#TESTS[@]}" -eq 0 ]]; then
    echo "[merge-test] no test names any file this merge touched." >&2
    echo "[merge-test] That is NOT a pass -- it is an absence of coverage, and the" >&2
    echo "[merge-test] resolution is unexamined by anything but the person who made it." >&2
    exit 0
fi

echo "[merge-test] running ${#TESTS[@]} test file(s) covering this merge's paths" >&2
if ! python -m pytest "${!TESTS[@]}" -q --tb=short; then
    echo "" >&2
    echo "[merge-test] REFUSED: a test covering a resolved file fails." >&2
    echo "[merge-test] Read it before touching it. The most likely reading is not" >&2
    echo "[merge-test] that the test is stale -- it is that the resolution describes" >&2
    echo "[merge-test] behaviour the merged code no longer has." >&2
    exit 1
fi

echo "[merge-test] tests covering this merge's paths pass (coverage is lexical, not proof of a correct resolution)" >&2
exit 0
