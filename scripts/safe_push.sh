#!/bin/bash
# safe_push.sh — atomic fetch → freshness-check → auto-rebase → push
#
# WHY THIS EXISTS
# ---------------
# 2026-07-17 pattern: rebased a branch against a STALE local origin/main
# snapshot, then pushed. Pre-push freshness-check caught the drift
# correctly and blocked with "branch is stale, needs rebase." Bypass was
# reached for and used because the diagnostic was one env var away.
# Root cause: the sequence `git fetch → git rebase → git push` has a
# choice-point at step-one that I skipped. Every stale-rebase silently
# gets past the choice-point.
#
# WHAT THIS DOES
# --------------
# Removes the choice-point. Fetches base fresh, rebases if needed against
# the fresh base, then pushes. One atomic operation, no place to skip the
# fetch. Aligns with truth #11(a): take the option away.
#
# Usage:
#   scripts/safe_push.sh [remote] [base_branch]
#   Defaults: remote=origin, base_branch=main
#
# Exit codes:
#   0 — push succeeded (with or without an auto-rebase step)
#   1 — refused (on base branch / detached HEAD / dirty tree)
#   2 — rebase conflict (needs manual resolution, script aborts cleanly)
#   3 — push failed (network / permission / other git error)

set -u

REMOTE="${1:-origin}"
BASE_BRANCH="${2:-main}"

log() { printf '[safe-push] %s\n' "$*"; }

# --- Preflight ---

if ! CURRENT_BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null); then
    log "REFUSED: detached HEAD. Check out a branch first."
    exit 1
fi

if [[ "$CURRENT_BRANCH" == "$BASE_BRANCH" ]]; then
    log "REFUSED: on the base branch '$BASE_BRANCH'. Nothing to rebase."
    log "         Use 'git push' directly for base-branch updates."
    exit 1
fi

if [[ -n "$(git status --porcelain 2>/dev/null)" ]]; then
    log "REFUSED: working tree has uncommitted changes."
    log "         Commit or stash first — an auto-rebase step would fail."
    exit 1
fi

if ! git remote get-url "$REMOTE" &>/dev/null; then
    log "REFUSED: remote '$REMOTE' not configured."
    exit 1
fi

# --- Fetch fresh ---

log "fetch $REMOTE/$BASE_BRANCH ..."
if ! git fetch --quiet "$REMOTE" "$BASE_BRANCH" 2>&1; then
    log "fetch failed (offline?). Aborting rather than proceeding with stale data."
    exit 3
fi

REMOTE_REF="refs/remotes/$REMOTE/$BASE_BRANCH"
if ! git rev-parse --verify --quiet "$REMOTE_REF" >/dev/null; then
    log "REFUSED: $REMOTE_REF not resolvable after fetch."
    exit 3
fi

# --- Auto-rebase if stale ---

if git merge-base --is-ancestor "$REMOTE_REF" HEAD; then
    log "branch is fresh relative to $REMOTE/$BASE_BRANCH — no rebase needed"
else
    BEHIND=$(git rev-list --count "HEAD..$REMOTE_REF" 2>/dev/null || echo "?")
    log "branch is $BEHIND commit(s) behind $REMOTE/$BASE_BRANCH — auto-rebasing"
    if ! git rebase "$REMOTE_REF" 2>&1; then
        log ""
        log "REBASE CONFLICT — needs manual resolution:"
        log "  1. Resolve conflicts in the listed files"
        log "  2. git add <resolved-files>"
        log "  3. git rebase --continue    (or --abort to give up)"
        log "  4. re-run this script when done"
        exit 2
    fi
    log "rebase clean — HEAD is now on top of fresh $REMOTE/$BASE_BRANCH"
fi

# --- Push (force-with-lease so we never stomp another push we didn't fetch) ---

log "push $REMOTE $CURRENT_BRANCH --force-with-lease"
if git push "$REMOTE" "$CURRENT_BRANCH" --force-with-lease 2>&1; then
    log "push landed."
    exit 0
else
    log "push failed. See error above."
    exit 3
fi
