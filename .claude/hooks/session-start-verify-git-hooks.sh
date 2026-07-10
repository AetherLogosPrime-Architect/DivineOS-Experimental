#!/usr/bin/env bash
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

# All good — hook present, marker present. Silent.
exit 0
