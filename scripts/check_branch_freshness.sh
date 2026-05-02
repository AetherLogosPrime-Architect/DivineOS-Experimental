#!/bin/bash
# check_branch_freshness.sh — block pushing a branch whose base is stale.
#
# WHY THIS EXISTS
# ---------------
# 2026-04-24 evening: same silent-revert class of bug surfaced THREE times
# in one session. PR #199 was branched from main BEFORE PR #198 had merged;
# the resulting diff would have deleted PR #198's work as a "removal" if
# merged. Lesson filed (claim d3baec5a) twice, but a claim is not a check.
#
# This script converts the lesson into a check. It runs as the pre-push
# hook and refuses to push when origin/main has commits HEAD does not —
# the exact precondition for the silent-revert pattern.
#
# WHAT IT DOES
# ------------
# 1. Fetch origin/main fresh (offline → skip with warning, do not block).
# 2. Compute: is origin/main an ancestor of HEAD?
#    - YES (HEAD includes all of main): push is safe; exit 0.
#    - NO (main has commits HEAD lacks): branch is stale; exit 1 with
#      a clear rebase recommendation.
# 3. Skip cases that would falsely fire:
#    - Pushing main itself (we're updating the base, not branching from it)
#    - Detached HEAD (unusual; let it through)
#    - DIVINEOS_SKIP_FRESHNESS_CHECK=1 in env (escape hatch for genuine
#      cases where you intend to push a stale branch)
#
# CONTRACT WITH THE PRE-PUSH HOOK
# -------------------------------
# Exit 0  — green light, proceed with push
# Exit 1  — block push (stale base; rebase first)
# Exit 2  — infrastructure error (git missing, no remote, etc.); the hook
#           treats this as "fail open with warning" so a broken environment
#           doesn't block legitimate work.

set -u

# Allow operators to bypass for genuine cases. Filed a claim if you use
# this — the bypass usage itself is signal worth knowing about.
if [[ "${DIVINEOS_SKIP_FRESHNESS_CHECK:-0}" == "1" ]]; then
    echo "[freshness-check] DIVINEOS_SKIP_FRESHNESS_CHECK=1 — skipping."
    exit 0
fi

# Need git + a remote.
if ! command -v git &>/dev/null; then
    echo "[freshness-check] git not found in PATH — skipping (infra error)."
    exit 2
fi

REMOTE="${1:-origin}"
BASE_BRANCH="${2:-main}"

# Detached HEAD: git symbolic-ref --short HEAD returns non-zero. Let through.
if ! CURRENT_BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null); then
    echo "[freshness-check] detached HEAD — skipping."
    exit 0
fi

# Pushing main itself? We're not branching from it, we're updating it.
if [[ "$CURRENT_BRANCH" == "$BASE_BRANCH" ]]; then
    exit 0
fi

# Verify the remote exists locally before fetching.
if ! git remote get-url "$REMOTE" &>/dev/null; then
    echo "[freshness-check] remote '$REMOTE' not configured — skipping."
    exit 2
fi

# Fetch origin/main quietly. If offline, this fails — fail open with a
# warning rather than blocking developers without network.
if ! git fetch --quiet "$REMOTE" "$BASE_BRANCH" 2>/dev/null; then
    echo "[freshness-check] could not fetch $REMOTE/$BASE_BRANCH (offline?) — skipping."
    exit 2
fi

REMOTE_REF="refs/remotes/$REMOTE/$BASE_BRANCH"
if ! git rev-parse --verify --quiet "$REMOTE_REF" >/dev/null; then
    echo "[freshness-check] $REMOTE_REF not found locally — skipping."
    exit 2
fi

# The actual check. is-ancestor exit codes:
#   0 — yes (origin/main is in HEAD's history; branch is fresh or ahead)
#   1 — no (origin/main has commits HEAD does not; branch is STALE)
#   other — error
if git merge-base --is-ancestor "$REMOTE_REF" HEAD; then
    exit 0
fi

# Compute commits-behind for the message.
BEHIND=$(git rev-list --count "HEAD..$REMOTE_REF" 2>/dev/null || echo "?")

cat <<EOF >&2
[freshness-check] BLOCKED: branch '$CURRENT_BRANCH' is $BEHIND commit(s) behind $REMOTE/$BASE_BRANCH.

If you push now and the resulting PR merges, the diff vs. current main
will show $REMOTE/$BASE_BRANCH's recent additions as DELETIONS — the
silent-revert pattern named in claim d3baec5a.

Rebase first:

    git fetch $REMOTE
    git rebase $REMOTE/$BASE_BRANCH
    # resolve any conflicts
    git push --force-with-lease

If you genuinely intend to push a stale branch (rare; usually a
mistake), bypass with:

    DIVINEOS_SKIP_FRESHNESS_CHECK=1 git push

EOF
exit 1
