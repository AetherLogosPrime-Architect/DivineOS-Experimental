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

# Allow operators to bypass for genuine cases.
#
# 2026-07-17 jailbreak-response wiring (Andrew's directive): every use
# of the bypass auto-files an open error into the registry. The block
# is at the "start-next-project" boundary, not at any tool — this push
# still proceeds. But the next `divineos goal add` for a NEW main goal
# is refused until this error is either closed (root-cause fixed) or
# operator-deferred with a >=20-char reason. Removes the choice-point
# where a bypass could silently escape attribution.
if [[ "${DIVINEOS_SKIP_FRESHNESS_CHECK:-0}" == "1" ]]; then
    echo "[freshness-check] DIVINEOS_SKIP_FRESHNESS_CHECK=1 — skipping."
    # Best-effort auto-file the bypass event, but FIRE-AND-FORGET —
    # the divineos import cost (~5-10s Python startup) must not add to
    # the push path or the pre-push test-timeout budget. Backgrounded
    # via nohup + disowned; the parent script returns instantly. If the
    # background call fails silently the bypass still proceeds; missed
    # attribution surfaces at next goal-add via absence, not via
    # blocking the bypass itself. Skipped entirely in test environments
    # (DIVINEOS_TEST_ENV=1 set by test fixtures) to keep test runtime
    # deterministic and off the divineos install path.
    if [[ "${DIVINEOS_TEST_ENV:-0}" != "1" ]] && command -v divineos &>/dev/null; then
        _summary="Freshness-check bypass used ($(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null))"
        _context="branch=$(git symbolic-ref --short HEAD 2>/dev/null || echo unknown) cwd=$(pwd)"
        _hint="scripts/check_branch_freshness.sh — investigate why local base was stale before rebase. Common cause: rebased against stale origin/main snapshot without git fetch first. Fix: use scripts/safe_push.sh which fetches + auto-rebases + pushes atomically."
        nohup divineos error file \
            --source bypass \
            --summary "$_summary" \
            --context "$_context" \
            --hint "$_hint" \
            >/dev/null 2>&1 </dev/null &
        disown 2>/dev/null || true
    fi
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

MERGE main into this branch (preferred — preserves commit hashes so
the push fast-forwards; no force-push required):

    git fetch $REMOTE
    git merge $REMOTE/$BASE_BRANCH
    # resolve any conflicts
    git push

Rebase is also an option but rewrites every commit hash on this
branch. If the branch already exists on $REMOTE, the following push
becomes a non-fast-forward and requires --force-with-lease, which
opens a real footgun any time another agent has pushed to the same
branch (Aether 2026-07-09, learned the hard way after a rebase-loop
during the memory-linkage v2 ship). Prefer merge unless you have a
specific reason to rewrite history:

    git fetch $REMOTE
    git rebase $REMOTE/$BASE_BRANCH
    git push --force-with-lease   # danger: verify remote state first

If you genuinely intend to push a stale branch (rare; usually a
mistake), bypass with:

    DIVINEOS_SKIP_FRESHNESS_CHECK=1 git push

EOF
exit 1
