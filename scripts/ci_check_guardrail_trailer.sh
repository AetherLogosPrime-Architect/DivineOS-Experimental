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
#   REQUIRE_TREE_HASH=0 — allow legacy trailers with no tree-hash field.
#     ESCAPE HATCH ONLY. See the default flip below.
#
# 2026-08-01: DEFAULT FLIPPED 0 -> 1.
#
# The transition window opened 2026-06-13 "until tooling emits tree-hash"
# and then stayed open. Nothing ever set the variable — measured: it
# appears nowhere outside this script's own default and one test
# monkeypatch. So the entire Phase-2 substance binding was opt-in with
# no opt-in, and a stale round-id laminated onto unrelated guardrail
# code passed CI green.
#
# Two things made now the moment. The tooling condition is met:
# `divineos audit prepare-merge` and the per-commit trailer path both
# emit tree-hash, and PR #404's three guardrail commits reported
# "Phase 2 substance-bound: 3; legacy trailers: 0". And the companion
# change in check_multi_party_review.py deletes the 7-day recency window
# on the grounds that content-binding answers the same question exactly
# — which is only true if every trailer HAS a binding. Flipping this
# default is what makes that deletion safe rather than a hole.
#
# Exit code: 0 on pass, 1 on any blocked commit.

set -eu

PR_BASE="${1:-}"
PR_HEAD="${2:-}"
REQUIRE_TREE_HASH="${REQUIRE_TREE_HASH:-1}"

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

# Parse the External-Review trailer line(s) out of a commit message.
# Returns ALL trailer lines, one per line, or empty if none present.
#
# 2026-08-01: this used to end in `head -1`. That single word is the bug
# Andrew hit on every squash-merge, and it finally reproduced end to end
# on main at be48c290.
#
# GitHub builds a squash commit's message by CONCATENATING the messages
# of every commit in the branch. PR #404 had three guardrail commits,
# each correctly stamped with its own tree-hash, so the squash inherited
# three External-Review trailers. The gate read the first, which carries
# the FIRST commit's tree — an intermediate state that by definition is
# never the squashed result — and blocked:
#
#   trailer says: tree-hash:c92d23f4...   (first commit's tree)
#   actual tree:  tree-hash:5d470c1a...   (the squash's tree)
#
# The decisive detail: the CORRECT trailer sat in the same message
# further down, carrying exactly 5d470c1a — because the last stamped
# commit's tree IS the branch tip tree, and the branch tip tree IS the
# squash tree. The gate held the right answer and stopped reading before
# it got there.
#
# The rule is now: a commit passes if ANY of its trailers binds to its
# actual tree. This is NOT a weakening. A commit still fails unless some
# trailer's tree-hash equals the real tree, and that equality cannot be
# manufactured without producing the tree. What it removes is an
# arbitrary first-match cutoff that every legitimate multi-commit
# guardrail merge trips.
#
# Named for the reader: the alternative was to strip inherited trailers
# from the squash body via a generated block. Rejected — that makes
# every merge depend on a human remembering a manual paste, which is the
# shape that produced this bug in the first place.
parse_trailer_lines() {
    echo "$1" | grep -iE '^External-Review:[[:space:]]*\S+' || true
}

# Extract every tree-hash present across the given trailer lines.
# Returns 40-hex hashes, one per line, or empty if none carry one.
parse_trailer_tree_hashes() {
    echo "$1" | grep -oE 'tree-hash:[a-f0-9]{40}' | sed 's/tree-hash://' || true
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
    TRAILER=$(parse_trailer_lines "$MSG")

    if [ -z "$TRAILER" ]; then
        BLOCKED_COMMITS="$BLOCKED_COMMITS $commit"
        echo "[BLOCKED] $commit modifies guardrail file(s); no External-Review trailer."
        continue
    fi

    # Trailer(s) present. Now check substance-binding via tree-hash.
    TRAILER_TREE_HASH=$(parse_trailer_tree_hashes "$TRAILER")

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

    # Pass if ANY trailer binds to the actual tree. A squash-merge
    # legitimately carries one trailer per squashed commit, each bound to
    # its own intermediate tree; exactly one -- the branch tip's -- matches
    # the squash result. Requiring the FIRST to match blocked every
    # multi-commit guardrail merge. See parse_trailer_lines above.
    if echo "$TRAILER_TREE_HASH" | grep -qxF "$ACTUAL_TREE_HASH"; then
        SUBSTANCE_BOUND_COUNT=$((SUBSTANCE_BOUND_COUNT + 1))
        TRAILER_COUNT=$(echo "$TRAILER_TREE_HASH" | grep -c .)
        if [ "$TRAILER_COUNT" -gt 1 ]; then
            echo "[ok] $commit trailer present + tree-hash binding verified (1 of $TRAILER_COUNT trailers matched -- squash-merge shape)."
        else
            echo "[ok] $commit trailer present + tree-hash binding verified."
        fi
    else
        BLOCKED_COMMITS="$BLOCKED_COMMITS $commit"
        echo "[BLOCKED] $commit: no trailer tree-hash matches the commit's actual tree."
        echo "    commit's actual tree-hash: $ACTUAL_TREE_HASH"
        echo "    trailer tree-hash(es) offered:"
        echo "$TRAILER_TREE_HASH" | sed 's/^/      /'
        echo "    -> every round was filed against a different tree; cannot authorize."
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
