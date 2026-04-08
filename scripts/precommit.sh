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

if [ -z "$STAGED_PY" ]; then
    echo "No Python files staged."
    exit 0
fi

ERRORS=0

# 1. Auto-format (fix, don't just report)
echo "=== Format ==="
echo "$STAGED_PY" | xargs ruff format 2>/dev/null
echo "  Formatted. Re-staging..."
echo "$STAGED_PY" | xargs git add

# 2. Lint
echo "=== Lint ==="
if ! echo "$STAGED_PY" | xargs ruff check 2>/dev/null; then
    ERRORS=$((ERRORS + 1))
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

# 6. Vulture
if [ -n "$STAGED_SRC" ] && command -v vulture &>/dev/null; then
    echo "=== Vulture ==="
    # shellcheck disable=SC2086
    if ! vulture $STAGED_SRC scripts/vulture_whitelist.py --min-confidence 70 2>/dev/null; then
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
