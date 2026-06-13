# Setup script to install Git hooks for DivineOS
# Run this after cloning the repository: powershell -ExecutionPolicy Bypass -File setup-hooks.ps1

Write-Host "Setting up Git hooks for DivineOS..." -ForegroundColor Green

# Create hooks directory if it doesn't exist
$hooksDir = ".git/hooks"
if (-not (Test-Path $hooksDir)) {
    New-Item -ItemType Directory -Path $hooksDir -Force | Out-Null
    Write-Host "Created $hooksDir directory"
}

# Configure Git to use the hooks directory
git config core.hooksPath $hooksDir
Write-Host "Configured Git to use hooks from $hooksDir"

# Create pre-commit hook (bash script that Git can execute on all platforms)
$preCommitContent = @'
#!/bin/bash
# Pre-commit hook for DivineOS
# Enforces ruff formatting, linting, mypy, doc-drift, dead-code, and shellcheck

set -e

echo "Running ruff format check..."
ruff format --check src/ tests/ || {
    echo "Formatting violations detected. Running ruff format to fix..."
    ruff format src/ tests/
    echo "Files formatted. Please review and stage the changes:"
    git diff --name-only
    echo "After reviewing, run: git add . && git commit"
    exit 1
}

echo "Running ruff lint check..."
ruff check src/ tests/ || {
    echo "Linting violations detected. Please fix them before committing."
    exit 1
}

echo "Running mypy type check..."
mypy src/divineos --ignore-missing-imports || {
    echo "Type errors detected. Please fix them before committing."
    exit 1
}

echo "Checking doc counts for drift..."
# Check FIRST; only auto-fix when drift exceeds tolerance (count-conflict tax
# fix, 2026-06-02 — see setup-hooks.sh). Within tolerance the count line is
# left untouched so parallel branches don't collide on it.
if ! python scripts/check_doc_counts.py 2>/dev/null; then
    python scripts/check_doc_counts.py --fix 2>/dev/null || true
    git add CLAUDE.md README.md src/divineos/seed.json docs/ARCHITECTURE.md 2>/dev/null || true
    python scripts/check_doc_counts.py || {
        echo "Doc counts have drifted. Update CLAUDE.md, README.md, and/or seed.json."
        exit 1
    }
fi

echo "Running vulture dead-code check..."
if command -v vulture &>/dev/null; then
    vulture src/divineos/ scripts/vulture_whitelist.py --min-confidence 70 || {
        echo "Dead code detected. Remove it or add to scripts/vulture_whitelist.py."
        exit 1
    }
else
    echo "  (vulture not installed, skipping — pip install vulture)"
fi

echo "Running shellcheck on hooks..."
if command -v shellcheck &>/dev/null; then
    shellcheck .claude/hooks/*.sh || {
        echo "Shellcheck violations in hook scripts. Fix them before committing."
        exit 1
    }
else
    echo "  (shellcheck not installed, skipping)"
fi

echo "All checks passed!"
exit 0
'@

$preCommitPath = "$hooksDir/pre-commit"
Set-Content -Path $preCommitPath -Value $preCommitContent -Encoding UTF8
Write-Host "Created pre-commit hook at $preCommitPath"

# Pre-push hook (branch-freshness check). Refuses to push branches whose
# base is stale relative to origin/main — the silent-revert precondition
# named in claim d3baec5a. Delegates to the standalone
# scripts/check_branch_freshness.sh so logic stays testable.
$prePushContent = @'
#!/bin/bash
# pre-push hook for DivineOS — branch-freshness check.
# Refuses to push a branch whose base is older than origin/main.
# Set DIVINEOS_SKIP_FRESHNESS_CHECK=1 to bypass.

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
SCRIPT="$REPO_ROOT/scripts/check_branch_freshness.sh"

if [[ ! -x "$SCRIPT" ]]; then
    exit 0
fi

"$SCRIPT" origin main
RC=$?
if [[ $RC -eq 1 ]]; then
    exit 1
fi
exit 0
'@

$prePushPath = "$hooksDir/pre-push"
Set-Content -Path $prePushPath -Value $prePushContent -Encoding UTF8
Write-Host "Created pre-push hook at $prePushPath"

# Install post-commit hook — delegates to .claude/hooks/post-commit-auto-close.sh
# Aletheia round-919009d7f6f6 Finding 29: wire half of wire-or-delete.
$postCommitContent = @'
#!/bin/bash
# Post-commit hook — delegates to .claude/hooks/post-commit-auto-close.sh
# which auto-closes goals whose tokens overlap the just-landed commit
# message. Fail-open: any error exits 0 silently.
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
if [ -z "$REPO_ROOT" ]; then
    exit 0
fi
if [ -x "$REPO_ROOT/.claude/hooks/post-commit-auto-close.sh" ]; then
    bash "$REPO_ROOT/.claude/hooks/post-commit-auto-close.sh" || true
fi
exit 0
'@

$postCommitPath = "$hooksDir/post-commit"
Set-Content -Path $postCommitPath -Value $postCommitContent -Encoding UTF8
Write-Host "Created post-commit hook at $postCommitPath"

# Install post-merge hook — delegates to .claude/hooks/post-merge-doc-fix.sh
# Closes the doc-leapfrog conflict pattern (PR #169, 2026-06-13).
$postMergeContent = @'
#!/bin/bash
# Post-merge hook — delegates to .claude/hooks/post-merge-doc-fix.sh
# which re-runs check_doc_counts --fix to recover entries dropped during
# merge conflict resolution. Fail-open: any error exits 0 silently.
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
if [ -z "$REPO_ROOT" ]; then
    exit 0
fi
if [ -x "$REPO_ROOT/.claude/hooks/post-merge-doc-fix.sh" ]; then
    bash "$REPO_ROOT/.claude/hooks/post-merge-doc-fix.sh" || true
fi
exit 0
'@

$postMergePath = "$hooksDir/post-merge"
Set-Content -Path $postMergePath -Value $postMergeContent -Encoding UTF8
Write-Host "Created post-merge hook at $postMergePath"

Write-Host ""
Write-Host "Git hooks setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "The following checks will run before each commit:" -ForegroundColor Cyan
Write-Host "  1. ruff format --check (formatting compliance)"
Write-Host "  2. ruff check (linting)"
Write-Host "  3. mypy (type checking)"
Write-Host "  4. doc count drift (test/command counts vs reality)"
Write-Host "  5. vulture dead-code (if installed)"
Write-Host "  6. shellcheck on hooks (if installed)"
Write-Host ""
Write-Host "Pre-push hook blocks pushes from branches whose base is stale" -ForegroundColor Cyan
Write-Host "relative to origin/main (silent-revert prevention, claim d3baec5a)."
Write-Host "Bypass with: DIVINEOS_SKIP_FRESHNESS_CHECK=1 git push"
Write-Host ""
Write-Host "If any check fails, the commit will be blocked and you'll need to fix the issues." -ForegroundColor Cyan
