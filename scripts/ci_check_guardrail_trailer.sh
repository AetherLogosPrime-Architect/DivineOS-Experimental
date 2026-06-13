#!/bin/bash
# Server-side multi-party-review gate: verify each commit that modifies
# a guardrail file in a PR range carries a valid External-Review trailer.
#
# Trailer formats accepted:
#
#   External-Review: <round-id>
#       Legacy form (Phase 1). Trailer presence only — no substance
#       binding. Emits a DEPRECATION warning naming the bypass the
#       2026-06-13 substance-bypass session lived through. Still
#       passes during the transition window so existing trailers
#       don't break overnight; once tooling is updated to emit
#       tree-hash, the deprecation warning becomes a hard block via
#       the REQUIRE_TREE_HASH env var (default off).
#
#   External-Review: <round-id> tree-hash:<40-hex>
#       Phase 2 (substance-binding). The trailer commits to a specific
#       tree state; the gate verifies the tree-hash matches the
#       commit's actual tree-hash. A stale round-id stamped on new
#       work fails this check because the round's tree-hash claim
#       won't match the commit's actual tree.
#
# Closes the substance gap named in find-f128475b5b65 follow-up:
# trailer text alone passed the old check even when the referenced
# round was unrelated to the work. With tree-hash binding, the round
# must have been filed knowing the exact tree being authorized.
#
# Self-disclosure (Aletheia 2026-06-13): a gate that's honest about
# the limits of its own check is one a careful operator catches leaking.
# The exit-output always names what was checked AND what was not.
#
# Per knowledge a7193bf6-1e9d-4f04-ad37-706860b80b20.
#
# Usage:
#   ci_check_guardrail_trailer.sh <pr-base-sha> <pr-head-sha>
#
# Env:
#   REQUIRE_TREE_HASH=1 — fail when a trailer is missing the tree-hash
#     field. Off by default so existing trailers stay valid during the
#     transition window. Tooling-rollout flips this on once the
#     trailer-generating helpers default to including tree-hash.
#
# Exit code: 0 on pass, 1 on any blocked commit.

set -eu

PR_BASE="${1:-}"
PR_HEAD="${2:-}"
REQUIRE_TREE_HASH="${REQUIRE_TREE_HASH:-0}"

if [ -z "$PR_BASE" ] || [ -z "$PR_HEAD" ]; then
    echo "usage: $0 <pr-base-sha> <pr-head-sha>" >&2
    exit 2
fi

# Point-in-time guardrail-list resolution (2026-05-12 fix).
load_guardrail_list_at() {
    local commit="$1"
    git show "$commit:scripts/guardrail_files.txt" 2>/dev/null \
        | grep -vE '^[[:space:]]*(#|$)' || true
}

# Parse the External-Review trailer line out of a commit message.
# Returns the raw trailer line (everything after "External-Review:")
# or empty if no trailer present.
parse_trailer_line() {
    echo "$1" | grep -iE '^External-Review:[[:space:]]*\S+' | head -1
}

# Extract the tree-hash field from a trailer line, if present.
# Returns the 40-hex hash or empty.
parse_trailer_tree_hash() {
    echo "$1" | grep -oE 'tree-hash:[a-f0-9]{40}' | head -1 | sed 's/tree-hash://'
}

BLOCKED_COMMITS=""
SUBSTANCE_BOUND_COUNT=0
LEGACY_TRAILER_COUNT=0

# --first-parent skips commits absorbed via merge from an upstream remote.
# Those commits' review happened upstream (or rides on the merge commit's
# own trailer if the merge itself touches a guardrail file). Without
# --first-parent the gate retroactively re-validates upstream history
# every time a downstream branch merges. Closed 2026-05-01.
for commit in $(git rev-list --first-parent "${PR_BASE}..${PR_HEAD}"); do
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
    TRAILER=$(parse_trailer_line "$MSG")

    if [ -z "$TRAILER" ]; then
        BLOCKED_COMMITS="$BLOCKED_COMMITS $commit"
        echo "[BLOCKED] $commit modifies guardrail file(s); no External-Review trailer."
        continue
    fi

    # Trailer present. Now check substance-binding via tree-hash.
    TRAILER_TREE_HASH=$(parse_trailer_tree_hash "$TRAILER")

    if [ -z "$TRAILER_TREE_HASH" ]; then
        # Legacy trailer (Phase 1). Pass with a warning unless
        # REQUIRE_TREE_HASH is set.
        LEGACY_TRAILER_COUNT=$((LEGACY_TRAILER_COUNT + 1))
        if [ "$REQUIRE_TREE_HASH" = "1" ]; then
            BLOCKED_COMMITS="$BLOCKED_COMMITS $commit"
            echo "[BLOCKED] $commit trailer is missing tree-hash binding (REQUIRE_TREE_HASH=1)."
        else
            echo "[ok] $commit trailer present (legacy; no tree-hash binding)."
            echo "    [warn] DEPRECATED: trailer should include 'tree-hash:<40-hex>' for substance binding."
            echo "    [warn] Without tree-hash, the gate cannot verify the round actually covers this commit."
        fi
        continue
    fi

    # Substance-binding present. Verify it matches.
    ACTUAL_TREE_HASH=$(git rev-parse "${commit}^{tree}" 2>/dev/null || echo "")
    if [ -z "$ACTUAL_TREE_HASH" ]; then
        BLOCKED_COMMITS="$BLOCKED_COMMITS $commit"
        echo "[BLOCKED] $commit: could not resolve tree-hash for verification."
        continue
    fi

    if [ "$TRAILER_TREE_HASH" = "$ACTUAL_TREE_HASH" ]; then
        SUBSTANCE_BOUND_COUNT=$((SUBSTANCE_BOUND_COUNT + 1))
        echo "[ok] $commit trailer present + tree-hash binding verified."
    else
        BLOCKED_COMMITS="$BLOCKED_COMMITS $commit"
        echo "[BLOCKED] $commit: tree-hash in trailer does not match commit's actual tree."
        echo "    trailer says: tree-hash:$TRAILER_TREE_HASH"
        echo "    commit's actual tree-hash: $ACTUAL_TREE_HASH"
        echo "    -> the round was filed against a different tree; cannot authorize this commit."
    fi
done

# Self-disclosure footer: always emit what was checked AND what was not.
echo ""
echo "=== Multi-Party-Review Gate: scope of this check ==="
echo "Checked:"
echo "  - Trailer presence on each commit that modifies a guardrail file"
echo "    (per the point-in-time guardrail list at that commit's parent)."
echo "  - Tree-hash binding when the trailer includes tree-hash:<40-hex>"
echo "    (Phase 2; substance-binding verified against commit's actual tree)."
echo "Did NOT check (gap; follow-up work tracked):"
echo "  - Whether the round was created AFTER the branch's first commit"
echo "    (temporal precedence; prevents stamping stale rounds onto new work)."
echo "  - Whether the round contains user-CONFIRMS and external-AI-CONFIRMS."
echo "  - When REQUIRE_TREE_HASH is unset, legacy trailers without tree-hash"
echo "    pass with a deprecation warning (transition window)."
echo ""
echo "Phase 2 substance-bound: ${SUBSTANCE_BOUND_COUNT}; legacy trailers: ${LEGACY_TRAILER_COUNT}."
echo "(Per knowledge a7193bf6-1e9d-4f04-ad37-706860b80b20.)"
echo ""

if [ -n "$BLOCKED_COMMITS" ]; then
    echo "=== Multi-Party-Review Gate (server-side, point-in-time) ==="
    echo "BLOCKED. Commits modifying guardrail files failed the trailer check:"
    for c in $BLOCKED_COMMITS; do
        echo "  $c"
    done
    echo ""
    echo "Every commit that modifies a file in scripts/guardrail_files.txt"
    echo "AS IT WAS at that commit must carry an 'External-Review: <id>'"
    echo "trailer. For substance-binding, add tree-hash:<40-hex> after the"
    echo "round-id; the gate verifies it matches the commit's actual tree."
    exit 1
fi

echo "All guardrail-modifying commits in this range carry a valid External-Review trailer."
