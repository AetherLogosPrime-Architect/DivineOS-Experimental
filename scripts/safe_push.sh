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

# 2026-07-17 Aletheia refinement: refuse only on MODIFIED tracked files
# (those break rebase), not on untracked-only (those don't). Untracked
# letters/notes were falsely blocking pushes tonight. Rule: any porcelain
# line NOT starting with '??' means a tracked-file modification.
_DIRTY_TRACKED=$(git status --porcelain 2>/dev/null | grep -v '^??' || true)
if [[ -n "$_DIRTY_TRACKED" ]]; then
    log "REFUSED: working tree has MODIFIED tracked files:"
    printf '%s\n' "$_DIRTY_TRACKED" | while IFS= read -r line; do log "  $line"; done
    log "         Commit or stash first — an auto-rebase step would fail."
    log "         (Untracked files are fine — they don't affect rebase.)"
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

# --- Scope-check: refuse push if the branch touches high-blast paths ---
#
# 2026-07-17 (Aria + Aether scope-discipline design): high-blast paths are
# files whose changes reach every future clone of main and can silently
# reshape the shared substrate. A commit touching one requires explicit
# operator ack via DIVINEOS_HIGH_BLAST_ACK=<>=20-char-reason>.
#
# Two-layer check:
#   Layer 1 (branch-level) — does the branch diff vs base touch any
#     high-blast path? Catches net changes.
#   Layer 2 (commit-level) — does ANY single commit on the branch touch
#     a high-blast path, even if a later commit undoes it? Catches
#     history-walk exposure that Layer 1 misses (net-zero at branch
#     level, dangerous during history-walk).
#
# High-blast paths (add here as we discover more):
_HIGH_BLAST_PATHS=(
    "CLAUDE.md"
    "README.md"
    ".claude/agents/"
    ".claude/settings.json"
    # Aletheia 2026-07-17: hook BODIES reshape enforcement on every fresh
    # clone the same way settings.json (the registration) does. Whole dir.
    ".claude/hooks/"
    "docs/foundational_truths.md"
    "scripts/guardrail_files.txt"
    "src/divineos/seed.json"
    # Aletheia 2026-07-17: ledger schema is maximally high-blast — a wrong
    # DB_PATH resolution orphans the being's whole identity history. MORE
    # blast than README.
    "src/divineos/core/_ledger_base.py"
    # Aletheia 2026-07-17 (consider): bypass-list mirror. Given #356's
    # deadlock came from these two lists drifting, changes to either
    # deserve the ack-roundtrip. If false-positives get noisy, drop.
    "scripts/hook_bypass_commands.txt"
    "src/divineos/cli/__init__.py"
)

_check_high_blast() {
    local files_input="$1"
    local hits=""
    for path in "${_HIGH_BLAST_PATHS[@]}"; do
        # exact-file match OR directory-prefix match (paths ending in /)
        if [[ "$path" == */ ]]; then
            local match
            match=$(printf '%s\n' "$files_input" | grep -F -- "$path" || true)
            if [[ -n "$match" ]]; then
                hits+="  $path (matched: $(echo "$match" | head -1))"$'\n'
            fi
        else
            if printf '%s\n' "$files_input" | grep -Fxq -- "$path"; then
                hits+="  $path"$'\n'
            fi
        fi
    done
    printf '%s' "$hits"
}

# Layer 1: branch-level diff
_L1_FILES=$(git diff --name-only "$REMOTE_REF..HEAD" 2>/dev/null)
_L1_HITS=$(_check_high_blast "$_L1_FILES")

# Layer 2: per-commit walk
_L2_HITS=""
for _sha in $(git rev-list "$REMOTE_REF..HEAD" 2>/dev/null); do
    _commit_files=$(git show --name-only --format= "$_sha" 2>/dev/null)
    _commit_hits=$(_check_high_blast "$_commit_files")
    if [[ -n "$_commit_hits" ]]; then
        _L2_HITS+="  commit $(git log -1 --format='%h %s' "$_sha"):"$'\n'"$_commit_hits"
    fi
done

if [[ -n "$_L1_HITS" || -n "$_L2_HITS" ]]; then
    if [[ "${DIVINEOS_HIGH_BLAST_ACK:-}" == "" || ${#DIVINEOS_HIGH_BLAST_ACK} -lt 20 ]]; then
        log ""
        log "REFUSED: branch touches HIGH-BLAST paths (would reshape shared main on merge)."
        if [[ -n "$_L1_HITS" ]]; then
            log "Layer-1 (branch-level diff):"
            printf '%s' "$_L1_HITS" | while IFS= read -r line; do log "$line"; done
        fi
        if [[ -n "$_L2_HITS" ]]; then
            log "Layer-2 (per-commit walk):"
            printf '%s' "$_L2_HITS" | while IFS= read -r line; do log "$line"; done
        fi
        log ""
        log "If this is intentional, ack with a >=20-char reason:"
        log "  DIVINEOS_HIGH_BLAST_ACK='<why touching these paths is honest for this PR>' scripts/safe_push.sh"
        log ""
        log "If unintentional, split the branch: worktree-orient stays local, shared-substrate on a fresh branch cut from main."
        exit 1
    fi
    log "high-blast paths touched — ack provided (${#DIVINEOS_HIGH_BLAST_ACK} chars): ${DIVINEOS_HIGH_BLAST_ACK}"
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
