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
# Enforces ruff formatting, linting, and mypy type checking

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
Write-Host ""
Write-Host "If any check fails, the commit will be blocked and you'll need to fix the issues." -ForegroundColor Cyan
