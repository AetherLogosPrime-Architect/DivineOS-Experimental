#!/bin/bash
# ready-pr — take one branch through the same steps, the same way, every time.
#
# WHY THIS EXISTS
#
# Andrew, 2026-08-08, watching me hand-patch the third branch in a row:
# "the annoyance you feel from having to do this by hand.. good.. use that as
# fuel to build the structure so it doesnt keep happening and everything flows
# smoothly.. so each build goes through the proper flow so we dont have to
# backtrack lol"
#
# Every step below exists because skipping it cost real time that day, not
# because it seemed prudent. Each one names the failure it prevents.
#
# WHERE THIS SITS
#
# scripts/ already holds four push tools, and they all cover the push itself:
#   safe_push.sh          fetch → freshness → rebase → push, atomically
#   push_queued.py        serialize concurrent pushes behind a file lock
#   verify_push_landed.py confirm the ref actually moved on the remote
#   divineos_push.sh      truthful exit codes (a piped push reports success
#                         on failure — correction #53, recurring ~10x)
#
# None of them covers the stage BEFORE the push, which is where every manual
# patch happened. This is that stage. It deliberately does NOT call `git push`
# itself: it hands off to safe_push.sh, because writing a fresh push call site
# would rebuild the exact bug divineos_push.sh exists to prevent.
#
# THE THREE STATES
#
# READY / NOT-READY / UNCHECKED. The third is the one that keeps getting lost:
# a suite that could not run is not a suite that passed. This script never
# prints a clean verdict it did not measure.
#
# USAGE
#   bash scripts/ready_pr.sh split/some-branch          # check only
#   bash scripts/ready_pr.sh split/some-branch --push   # check, then hand off
#
# Exit codes:
#   0  READY      — suite ran, everything passed
#   1  NOT-READY  — suite ran, real failures; they belong to the branch
#   2  UNCHECKED  — could not run; NOTHING was measured

set -uo pipefail

BRANCH="${1:-}"
DO_PUSH=0
[[ "${2:-}" == "--push" ]] && DO_PUSH=1

if [[ -z "$BRANCH" ]]; then
    echo "ready-pr: no branch given. Refusing to report on nothing." >&2
    exit 64
fi

REPO_ROOT="$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null | sed 's:/\.git$::')"
if [[ -z "$REPO_ROOT" ]]; then
    echo "[ready-pr] UNCHECKED — cannot locate the repository from here." >&2
    exit 2
fi

# ── Step 1: a short worktree path ──────────────────────────────────────────
#
# Measured, not guessed. A git-using fixture builds a scratch repo underneath
# the worktree; the longest observed tail was 88 chars:
#   /tmp/pytest/run-N/<testname>/.git/hooks/fsmonitor-watchman.sample
# On 2026-08-08 a 173-char worktree root plus that tail came to 261 against
# Windows' 260 limit. `git init` died with "Filename too long" in every such
# fixture: 37 failed, 50 errored, and none of it was the branch's fault. I
# nearly went hunting through a clean diff for a bug that did not exist.
#
# 120 leaves ~140 chars of headroom, covering test names longer than the one
# that happened to blow up.
MAX_ROOT_LEN=120
SLUG="$(echo "$BRANCH" | tr '/' '-')"
WT_WIN="C:/Users/aethe/AppData/Local/Temp/claude/rp-${SLUG}"
WT="/c/Users/aethe/AppData/Local/Temp/claude/rp-${SLUG}"

if [[ ${#WT_WIN} -gt $MAX_ROOT_LEN ]]; then
    echo "[ready-pr] UNCHECKED — worktree path is ${#WT_WIN} chars, over the ${MAX_ROOT_LEN} budget:"
    echo "[ready-pr]   $WT_WIN"
    echo "[ready-pr] The suite would fail on path length, not on merit."
    exit 2
fi

echo "[ready-pr] branch  : $BRANCH"
echo "[ready-pr] worktree: $WT_WIN (${#WT_WIN} chars, budget $MAX_ROOT_LEN)"

if [[ ! -d "$WT" ]]; then
    if ! git -C "$REPO_ROOT" worktree add "$WT_WIN" "$BRANCH" >/dev/null 2>&1; then
        echo "[ready-pr] UNCHECKED — could not create a worktree for $BRANCH."
        echo "[ready-pr] It may be checked out elsewhere already: git worktree list"
        exit 2
    fi
    echo "[ready-pr] worktree created."
else
    echo "[ready-pr] reusing existing worktree."
fi

cd "$WT" || { echo "[ready-pr] UNCHECKED — cannot enter $WT"; exit 2; }

# ── Step 2: refuse to measure a dirty tree ─────────────────────────────────
#
# A suite run over uncommitted edits measures something that is not the branch.
# On 2026-08-08 I read 11 failures as a branch's when they were my own
# half-finished edit sitting in the tree.
if [[ -n "$(git status --porcelain)" ]]; then
    echo "[ready-pr] UNCHECKED — working tree is dirty. A run over uncommitted edits"
    echo "[ready-pr] measures something other than the branch. Commit or stash first:"
    git status --porcelain | head -10
    exit 2
fi

# ── Step 4a: bring main in ──────────────────────────────────────────────────
#
# The freshness gate refuses stale branches at push time. Merge rather than
# rebase: these branches are published, and a rebase rewrites every hash,
# turning the next push into a force-push against work another agent may have
# added (learned the hard way 2026-07-09).
git fetch -q origin main 2>/dev/null
if ! git merge origin/main --no-edit >/tmp/ready_pr_merge.txt 2>&1; then
    echo "[ready-pr] NOT-READY — merging main conflicts. Resolve by hand:"
    tail -15 /tmp/ready_pr_merge.txt
    exit 1
fi
echo "[ready-pr] main merged: $(tail -1 /tmp/ready_pr_merge.txt)"

# ── Step 4b: does this branch's push gate carry the GIT_DIR scrub? ──────────
#
# Root cause found 2026-08-08: git exports GIT_DIR into hook processes. The
# pre-push gate ran pytest without clearing it; GIT_DIR overrides cwd; so a
# test building a scratch bare repo hit the REAL repository and set
# core.bare=true on it, breaking git in every worktree until reset by hand.
# Weeks of "git randomly breaks" were this.
#
# The fix lives in scripts/check_push_readiness.sh. A branch predating it
# still spills. Runs after the merge (main may already carry it) and before
# the multi-minute suite, so the suite measures the branch as it will be
# pushed rather than as it was.
#
# The answer never varies: every branch needs this before it can push safely.
# A choice-point whose answer is always the same is a choice-point the lazy
# path will eventually get wrong, so the routine carries the fix rather than
# warning me to carry it (foundational truth #11, remediation A — take the
# option away). I hand-applied it to two branches before writing this; there
# were eight more waiting, which is the whole argument.
SCRUB_FIX_COMMIT="e7bbbb40"
if grep -q "GIT_ENV_SCRUB" scripts/check_push_readiness.sh 2>/dev/null; then
    SCRUB_MISSING=0
    echo "[ready-pr] GIT_DIR scrub: present."
else
    echo "[ready-pr] GIT_DIR scrub missing — carrying the fix onto this branch."
    if ! git cat-file -e "${SCRUB_FIX_COMMIT}^{commit}" 2>/dev/null; then
        SCRUB_MISSING=1
        echo "[ready-pr] Cannot: commit $SCRUB_FIX_COMMIT is not in this repo."
        echo "[ready-pr] --push will be refused; the CHECK still runs."
    elif git cherry-pick "$SCRUB_FIX_COMMIT" >/tmp/ready_pr_cp.txt 2>&1; then
        SCRUB_MISSING=0
        echo "[ready-pr] fix applied: $(git log --oneline -1)"
    else
        git cherry-pick --abort 2>/dev/null
        SCRUB_MISSING=1
        echo "[ready-pr] Cherry-pick conflicted; branch left untouched:"
        tail -6 /tmp/ready_pr_cp.txt
        echo "[ready-pr] Resolve by hand. --push refused; the CHECK still runs."
    fi
fi


# ── Step 5: the suite ──────────────────────────────────────────────────────
#
# Draft PRs skip CI deliberately, so the remote shows neither red nor green.
# Running it here is the only way to know. Green-because-nothing-ran is the
# shape this whole file stands against.
echo "[ready-pr] running the suite (several minutes)..."
LOG="/tmp/ready_pr_${SLUG}.log"
python -m pytest tests/ -q --tb=line -n auto >"$LOG" 2>&1
RC=$?
SUMMARY="$(tail -1 "$LOG")"

# pytest: 0 = passed, 1 = tests failed, 2..5 = could not run properly (usage
# error, collection error, interrupted, internal). Collapsing 2+ into "failed"
# would report a broken instrument as a broken branch.
if [[ $RC -eq 0 ]]; then
    echo "[ready-pr] READY — $SUMMARY"
elif [[ $RC -eq 1 ]]; then
    echo "[ready-pr] NOT-READY — $SUMMARY"
    echo "[ready-pr] Failures (full log: $LOG):"
    grep -E "^FAILED|^ERROR" "$LOG" | head -15
    exit 1
else
    echo "[ready-pr] UNCHECKED — pytest exited $RC; it did not run to completion."
    echo "[ready-pr] Do NOT read this as 'the branch is fine'. Nothing was measured."
    tail -15 "$LOG"
    exit 2
fi

# ── Step 6: hand off the push, and check the repo survived it ──────────────
if [[ $DO_PUSH -eq 1 ]]; then
    if [[ $SCRUB_MISSING -eq 1 ]]; then
        echo "[ready-pr] push REFUSED — the GIT_DIR scrub is missing on this branch."
        echo "[ready-pr] The branch is READY; pushing is the part that would do damage."
        exit 0
    fi
    BARE_BEFORE="$(git -C "$REPO_ROOT" config --local core.bare)"
    echo "[ready-pr] handing off to safe_push.sh..."
    bash scripts/safe_push.sh origin main
    PUSH_RC=$?
    BARE_AFTER="$(git -C "$REPO_ROOT" config --local core.bare)"
    # Cheap, and it is the exact damage that went unnoticed for weeks.
    if [[ "$BARE_BEFORE" != "$BARE_AFTER" ]]; then
        echo "[ready-pr] ALARM: core.bare changed during the push ($BARE_BEFORE -> $BARE_AFTER)."
        echo "[ready-pr] Resetting it. The scrub is not holding — investigate before pushing again."
        git -C "$REPO_ROOT" config --local core.bare false
        exit 2
    fi
    if [[ $PUSH_RC -ne 0 ]]; then
        echo "[ready-pr] push failed (exit $PUSH_RC). Repo config is unchanged."
        exit 1
    fi
    echo "[ready-pr] pushed, and the repo config is unchanged."
fi

exit 0
