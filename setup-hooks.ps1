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

# Create pre-commit hook
$preCommitContent = @'
@echo off
REM Pre-commit hook for DivineOS
REM Enforces ruff formatting, linting, and mypy type checking

powershell -ExecutionPolicy Bypass -File "%~dp0pre-commit.ps1"
exit /b %ERRORLEVEL%
'@

$preCommitPath = "$hooksDir/pre-commit.bat"
Set-Content -Path $preCommitPath -Value $preCommitContent -Encoding ASCII
Write-Host "Created pre-commit hook at $preCommitPath"

# Create pre-commit PowerShell script
$preCommitPsContent = @'
# Pre-commit hook to enforce ruff formatting and linting (PowerShell version)

$ErrorActionPreference = "Stop"

Write-Host "Running ruff format check..."
ruff format --check src/ tests/
if ($LASTEXITCODE -ne 0) {
    Write-Host "Formatting violations detected. Running ruff format to fix..." -ForegroundColor Yellow
    ruff format src/ tests/
    Write-Host "Files formatted. Please review and stage the changes:" -ForegroundColor Yellow
    git diff --name-only
    Write-Host "After reviewing, run: git add . && git commit" -ForegroundColor Yellow
    exit 1
}

Write-Host "Running ruff lint check..."
ruff check src/ tests/
if ($LASTEXITCODE -ne 0) {
    Write-Host "Linting violations detected. Please fix them before committing." -ForegroundColor Red
    exit 1
}

Write-Host "Running mypy type check..."
mypy src/divineos --ignore-missing-imports
if ($LASTEXITCODE -ne 0) {
    Write-Host "Type errors detected. Please fix them before committing." -ForegroundColor Red
    exit 1
}

Write-Host "All checks passed!" -ForegroundColor Green
exit 0
'@

$preCommitPsPath = "$hooksDir/pre-commit.ps1"
Set-Content -Path $preCommitPsPath -Value $preCommitPsContent -Encoding UTF8
Write-Host "Created pre-commit PowerShell script at $preCommitPsPath"

Write-Host ""
Write-Host "Git hooks setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "The following checks will run before each commit:" -ForegroundColor Cyan
Write-Host "  1. ruff format --check (formatting compliance)"
Write-Host "  2. ruff check (linting)"
Write-Host "  3. mypy (type checking)"
Write-Host ""
Write-Host "If any check fails, the commit will be blocked and you'll need to fix the issues." -ForegroundColor Cyan
