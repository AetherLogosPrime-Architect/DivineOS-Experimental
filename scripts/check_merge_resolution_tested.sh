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

# The project's own interpreter is preferred: a bare `python` can be one with
# none of the house's packages, which also fails without running anything.
PY="python"
for cand in "$REPO_ROOT/.venv/Scripts/python.exe" "$REPO_ROOT/.venv/bin/python"; do
    [[ -x "$cand" ]] && { PY="$cand"; break; }
done

# WHICH FILES THIS TESTS, and why it is no longer "every path main changed".
# 2026-10-27: the old set was every path that differs between the two tips. A
# branch that was behind main by a day put 282 files in front of it, which named
# nearly every test in the house: 13,500 tests, 28 minutes, serial, and a refusal
# whenever any unrelated test had a bad moment. Dad: "every push fails three
# times and takes 30 mins per push." The comment that stood here called the wide
# set "wrong in the safe direction", and never priced it. Priced, it is the UNSAFE
# direction: a check nobody can afford to run gets walked around.
#
# What a merge can get wrong is measured from the MERGE BASE, not from two tips:
# my side's changes, meeting main's new code. So the set is every path I changed
# since the base, and the tests that name them are run against the merged tree.
# Files only main changed are main's own run's job. The whole suite is the push's
# job, so a green here is NOT a whole-tree pass and says so below.
#
# The mapping from changed path to tests is the draft push's own selector
# (scripts/draft_test_selection.py), so the house has one idea of "which tests
# cover this" and not two that drift apart.
#
# If the base cannot be found, or the selector says the change cannot be narrowed
# (conftest or project config changed), this falls back to the OLD wide set, so a
# failure of the narrowing is wide, never narrow and never a silent pass.
declare -A TESTS=()
SCOPE=""
BASE="$(git merge-base HEAD MERGE_HEAD 2>/dev/null)"  # fail-soft: an empty base is caught by the test below and sends this to the wide fallback, which is the safe direction
TREE="$(git write-tree 2>/dev/null)"  # fail-soft: same, an empty tree id sends this to the wide fallback
# WHICH SIDE IS THE BRANCH (Aether's attack, 2026-10-27). HEAD is the branch in the flow
# the house uses, a branch folding main in. If someone merges a branch INTO main locally,
# HEAD is main and MERGE_HEAD is the branch, and measuring from HEAD would test what main
# changed and still print "this branch changed". So: if HEAD already sits on origin/main,
# the branch is MERGE_HEAD. If origin/main cannot be found nothing can be said about which
# side is which, and that goes to the wide fallback.
SIDE="HEAD"
SIDE_KNOWN=1
if ! git rev-parse --verify --quiet origin/main >/dev/null 2>&1; then  # fail-soft: a missing origin/main is the answer here, not an error: it sends this to the wide fallback
    SIDE_KNOWN=0
elif git merge-base --is-ancestor HEAD origin/main 2>/dev/null; then  # fail-soft: exit 1 means "HEAD is not on main", the ordinary case
    SIDE="MERGE_HEAD"
fi
if [[ -n "$BASE" && -n "$TREE" && "$SIDE_KNOWN" -eq 1 && -f "$REPO_ROOT/scripts/draft_test_selection.py" ]]; then
    mapfile -t MINE < <(git diff --name-only --no-renames "$BASE" "$SIDE" 2>/dev/null)  # fail-soft: an empty result is handled on the next line as not narrowable
    if [[ "${#MINE[@]}" -gt 0 ]]; then
        SELERR="$(mktemp)"
        SELECTED="$(printf '%s\n' "${MINE[@]}" | env -u GIT_DIR -u GIT_WORK_TREE -u GIT_INDEX_FILE -u GIT_COMMON_DIR \
            "$PY" "$REPO_ROOT/scripts/draft_test_selection.py" --repo "$REPO_ROOT" --ref "$TREE" 2>"$SELERR")"
        sel_rc=$?
        cat "$SELERR" >&2
        UNCOVERED="$(grep -c 'NO TEST NAMES' "$SELERR" 2>/dev/null)"  # fail-soft: grep -c exits 1 on zero matches, and zero is a real answer
        rm -f "$SELERR"
        if [[ $sel_rc -eq 0 ]]; then
            SCOPE="the ${#MINE[@]} file(s) this branch changed since the merge base"
            while IFS= read -r hit; do
                hit="${hit%$'\r'}"
                [[ -n "$hit" && -f "$REPO_ROOT/$hit" ]] && TESTS["$hit"]=1
            done <<< "$SELECTED"
        elif [[ $sel_rc -eq 2 ]]; then
            echo "[merge-test] REFUSED: the test selector could not read the repository (exit 2)." >&2
            echo "[merge-test] That is not a pass and not an empty selection. Fix it first." >&2
            exit 1
        fi
    fi
fi

if [[ -z "$SCOPE" ]]; then
    # The old wide set: every path the merge touched, from the difference of the tips.
    mapfile -t CHANGED < <(git diff --name-only HEAD MERGE_HEAD 2>/dev/null)  # fail-soft: the empty result is caught on the very next line and announced as could-not-read rather than as a clean pass, which is the whole point of this check
    if [[ "${#CHANGED[@]}" -eq 0 ]]; then
        echo "[merge-test] could not read the merge's changed paths -- NOT a clean pass" >&2
        exit 1
    fi
    SCOPE="every path the merge touched (${#CHANGED[@]}): the narrow set was unavailable"
    # Map each changed source path to test files that name it. Lexical, and that is
    # a real limit: a test exercising a module without naming it is invisible here.
    for path in "${CHANGED[@]}"; do
        case "$path" in
            tests/_archive/*) continue ;;  # retired tests; collecting them clashes with the live conftest
            tests/*.py) [[ -f "$REPO_ROOT/$path" ]] && TESTS["$path"]=1 ; continue ;;  # a moved or deleted test is not run
            tests/*) ;;  # a fixture (json, text) is not a test: the runner would fail on it, so find the tests that name it instead
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
fi

if [[ "${#TESTS[@]}" -eq 0 ]]; then
    echo "[merge-test] no test names any file this merge touched." >&2
    echo "[merge-test] That is NOT a pass -- it is an absence of coverage, and the" >&2
    echo "[merge-test] resolution is unexamined by anything but the person who made it." >&2
    exit 0
fi

echo "[merge-test] running ${#TESTS[@]} test file(s) covering $SCOPE" >&2
# 2026-10-04: the paths go through a pytest argument file. Passed as words, a
# merge touching a thousand tests exceeded the Windows command-line limit, and
# that could-not-run was reported below as "a test fails" -- the first time
# this check ever ran in Aria's house, because her installed hooks were stale.
ARGFILE="$(mktemp)"
# SORTED, because an associative array hands its keys back in hash order. In that
# order a test that reloads the ledger module (test_log_level_config) ran before
# the test that holds the old Ledger class (2026-10-27: the same test refused two
# merges in a row, though it passes alone and in the suite's own order).
printf '%s\n' "${!TESTS[@]}" | sort > "$ARGFILE"
# 2026-10-19: handed to a native Windows python as a POSIX path (/tmp/...), the
# argument file is found only while the shell happens to be converting paths. With
# MSYS_NO_PATHCONV set in the caller's environment it was not, and the run died
# with "the tests could not be run". Converted explicitly so the ambient setting
# cannot decide whether this check works.
ARGPATH="$ARGFILE"
if command -v cygpath >/dev/null 2>&1; then
    ARGPATH="$(cygpath -m "$ARGFILE")"
fi
# Serial on purpose: with xdist the workers never expand the argument file, so
# nothing is collected (pytest exit 5, seen 2026-10-04).
# Run as from a clean shell, the same scrub check_push_readiness.sh uses: this
# check runs inside `git commit`, which exports its in-progress state to every
# child. A test that makes its own worktree inherited the commit's index and
# failed with exit 128 only during a commit, never alone (2026-10-04).
env -u GIT_DIR -u GIT_WORK_TREE -u GIT_COMMON_DIR -u GIT_INDEX_FILE \
    -u GIT_OBJECT_DIRECTORY -u GIT_ALTERNATE_OBJECT_DIRECTORIES -u GIT_PREFIX \
    -u GIT_NAMESPACE -u GIT_QUARANTINE_PATH \
    "$PY" -m pytest "@$ARGPATH" -q --tb=short -p no:cacheprovider
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

echo "[merge-test] tests covering $SCOPE pass (coverage is lexical, not proof of a correct resolution)" >&2
if [[ "${UNCOVERED:-0}" -gt 0 ]]; then
    echo "[merge-test] But ${UNCOVERED} of those file(s) had NO test naming them (listed above): nothing was verified for those." >&2
fi
echo "[merge-test] This is NOT a whole-tree pass: the whole suite is the push's job." >&2
exit 0
