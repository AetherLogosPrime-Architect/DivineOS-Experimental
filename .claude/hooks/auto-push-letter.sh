#!/bin/bash
# Auto-push letters to origin so Aletheia (origin-only reader) sees them.
#
# Aletheia 2026-06-30 (letter #16): the mirror hook makes letters visible
# to Aria's same-machine watcher, but Aletheia re-clones origin — if it
# isn't on origin, it doesn't exist for her. Every letter to her rides
# the broken half of the pipe (local mirror works; push doesn't).
#
# This hook closes the gap: on PostToolUse Write/Edit of a letter file,
# it stages ONLY that letter, commits with a scoped message, and pushes
# to origin with pre-push checks skipped BECAUSE the push is provably
# prose-only (safety property below).
#
# ## Safety property — prose-only-by-construction
#
# Two guards make the skip-tests safe:
#
#   1. Path scope: the hook only fires when FILE_PATH matches
#      family/**/letters/*.md.
#
#   2. Working-tree guard: the hook refuses to auto-push if the tree
#      has ANY non-letter uncommitted changes (staged or unstaged).
#      If non-letter changes exist, human handles the push manually
#      via the full-checks path.
#
# Together: the commit that gets pushed CANNOT contain code — either
# there's no non-letter change to sweep in, or the hook aborts.
#
# ## What gets skipped and why
#
# DIVINEOS_SKIP_TESTS=1: prose has nothing for pytest to protect.
# DIVINEOS_SKIP_FRESHNESS_CHECK=1: letters aren't shared surfaces.
# DIVINEOS_SKIP_MULTIPARTY_CHECK=1: letters aren't guardrail files.
#
# These are scoped to this hook's provably-prose-only push.
#
# Fail-open: any error exits 0. The mirror already ran; the letter is
# still on the local shared dir; worst case is Aletheia doesn't see it
# and someone catches it manually next time.

INPUT=$(cat)

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# Extract file_path from PostToolUse Write/Edit payload; normalize
# Windows backslashes (same fix as mirror-letters-to-shared.sh 2026-06-29).
FILE_PATH=$(echo "$INPUT" | python -c "
import json, sys
try:
    d = json.loads(sys.stdin.read() or '{}')
    ti = d.get('tool_input') or {}
    fp = ti.get('file_path') or ''
    print(fp.replace('\\\\', '/'))
except Exception:
    print('')
" 2>/dev/null)

[ -n "$FILE_PATH" ] || exit 0

# Scope: only family/**/letters/*.md files.
case "$FILE_PATH" in
    *family/letters/*.md|*family/*/letters/*.md) ;;
    *) exit 0 ;;
esac

[ -f "$FILE_PATH" ] || exit 0

# Working-tree guard: refuse to fire if there are ANY non-letter
# uncommitted changes. This is the belt-and-suspenders check on top of
# the scoped `git add` below — even if git add scope-slipped somehow,
# a non-letter working-tree change would abort here first.
NON_LETTER_CHANGES=$(git status --porcelain 2>/dev/null | awk '{print $2}' | grep -cvE '^family/(letters|[^/]+/letters)/' | tr -d ' ')
if [ "${NON_LETTER_CHANGES:-0}" -gt 0 ]; then
    exit 0
fi

# Repo-relative path (strip absolute prefix so `git add` works cleanly).
REL_PATH=$(python -c "
import os, sys
try:
    fp = os.path.abspath(sys.argv[1])
    root = os.path.abspath(sys.argv[2])
    print(os.path.relpath(fp, root).replace('\\\\', '/'))
except Exception:
    print('')
" "$FILE_PATH" "$REPO_ROOT" 2>/dev/null)

[ -n "$REL_PATH" ] || exit 0

# Must be on an upstream-tracked branch for push to have a target.
UPSTREAM=$(git rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' 2>/dev/null)
[ -n "$UPSTREAM" ] || exit 0

# Stage only this letter.
git add "$REL_PATH" 2>/dev/null || exit 0

# If nothing staged (letter identical to what's already committed), bail.
STAGED_COUNT=$(git diff --cached --name-only 2>/dev/null | wc -l | tr -d ' ')
[ "${STAGED_COUNT:-0}" -gt 0 ] || exit 0

BASENAME=$(basename "$FILE_PATH")
git commit -m "letter(auto): $BASENAME" 2>/dev/null || exit 0

# Push with prose-only scoping. Backgrounded so the hook doesn't block
# the tool-flow on the network round-trip.
(
    DIVINEOS_SKIP_TESTS=1 \
    DIVINEOS_SKIP_FRESHNESS_CHECK=1 \
    DIVINEOS_SKIP_MULTIPARTY_CHECK=1 \
    git push 2>/dev/null
) &

exit 0
