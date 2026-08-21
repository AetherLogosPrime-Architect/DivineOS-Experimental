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

# Fall back to the pull request's own body when the commit message has no
# trailer.
#
# WHY THIS EXISTS, measured 2026-08-14. GitHub composes a squash-merge message
# when the merge dialog is OPENED and never refreshes it. The operator opened
# the dialog, two more commits landed on the branch, and the merge took the
# current head while keeping the stale message -- so the code merged and the
# trailer did not, and this gate went red on `main` over a message-snapshot
# race. That red cannot be cleaned without force-pushing `main`, declined as
# too risky, so the badge is permanent.
#
# The operator cannot fix that by being more careful. There is no click order
# that avoids it, and he had already said plainly: "i cant copy paste
# anything." A requirement whose only compliance path is a human pasting text
# into a web form at exactly the right instant is a trap, not a control.
#
# The PR body carries the same audit claim through a channel that cannot go
# stale: fetched live at check time, editable after the fact, and it is the
# artifact the operator actually reviews. A trailer on the commit still wins;
# this runs only when there is none.
#
# Fails toward the old behaviour: no gh, no token, no PR number, or any error
# leaves the result empty and the commit blocks exactly as before.
trailer_from_pr_body() {
    local subject="$1"
    local pr="${PR_NUMBER:-}"
    # On a pull_request event the workflow supplies PR_NUMBER directly.
    # Branch commits carry no "(#N)" in their subject -- only the squash
    # commit does -- so without this the fallback worked AFTER the merge and
    # not before it, which is the whole complaint: the check could never be
    # seen green in the place where seeing it still changes the outcome.
    if [ -z "$pr" ]; then
        pr=$(echo "$subject" | grep -oE '\(#[0-9]+\)$' | grep -oE '[0-9]+') || true
    fi
    [ -z "$pr" ] && return 0
    command -v gh >/dev/null 2>&1 || return 0
    gh pr view "$pr" --json body --jq .body 2>/dev/null \
        | grep -iE '^External-Review:[[:space:]]*\S+' | head -1 || true
}

# Extract the tree-hash field from a trailer line, if present.
# Returns the 40-hex hash or empty.
parse_trailer_tree_hash() {
    echo "$1" | grep -oE 'tree-hash:[a-f0-9]{40}' | head -1 | sed 's/tree-hash://'
}

# Self-disclosure footer: always emit what was checked AND what was not.
#
# A FUNCTION rather than a trailing block, since 2026-08-19. It used to sit at
# the bottom, which meant any early exit silently skipped it -- and the net-diff
# shortcut added below is exactly such an exit. Caught by
# test_self_disclosure_block_always_emitted, which asserts "always" and meant it.
# A check that passes without stating its own scope-limits is the shape this
# footer exists to prevent, so the footer must not be reachable only on one path.
emit_scope_disclosure() {
    echo ""
    echo "=== Multi-Party-Review Gate: scope of this check ==="
    echo "Checked:"
    echo "  - Whether the NET DIFF being merged lands any guardrail-listed file."
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
    echo "  - Anything about commits whose content is already on main; a branch"
    echo "    that lands no guardrail change is not inspected commit-by-commit."
    echo ""
    echo "Phase 2 substance-bound: ${SUBSTANCE_BOUND_COUNT}; legacy trailers: ${LEGACY_TRAILER_COUNT}."
    echo "(Per knowledge a7193bf6-1e9d-4f04-ad37-706860b80b20.)"
    echo ""
}

BLOCKED_COMMITS=""
SUBSTANCE_BOUND_COUNT=0
LEGACY_TRAILER_COUNT=0

# ─── WHAT LANDS IS WHAT NEEDS REVIEW ───────────────────────────────────────
#
# Andrew, 2026-08-13 and repeatedly since: "not every commit just every merge
# to main, committing is allowed in your own workspace without any audit, the
# github is the main vault/backup."
#
# That instruction was already quoted in integrity-audit.yml and the loop below
# still asked the other question. It walks the branch's HISTORY and blocks on
# any commit that ever touched a guardrail file. But this repo squash-merges:
# what reaches main is one commit whose content is the NET DIFF. A commit sitting
# in the branch's history that contributes nothing to that diff lands nothing,
# and demanding review for it is demanding review of content that is not being
# merged.
#
# MEASURED, PR #407 (2026-08-19). Blocked on 507dbfac, which changed
# scripts/check_push_readiness.sh on 2026-08-08. That file is guardrail-listed,
# so the walk was correct on its own terms -- but the file shows ZERO change in
# the PR's net diff, because main already carries that content under a different
# sha from an earlier squash-merge. The commit is not an ancestor of main
# (`git merge-base --is-ancestor` exits 1) while its content is already there.
# So split branches keep the original commits, main keeps squashed equivalents,
# and the walk finds un-trailered guardrail commits that no round can ever fix:
# adding a review would review something that is not landing. Unmeetable by
# construction, which is the same shape as the per-commit-trailer requirement
# that was removed on 2026-08-13 for being unmeetable after a force-push.
#
# So: evaluate the net diff first. If nothing guardrail-listed is actually
# landing, there is nothing to review and the check passes. If something IS
# landing, fall through to the existing walk unchanged -- every protection below
# still applies, including the tree-hash substance binding.
#
# This REMOVES NO COVERAGE. Guardrail content reaching main still requires the
# trailer. What it removes is the demand to re-review content already reviewed
# and already merged.
# NOT fail-soft. If the net diff cannot be computed, this must NOT reach the
# early exit -- an empty NET_FILES would read as "lands nothing guardrail-listed"
# and PASS, which is failing open on the one path that protects main. A bad ref
# would become a green check. So the failure is announced and the run falls
# through to the per-commit walk, which is the conservative answer.
NET_DIFF_OK=1
if ! NET_FILES=$(git diff --name-only "${PR_BASE}" "${PR_HEAD}" 2>&1); then
    echo "[warn] could not compute net diff ${PR_BASE}..${PR_HEAD}: ${NET_FILES}" >&2
    echo "[warn] falling through to the per-commit walk rather than passing." >&2
    NET_FILES=""
    NET_DIFF_OK=0
fi
HEAD_GUARDRAIL_LIST=$(load_guardrail_list_at "${PR_HEAD}")
NET_TOUCHES_GUARDRAIL=""
if [ -n "$HEAD_GUARDRAIL_LIST" ]; then
    while IFS= read -r file; do
        [ -z "$file" ] && continue
        while IFS= read -r guardrail_path; do
            [ -z "$guardrail_path" ] && continue
            if [ "$file" = "$guardrail_path" ]; then
                NET_TOUCHES_GUARDRAIL="$file"
                break
            fi
        done <<< "$HEAD_GUARDRAIL_LIST"
        [ -n "$NET_TOUCHES_GUARDRAIL" ] && break
    done <<< "$NET_FILES"
fi

if [ -z "$NET_TOUCHES_GUARDRAIL" ] && [ "$NET_DIFF_OK" = "1" ]; then
    echo "=== Multi-Party-Review Gate (server-side, point-in-time) ==="
    echo "PASS. The net diff ${PR_BASE}..${PR_HEAD} lands no guardrail-listed file."
    echo "Individual commits in this branch's history may have touched one, but"
    echo "what merges is the net diff, and review binds to what lands."
    emit_scope_disclosure
    exit 0
fi

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

    FROM_PR_BODY=""
    if [ -z "$TRAILER" ]; then
        TRAILER=$(trailer_from_pr_body "$(git log -1 --format=%s "$commit")")
        if [ -n "$TRAILER" ]; then
            FROM_PR_BODY="1"
            echo "[info] $commit: trailer absent from the commit message; read from the PR body instead."
        fi
    fi

    if [ -z "$TRAILER" ]; then
        BLOCKED_COMMITS="$BLOCKED_COMMITS $commit"
        echo "[BLOCKED] $commit modifies guardrail file(s); no External-Review trailer."
        continue
    fi

    # Trailer(s) present. Now check substance-binding via tree-hash.
    TRAILER_TREE_HASH=$(parse_trailer_tree_hashes "$TRAILER")

    # A tree-hash in a PR-BODY trailer describes the PULL REQUEST, not any one
    # commit inside it. Verifying it against an individual commit's tree is a
    # category error that fails 100% of the time on a multi-commit branch --
    # only the last commit could ever match, and not after main is merged in.
    #
    # Measured 2026-08-15 across the open stack: ten PRs carry a tree-hash
    # trailer in the body and ZERO of their branch commits carry one in the
    # message, so every one of them would have taken this path and been
    # blocked by a hash that was never a claim about them. The check would
    # have reported ten review failures and meant nothing by any of them.
    #
    # On this path the substance anchor is merge-review instead: the operator
    # approves the HEAD commit, and that approval is invalidated by any later
    # push. Say so in the output rather than implying a binding that was not
    # checked -- a gate that is honest about the limits of its own check is
    # the one an operator can trust the rest of the time.
    if [ -n "$FROM_PR_BODY" ] && [ -n "$TRAILER_TREE_HASH" ]; then
        echo "    [info] tree-hash in a PR-body trailer describes the PR, not this commit; not verified here."
        echo "    [info] substance anchor on this path is merge-review's operator approval of the head commit."
        TRAILER_TREE_HASH=""
    fi

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

emit_scope_disclosure

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
