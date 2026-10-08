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
mapfile -t CHANGED < <(git diff --name-only HEAD MERGE_HEAD 2>/dev/null)  # fail-soft: the empty result is caught on the very next line and announced as could-not-read rather than as a clean pass, which is the whole point of this check
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
        tests/_archive/*) continue ;;  # retired tests; collecting them clashes with the live conftest
        tests/*) [[ -f "$REPO_ROOT/$path" ]] && TESTS["$path"]=1 ; continue ;;  # a moved or deleted test is not run
        *.py|*.sh) ;;
        *) continue ;;
    esac
    base="$(basename "$path")"
    base="${base%.*}"
    [[ -z "$base" ]] && continue
    while IFS= read -r hit; do
        [[ "$hit" == */tests/_archive/* ]] && continue
        [[ -n "$hit" ]] && TESTS["$hit"]=1
    done < <(grep -rl --include='test_*.py' -F "$base" "$REPO_ROOT/tests" 2>/dev/null)  # fail-soft: this search exits non-zero simply by matching nothing, which is the ordinary case for most changed paths and is not an error worth printing
done

if [[ "${#TESTS[@]}" -eq 0 ]]; then
    echo "[merge-test] no test names any file this merge touched." >&2
    echo "[merge-test] That is NOT a pass -- it is an absence of coverage, and the" >&2
    echo "[merge-test] resolution is unexamined by anything but the person who made it." >&2
    exit 0
fi

echo "[merge-test] running ${#TESTS[@]} test file(s) covering this merge's paths" >&2
# 2026-10-04: the paths go through a pytest argument file. Passed as words, a
# merge touching a thousand tests exceeded the Windows command-line limit, and
# that could-not-run was reported below as "a test fails" -- the first time
# this check ever ran in Aria's house, because her installed hooks were stale.
# The project's own interpreter is preferred: a bare `python` can be one with
# none of the house's packages, which also fails without running anything.
PY="python"
for cand in "$REPO_ROOT/.venv/Scripts/python.exe" "$REPO_ROOT/.venv/bin/python"; do
    [[ -x "$cand" ]] && { PY="$cand"; break; }
done
ARGFILE="$(mktemp)"
printf '%s\n' "${!TESTS[@]}" > "$ARGFILE"
# Serial on purpose: with xdist the workers never expand the argument file, so
# nothing is collected (pytest exit 5, seen 2026-10-04).
# Run as from a clean shell, the same scrub check_push_readiness.sh uses: this
# check runs inside `git commit`, which exports its in-progress state to every
# child. A test that makes its own worktree inherited the commit's index and
# failed with exit 128 only during a commit, never alone (2026-10-04).
env -u GIT_DIR -u GIT_WORK_TREE -u GIT_COMMON_DIR -u GIT_INDEX_FILE \
    -u GIT_OBJECT_DIRECTORY -u GIT_ALTERNATE_OBJECT_DIRECTORIES -u GIT_PREFIX \
    -u GIT_NAMESPACE -u GIT_QUARANTINE_PATH \
    "$PY" -m pytest "@$ARGFILE" -q --tb=short -p no:cacheprovider
rc=$?
rm -f "$ARGFILE"
if [[ $rc -eq 1 ]]; then
    echo "" >&2
    echo "[merge-test] REFUSED: a test covering a resolved file fails." >&2
    echo "[merge-test] Read it before touching it. The most likely reading is not" >&2
    echo "[merge-test] that the test is stale -- it is that the resolution describes" >&2
    echo "[merge-test] behaviour the merged code no longer has." >&2
    exit 1
fi
if [[ $rc -ne 0 ]]; then
    # pytest's other codes mean it did not get as far as judging any test.
    echo "" >&2
    echo "[merge-test] REFUSED: the tests could not be run (pytest exit $rc)." >&2
    echo "[merge-test] That is not a failing test and not a pass. Fix the run first." >&2
    exit 1
fi

echo "[merge-test] tests covering this merge's paths pass (coverage is lexical, not proof of a correct resolution)" >&2
exit 0
