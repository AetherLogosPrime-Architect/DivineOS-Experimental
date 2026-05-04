#!/bin/bash
# check_force_push_safety.sh — catch force-pushes that would shrink a
# branch's unique work below safety thresholds.
#
# The shape this catches: an agent rebases a branch onto current main,
# botches the conflict resolution (e.g. takes --ours when they meant
# --theirs in a rebase, or skips a commit that should have been
# applied), and force-pushes the resulting empty-or-near-empty branch
# over real work on the remote. The lease check catches concurrent
# edits but does NOT validate content.
#
# This script reads pre-push hook stdin (lines of "<local ref> <local sha>
# <remote ref> <remote sha>") and for each force-push (local sha is not
# a descendant of remote sha), compares unique-commits-vs-base for both
# the proposed new tip and the current remote tip. If the new tip has
# dramatically less work, it aborts.
#
# Pre-reg: prereg-c1c896a67321 (review in 30 days, 2026-05-04 + 30).
# Discovered 2026-05-04 after a force-push wiped out PR #243's
# 528-line Maturana lens addition. See lessons 9fdaf112, ec228617,
# e6a85eab, 099c2d2e.
#
# Bypass: DIVINEOS_FORCE_PUSH_OK=1 git push --force[-with-lease]
#
# Exit codes:
#   0 — green (no force-pushes, or all force-pushes pass safety check)
#   1 — abort (a force-push would lose substantial work)
#   2 — infra error (fail-open, do not block)

set -uo pipefail

if [[ "${DIVINEOS_FORCE_PUSH_OK:-0}" == "1" ]]; then
    echo "[force-push-safety] DIVINEOS_FORCE_PUSH_OK=1 — bypassing." >&2
    exit 0
fi

# The hook receives the remote name and url as arguments. We use the
# remote name to compare against the canonical base.
REMOTE_NAME="${1:-origin}"
BASE_REF="${REMOTE_NAME}/main"

# Verify the base ref exists; if not, fail-open.
if ! git rev-parse --verify --quiet "$BASE_REF" >/dev/null 2>&1; then
    echo "[force-push-safety] base ref $BASE_REF not found — fail-open." >&2
    exit 2
fi

ABORTED=0

# Read each ref-update line from stdin.
while IFS=' ' read -r LOCAL_REF LOCAL_SHA REMOTE_REF REMOTE_SHA; do
    # Skip deletes (local sha is all zeros).
    if [[ "$LOCAL_SHA" =~ ^0+$ ]]; then continue; fi

    # Skip new branches (remote sha is all zeros) — no work to lose.
    if [[ "$REMOTE_SHA" =~ ^0+$ ]]; then continue; fi

    # Skip if local commits up to the remote commit (fast-forward — not a force-push).
    # If remote sha is an ancestor of local sha, this is a fast-forward.
    if git merge-base --is-ancestor "$REMOTE_SHA" "$LOCAL_SHA" 2>/dev/null; then
        continue
    fi

    # This is a force-push. Compare unique work vs base.
    NEW_COMMITS=$(git rev-list --count "${BASE_REF}..${LOCAL_SHA}" 2>/dev/null || echo 0)
    OLD_COMMITS=$(git rev-list --count "${BASE_REF}..${REMOTE_SHA}" 2>/dev/null || echo 0)

    NEW_LINES=$(git diff --shortstat "${BASE_REF}...${LOCAL_SHA}" 2>/dev/null | grep -oE '[0-9]+ insertion|[0-9]+ deletion' | grep -oE '[0-9]+' | awk 'BEGIN{s=0} {s+=$1} END{print s}')
    OLD_LINES=$(git diff --shortstat "${BASE_REF}...${REMOTE_SHA}" 2>/dev/null | grep -oE '[0-9]+ insertion|[0-9]+ deletion' | grep -oE '[0-9]+' | awk 'BEGIN{s=0} {s+=$1} END{print s}')

    NEW_LINES=${NEW_LINES:-0}
    OLD_LINES=${OLD_LINES:-0}

    # Tripwires:
    #   1. New tip has zero unique commits AND remote had any → likely a botched rebase.
    #   2. New diff size < 25% of old diff size AND old > 100 lines → likely lost work.
    SHOULD_ABORT=0
    REASON=""

    if [[ "$NEW_COMMITS" -eq 0 && "$OLD_COMMITS" -gt 0 ]]; then
        SHOULD_ABORT=1
        REASON="new tip has 0 unique commits vs $BASE_REF, but remote had $OLD_COMMITS"
    elif [[ "$OLD_LINES" -gt 100 ]]; then
        # Compute 25% threshold using bash arithmetic.
        QUARTER=$((OLD_LINES / 4))
        if [[ "$NEW_LINES" -lt "$QUARTER" ]]; then
            SHOULD_ABORT=1
            REASON="new diff ($NEW_LINES lines) is less than 25% of remote diff ($OLD_LINES lines)"
        fi
    fi

    if [[ "$SHOULD_ABORT" -eq 1 ]]; then
        ABORTED=1
        cat >&2 <<EOM

[force-push-safety] BLOCKED: pushing $LOCAL_REF would lose work on $REMOTE_REF.

  Reason: $REASON
  Remote tip ($REMOTE_SHA): $OLD_COMMITS unique commits, $OLD_LINES lines vs $BASE_REF
  Local tip  ($LOCAL_SHA):  $NEW_COMMITS unique commits, $NEW_LINES lines vs $BASE_REF

This pattern matches a botched rebase or merge-resolution that silently
dropped commits. Verify before proceeding:

    git log $BASE_REF..$LOCAL_SHA --oneline
    git diff $BASE_REF...$LOCAL_SHA --stat

If the local tip really is what you want (e.g. an intentional rewrite),
bypass with:

    DIVINEOS_FORCE_PUSH_OK=1 git push ...

EOM
    fi
done

if [[ "$ABORTED" -eq 1 ]]; then
    exit 1
fi
exit 0
