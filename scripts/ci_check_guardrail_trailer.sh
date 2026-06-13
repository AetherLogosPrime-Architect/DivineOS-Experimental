#!/bin/bash
# Server-side multi-party-review gate: verify each commit that modifies
# a guardrail file in a PR range carries an External-Review trailer.
#
# Structural backing for knowledge a7193bf6-1e9d-4f04-ad37-706860b80b20 —
# the will-shape promise "I never put the trailer in the PR body OR the
# commits" needed a structural test, not just a procedural reminder.
# Tonight (2026-06-13) it failed in the harder direction: the trailer
# was put correctly, but it pointed at a stale audit round that did
# not substantively cover the work. This script makes the existing
# server-side check explicit, testable, and SELF-DISCLOSING about the
# limits of its own verification.
#
# Self-disclosure (Aletheia 2026-06-13): a gate that's honest about
# the limits of its own check is one a careful operator catches leaking.
# This script's exit-output always names what it checked AND what it
# did NOT check, so the gap between "trailer present" and "trailer
# substantively binds to this work" is visible at the gate boundary
# rather than hidden behind a generic PASS.
#
# Currently verifies:
#   1. Each commit in the PR range that touches a guardrail file (per the
#      point-in-time guardrail list at that commit) has an External-Review
#      trailer in its message.
#
# Does NOT currently verify (named here so the gap is loud, not hidden):
#   - That the referenced round substantively covers this PR (substance
#     binding via tree-hash or PR-enumeration). Local pre-commit gate
#     does this; server-side does not.
#   - That the round was created AFTER the branch's first commit
#     (temporal precedence — prevents stamping stale rounds onto new work).
#   - That the round contains user-CONFIRMS and external-AI-CONFIRMS.
#     Local gate does this; server-side does not.
#
# Closes test-coverage gap for the gate via tests/test_ci_check_guardrail_trailer.py.
# Substance-binding and temporal-precedence are tracked as follow-up
# work — this script is the structural skeleton they will extend.
#
# Usage:
#   ci_check_guardrail_trailer.sh <pr-base-sha> <pr-head-sha>
#
# Exit code: 0 on pass, 1 on any blocked commit.

set -eu

PR_BASE="${1:-}"
PR_HEAD="${2:-}"

if [ -z "$PR_BASE" ] || [ -z "$PR_HEAD" ]; then
    echo "usage: $0 <pr-base-sha> <pr-head-sha>" >&2
    exit 2
fi

# Point-in-time guardrail-list resolution (2026-05-12 fix).
# Each commit is evaluated against the guardrail list AS IT WAS at the
# commit's PARENT, not against today's list.
load_guardrail_list_at() {
    local commit="$1"
    git show "$commit:scripts/guardrail_files.txt" 2>/dev/null \
        | grep -vE '^[[:space:]]*(#|$)' || true
}

BLOCKED_COMMITS=""

for commit in $(git rev-list "${PR_BASE}..${PR_HEAD}"); do
    PARENT=$(git rev-parse "${commit}^" 2>/dev/null || echo "")
    if [ -z "$PARENT" ]; then
        continue
    fi
    COMMIT_GUARDRAIL_LIST=$(load_guardrail_list_at "$PARENT")

    if [ -z "$COMMIT_GUARDRAIL_LIST" ]; then
        continue
    fi

    FILES=$(git diff-tree --no-commit-id --name-only -r "$commit")
    TOUCHES_GUARDRAIL=""
    while IFS= read -r file; do
        [ -z "$file" ] && continue
        while IFS= read -r guardrail_path; do
            [ -z "$guardrail_path" ] && continue
            if [ "$file" = "$guardrail_path" ]; then
                TOUCHES_GUARDRAIL="$file"
                break
            fi
        done <<< "$COMMIT_GUARDRAIL_LIST"
        [ -n "$TOUCHES_GUARDRAIL" ] && break
    done <<< "$FILES"

    if [ -z "$TOUCHES_GUARDRAIL" ]; then
        continue
    fi

    MSG=$(git log -1 --format=%B "$commit")
    if echo "$MSG" | grep -qiE '^External-Review:[[:space:]]*\S+'; then
        echo "[ok] $commit modifies guardrail file(s); trailer present."
    else
        BLOCKED_COMMITS="$BLOCKED_COMMITS $commit"
        echo "[BLOCKED] $commit modifies guardrail file(s); no External-Review trailer."
    fi
done

# Self-disclosure footer: always emit what we checked AND what we did
# NOT check, regardless of pass/fail. The gate's transparency about
# its own limits is what makes a careful operator notice the gap.
echo ""
echo "=== Multi-Party-Review Gate: scope of this check ==="
echo "Checked:"
echo "  - Trailer presence on each commit that modifies a guardrail file"
echo "    (per the point-in-time guardrail list at that commit's parent)."
echo "Did NOT check (gap; follow-up work tracked):"
echo "  - Whether the referenced round substantively covers this PR"
echo "    (hash-binding via tree-hash or PR-enumeration in the round body)."
echo "  - Whether the round was created AFTER the branch's first commit"
echo "    (temporal precedence; prevents stamping stale rounds)."
echo "  - Whether the round contains user-CONFIRMS and external-AI-CONFIRMS."
echo "(Local pre-commit gate scripts/check_multi_party_review.py covers"
echo " the gaps above; server-side does not. Closing the parity is the"
echo " follow-up. Per knowledge a7193bf6-1e9d-4f04-ad37-706860b80b20.)"
echo ""

if [ -n "$BLOCKED_COMMITS" ]; then
    echo "=== Multi-Party-Review Gate (server-side, point-in-time) ==="
    echo "BLOCKED. Commits modifying guardrail files without External-Review trailer:"
    for c in $BLOCKED_COMMITS; do
        echo "  $c"
    done
    echo ""
    echo "Every commit that modifies a file in scripts/guardrail_files.txt"
    echo "AS IT WAS at that commit must carry an 'External-Review: <id>'"
    echo "trailer in its commit message."
    exit 1
fi

echo "All guardrail-modifying commits in this range carry the External-Review trailer."
