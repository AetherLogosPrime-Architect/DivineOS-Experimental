#!/bin/bash
# Setup script to install Git hooks for DivineOS
# Run this after cloning the repository: bash setup-hooks.sh

echo "Setting up Git hooks for DivineOS..."

# Create hooks directory if it doesn't exist
HOOKS_DIR=".git/hooks"
mkdir -p "$HOOKS_DIR"
echo "Created $HOOKS_DIR directory"

# Configure Git to use the hooks directory
git config core.hooksPath "$HOOKS_DIR"
echo "Configured Git to use hooks from $HOOKS_DIR"

# Create pre-commit hook
cat > "$HOOKS_DIR/pre-commit" << 'EOF'
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
EOF

chmod +x "$HOOKS_DIR/pre-commit"
echo "Created pre-commit hook at $HOOKS_DIR/pre-commit"

echo ""
echo "Git hooks setup complete!"
echo ""
echo "The following checks will run before each commit:"
echo "  1. ruff format --check (formatting compliance)"
echo "  2. ruff check (linting)"
echo "  3. mypy (type checking)"
echo ""
echo "If any check fails, the commit will be blocked and you'll need to fix the issues."
