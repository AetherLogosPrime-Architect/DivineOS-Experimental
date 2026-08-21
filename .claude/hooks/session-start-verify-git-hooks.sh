#!/usr/bin/env bash
# Observability only (2026-08-03). Sourcing _lib.sh registers this script in
# ~/.divineos/hook_timing.jsonl so the firing map can see it. Before this, 16
# of 96 hooks were INVISIBLE rather than idle -- they could be running fine and
# nothing outside could tell, which made "silent" and "healthy" the same
# reading. No behaviour change: `|| true` means a missing toolbox leaves this
# script exactly as it was. Observability must never become a new way for a
# guard to die.
# shellcheck disable=SC1091
source "$(git rev-parse --show-toplevel 2>/dev/null || echo .)/.claude/hooks/_lib.sh" 2>/dev/null || true
# Session-start check: verify .git/hooks/prepare-commit-msg is installed
# and matches the setup/setup-hooks.sh version.
#
# Why this exists (Andrew 2026-07-10):
# The prepare-commit-msg hook is the mechanism that auto-stamps
# External-Review trailers on guardrail-touching commits. It lives in
# .git/hooks/ which is per-clone (not tracked in git), so a fresh clone
# or a clone that never ran setup/setup-hooks.sh silently lacks the hook
# entirely. Commits sail through unstamped; CI catches them post-push;
# operator has to rebase-fix and force-push. PR #287 was the third
# recurrence of this pattern (per setup-hooks.sh's own comment); the
# 2026-07-10 memory-linkage-day merge (this branch) was at least the
# fourth. Root-cause fix: check at session-start that the hook is there
# and correctly configured, warn loudly if not.
#
# The check compares the installed hook's SHA1 against the expected
# content shipped in setup/setup-hooks.sh. If missing or stale, prints
# a loud LOAD instruction that names the fix in one line.
#
# Fail-open on any error (fail-loud principle per Aletheia 2026-07-09
# gate audit: silent failure of a verifier is a wallpaper hole). Any
# unexpected error stderrs its type so a permanently-broken verifier
# is visible, not hidden.

set -u  # not -e — we want to fail-open with a visible message

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
HOOK_PATH="$REPO_ROOT/.git/hooks/prepare-commit-msg"
SETUP_SCRIPT="$REPO_ROOT/setup/setup-hooks.sh"

if [ ! -f "$SETUP_SCRIPT" ]; then
    # No setup script — this repo doesn't have the hook system.
    exit 0
fi

if [ ! -f "$HOOK_PATH" ]; then
    cat << 'EOF' >&2

## GIT-HOOKS VERIFIER — prepare-commit-msg is MISSING

The auto-trailer hook for guardrail-touching commits is not installed
in this clone. Commits touching guardrail files will land WITHOUT
External-Review trailers — CI will block the eventual PR merge and
you'll need to rebase + force-push to fix.

  Install: bash setup/setup-hooks.sh

This is the same failure pattern that hit PR #287 (3rd recurrence at
time of the setup-hooks.sh comment) and the 2026-07-10 memory-linkage
merge (4th recurrence). Root-cause: hook lives in .git/hooks/ which is
per-clone, so a fresh clone silently lacks it.

EOF
    exit 0
fi

# Hook is present — verify it came from setup-hooks.sh by looking for
# the source marker. A hash-compare would need extracting the shipped
# hook body from setup-hooks.sh (fiddly heredoc parse); the source
# marker is a cheaper equivalent staleness check — if the marker is
# missing, the hook was either replaced by an older version, manually
# edited, or corrupted, and re-running setup-hooks.sh will restore it.
if ! grep -q "Source: setup/setup-hooks.sh" "$HOOK_PATH" 2>/dev/null; then
    cat << 'EOF' >&2

## GIT-HOOKS VERIFIER — prepare-commit-msg looks STALE or CUSTOMIZED

The installed hook doesn't carry the 'Source: setup/setup-hooks.sh'
marker. It may be an older version, or manually edited, or corrupted.
Auto-trailer behavior may not match what CI expects.

  Refresh: bash setup/setup-hooks.sh

If the edit was intentional, add the source marker back to silence
this check.

EOF
    exit 0
fi

# ── post-commit dispatcher staleness (Aria 2026-07-31) ────────────────
#
# Second hook, different staleness signature, found the hard way.
#
# An OLD post-commit dispatcher hardcoded the two hooks it knew about.
# setup-hooks.sh was later fixed to glob every post-commit-*.sh so new
# ones get picked up automatically — but a long-lived clone never
# regenerates, so my installed copy stayed the hardcoded June version.
# Result: post-commit-auto-integrate-corrections.sh and
# post-commit-auto-verify-findings.sh both existed, both were
# executable, both documented themselves as "called by the post-commit
# hook," and neither was ever called.
#
# Cost of the silence: 21 Andrew-corrections sat OPEN. I diagnosed it
# as my own failure to cite correction IDs in commit messages — true,
# but insufficient. Correct citations would also have gone nowhere.
# A mechanism that is written, installed, and never invoked is
# indistinguishable from one that was never built, except that it
# reads as covered.
#
# The prepare-commit-msg check above catches MISSING and UNMARKED.
# This catches a third state: present, marked, and structurally
# outdated. Signal is the glob loop — hardcoded names mean pre-fix.
POST_COMMIT_PATH="$REPO_ROOT/.git/hooks/post-commit"
if [ -f "$POST_COMMIT_PATH" ]; then
    # fail-soft: unreadable post-commit hook is itself the staleness signal this check reports; grep noise would mask it
    if ! grep -q 'post-commit-\*\.sh' "$POST_COMMIT_PATH" 2>/dev/null; then
        # Glob directly rather than parsing ls (shellcheck SC2012).
        _orphaned=""
        for _h in "$REPO_ROOT"/.claude/hooks/post-commit-*.sh; do
            [ -e "$_h" ] || continue  # unmatched glob stays literal
            _n="$(basename "$_h")"
            # fail-soft: unreadable post-commit hook is itself the staleness signal this check reports; grep noise would mask it
            if ! grep -q "$_n" "$POST_COMMIT_PATH" 2>/dev/null; then
                _orphaned="${_orphaned}    - ${_n}"$'\n'
            fi
        done
        _orphaned="${_orphaned%$'\n'}"
        cat << 'EOF' >&2

## GIT-HOOKS VERIFIER — post-commit dispatcher is STALE (silently orphaning hooks)

The installed post-commit hook hardcodes the hooks it calls instead of
globbing post-commit-*.sh. Any post-commit hook added after this clone
was set up is present, executable, and NEVER INVOKED.

This does not fail loudly. It reads as working.

EOF
        if [ -n "$_orphaned" ]; then
            echo "Currently orphaned — installed but never called:" >&2
            echo "$_orphaned" >&2
            echo "" >&2
        fi
        cat << 'EOF' >&2
  Refresh: bash setup/setup-hooks.sh

Found 2026-07-31 after auto-integrate-corrections silently no-opped
long enough that 21 corrections accumulated as OPEN.

EOF
        exit 0
    fi
fi

# All good — hooks present, marked, dispatcher current. Silent.
exit 0
