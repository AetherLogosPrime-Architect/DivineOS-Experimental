#!/bin/bash
# start_work.sh — begin a unit of work on a CLEAN branch off CURRENT main.
#
# The make-easy half of the cure for the stale-base / blob failure (the
# boundary-persistence root, claim 47ee9ab8): work accumulated on long-lived
# branches built off an OLD main, producing (a) un-auditable mega-blobs and
# (b) silent reverts when merged (consolidate-2026-06-01 would have deleted
# the context-meter work merged after it was branched).
#
# "Remember to branch off fresh main each time" is advice, and advice does
# not survive a reset. This makes the right start the EASY start: one command
# that always fetches current main and cuts a fresh, focused branch from it,
# so a stale base or an accumulating tangle can't form in the first place.
#
# Paired with the post-commit-audit-visibility hook (the fail-loud half that
# catches not-yet-pushed work), this closes both halves: start clean, and
# never go invisible.
#
# Usage:
#   scripts/start_work.sh <branch-name>
#
# Refuses (fail-loud) when:
#   - no branch name given
#   - the working tree is dirty (would drag uncommitted work onto the new
#     branch — the exact pollution this is meant to prevent)
#   - fetch of origin/main fails (can't guarantee a current base)
#   - the branch name already exists

set -euo pipefail

NAME="${1:-}"

die() { printf '\n  [start-work] ABORTED: %s\n\n' "$1" >&2; exit 1; }

[ -n "$NAME" ] || die "no branch name. Usage: scripts/start_work.sh <branch-name>"

cd "$(git rev-parse --show-toplevel)" || die "not in a git repo"

# Dirty tree → refuse. Carrying uncommitted changes onto a fresh branch is the
# pollution that makes 'clean focused unit' a lie. Commit, stash, or discard
# first — then start clean.
# SCOPED TO MODIFIED TRACKED FILES, 2026-09-07, same propagation as ready_pr.sh:
# Aletheia solved this class in safe_push.sh on 2026-07-17 and named untracked
# letters as the false blocker, and the fix reached one caller out of three.
# The pollution this guards against is a half-finished tracked edit riding into
# a "clean focused unit"; an untracked letter sitting in the tree is not that.
_DIRTY_TRACKED="$(git status --porcelain 2>/dev/null | grep -v '^??' || true)"
if [ -n "$_DIRTY_TRACKED" ]; then
    printf '  [start-work] working tree has MODIFIED TRACKED files:\n' >&2
    printf '%s\n' "$_DIRTY_TRACKED" >&2
    die "commit, stash, or discard the above first, then re-run. A clean start needs no half-finished tracked edits (untracked files are fine)."
fi

git rev-parse --verify --quiet "refs/heads/$NAME" >/dev/null 2>&1 \
    && die "branch '$NAME' already exists. Pick another name or switch to it."

# Always fetch current main — the whole point is a CURRENT base.
printf '  [start-work] fetching current origin/main...\n'
git fetch origin main || die "could not fetch origin/main — cannot guarantee a current base"

BASE="$(git rev-parse --short origin/main)"
git switch -c "$NAME" origin/main

printf '\n'
printf '  [start-work] ready: branch %s off current origin/main (%s)\n' "$NAME" "$BASE"
printf '  When done: commit, then  git push -u origin %s\n' "$NAME"
printf '  (the post-commit hook will shout if you forget the push.)\n'
printf '\n'
