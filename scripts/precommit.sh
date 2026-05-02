#!/bin/bash
# Pre-commit preflight — run this BEFORE `git commit` to fix everything in one pass.
# Usage: bash scripts/precommit.sh
#
# What it does:
#   1. Auto-formats staged files (ruff format)
#   2. Reports lint errors (ruff check)
#   3. Reports type errors (mypy)
#   4. Reports doc drift (test/command counts)
#   5. Reports vulture dead code
#   6. Re-stages auto-fixed files
#
# After this passes, `git commit` will succeed on first try.

set -e

STAGED_PY=$(git diff --cached --name-only --diff-filter=ACM | grep '\.py$' || true)
STAGED_SH=$(git diff --cached --name-only --diff-filter=ACM | grep '\.sh$' || true)

if [ -z "$STAGED_PY" ] && [ -z "$STAGED_SH" ]; then
    echo "No Python or shell files staged."
    exit 0
fi

ERRORS=0

# 0. Line-ending normalization for shell scripts.
# Windows editors write CRLF by default. .gitattributes specifies LF for .sh
# but that only applies at commit-write time; the working copy still has CRLF
# while shellcheck runs. Normalize staged .sh files to LF before any check
# sees them. This eliminates the "dos2unix then re-stage" dance.
if [ -n "$STAGED_SH" ]; then
    echo "=== Normalize .sh line endings ==="
    if command -v dos2unix &>/dev/null; then
        echo "$STAGED_SH" | xargs dos2unix 2>&1 | grep -v "converting" || true
    else
        # Fallback: sed strips \r. Works even without dos2unix.
        while IFS= read -r f; do
            [ -f "$f" ] && sed -i 's/\r$//' "$f"
        done <<< "$STAGED_SH"
    fi
    echo "$STAGED_SH" | xargs git add
    echo "  Normalized and re-staged."
fi

# 1. Auto-format (fix, don't just report)
if [ -n "$STAGED_PY" ]; then
    echo "=== Format ==="
    echo "$STAGED_PY" | xargs ruff format 2>/dev/null
    echo "  Formatted. Re-staging..."
    echo "$STAGED_PY" | xargs git add
fi

# 2. Lint
if [ -n "$STAGED_PY" ]; then
    echo "=== Lint ==="
    if ! echo "$STAGED_PY" | xargs ruff check 2>/dev/null; then
        ERRORS=$((ERRORS + 1))
    fi
fi

# 3. Mypy (src only)
STAGED_SRC=$(echo "$STAGED_PY" | grep '^src/' || true)
if [ -n "$STAGED_SRC" ]; then
    echo "=== Mypy ==="
    if ! echo "$STAGED_SRC" | xargs mypy --ignore-missing-imports 2>/dev/null; then
        ERRORS=$((ERRORS + 1))
    fi
fi

# 4. Doc drift (auto-fix test counts, then re-stage and verify)
echo "=== Doc Drift ==="
python scripts/check_doc_counts.py --fix 2>/dev/null || true
git add CLAUDE.md README.md src/divineos/seed.json 2>/dev/null || true
if ! python scripts/check_doc_counts.py 2>/dev/null; then
    ERRORS=$((ERRORS + 1))
fi

# 5. Broad exceptions
echo "=== Broad Exceptions ==="
if ! python scripts/check_broad_exceptions.py 2>/dev/null; then
    ERRORS=$((ERRORS + 1))
fi

# 5b. Pre-reg gate (un-gameable): new mechanisms require a filed pre-reg.
# The gate reads the staged diff and blocks when a new mechanism lacks a
# matching OPEN pre-registration in the ledger. Discipline from the
# gute_bridge docstring made binding. See scripts/check_preregs.py.
echo "=== Pre-reg Gate ==="
if ! python scripts/check_preregs.py; then
    ERRORS=$((ERRORS + 1))
fi

# 5c. Multi-party-review warning. The actual gate runs at commit-msg time
# (see .git/hooks/commit-msg installed by setup/setup-hooks.sh). This is
# an early warning so the operator sees the requirement BEFORE typing
# the commit message. Non-blocking — it only surfaces information.
if [ -f scripts/guardrail_files.txt ] && [ -f scripts/check_multi_party_review.py ]; then
    echo "=== Multi-Party-Review Check ==="
    # Read guardrail list (skip comments + blanks) once, then match.
    # Avoid `set -e` killing the subshell on grep-non-match.
    GUARDRAIL_LIST=$(grep -v '^\s*#' scripts/guardrail_files.txt | grep -v '^\s*$' || true)
    STAGED_GUARDRAILS=$(git diff --cached --name-only | while read -r f; do
        if echo "$GUARDRAIL_LIST" | grep -Fxq "$f"; then
            echo "$f"
        fi
    done || true)
    if [ -n "$STAGED_GUARDRAILS" ]; then
        echo "  [!] Guardrail files in this commit:"
        while IFS= read -r line; do
            [ -n "$line" ] && echo "      $line"
        done <<< "$STAGED_GUARDRAILS"
        DIFF_HASH=$(git diff --cached --unified=3 | sha256sum | cut -c1-64)
        echo ""
        echo "  Before committing, file a Watchmen audit round with:"
        echo "      - CONFIRMS from actor=user"
        echo "      - CONFIRMS from actor=grok | gemini | claude-<variant>"
        echo "      - round focus/notes contain: 'diff-hash: $DIFF_HASH'"
        echo "  Then add to the commit message:"
        echo "      External-Review: <round_id>"
        echo ""
        echo "  The commit-msg hook will block the commit if any piece is missing."
        echo ""

        # Gate-self-test (claim cf05b878, 2026-04-25): the commit-msg
        # hook is what enforces the hash binding. If it isn't installed,
        # the gate is theater — operator-discipline only. Discovered live
        # 2026-04-25 when both that day's External-Review rounds landed
        # without the hook running. Worktree-incompatibility in
        # setup-hooks.sh silently no-op'd the install. Verify here that
        # the hook actually exists and is non-empty BEFORE the operator
        # types the commit message — the operator should see this loudly.
        HOOK_PATH=$(git rev-parse --git-path hooks/commit-msg 2>/dev/null || echo ".git/hooks/commit-msg")
        if [ ! -s "$HOOK_PATH" ]; then
            echo "  [!!] COMMIT-MSG HOOK NOT INSTALLED — gate enforcement absent."
            echo "       Path checked: $HOOK_PATH"
            echo "       Without this hook, the External-Review trailer is"
            echo "       NOT validated at commit time. The hash binding"
            echo "       between the filed round and the landed commit is"
            echo "       operator-discipline only, not structurally enforced."
            echo "       Install: bash setup/setup-hooks.sh (note: has a"
            echo "       worktree-compatibility bug — verify the hook"
            echo "       actually appears at the path above after running,"
            echo "       or write it manually)."
            echo ""
            ERRORS=$((ERRORS + 1))
        fi
    fi
fi

# 6. Vulture
if [ -n "$STAGED_SRC" ] && command -v vulture &>/dev/null; then
    echo "=== Vulture ==="
    # shellcheck disable=SC2086
    if ! vulture $STAGED_SRC scripts/vulture_whitelist.py --min-confidence 70 2>/dev/null; then
        ERRORS=$((ERRORS + 1))
    fi
fi

# 7. Shellcheck on staged .sh files (line endings already normalized in step 0)
if [ -n "$STAGED_SH" ] && command -v shellcheck &>/dev/null; then
    echo "=== Shellcheck ==="
    if ! echo "$STAGED_SH" | xargs shellcheck 2>/dev/null; then
        ERRORS=$((ERRORS + 1))
    fi
fi

echo ""
if [ $ERRORS -eq 0 ]; then
    echo "All clear. git commit will succeed."
else
    echo "$ERRORS check(s) failed. Fix them, then git commit."
fi
exit $ERRORS
