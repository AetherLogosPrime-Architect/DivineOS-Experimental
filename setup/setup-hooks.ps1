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
python scripts/check_doc_counts.py || {
    echo "Doc counts have drifted. Update CLAUDE.md, README.md, and/or seed.json."
    exit 1
}

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
Write-Host "If any check fails, the commit will be blocked and you'll need to fix the issues." -ForegroundColor Cyan
