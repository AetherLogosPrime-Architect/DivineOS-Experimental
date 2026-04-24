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
python scripts/check_doc_counts.py --fix 2>/dev/null || true
git add CLAUDE.md README.md src/divineos/seed.json 2>/dev/null || true
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
EOF

chmod +x "$HOOKS_DIR/pre-commit"
echo "Created pre-commit hook at $HOOKS_DIR/pre-commit"

# Create commit-msg hook (multi-party-review gate for guardrail files).
# Runs after the user has written the commit message; validates that
# any modification to guardrail files carries a valid External-Review
# trailer referencing a Watchmen audit round with user + external-AI
# CONFIRMS findings. See scripts/check_multi_party_review.py.
cat > "$HOOKS_DIR/commit-msg" << 'EOF'
#!/bin/bash
# commit-msg hook for DivineOS — multi-party-review gate.
# Blocks commits that modify guardrail files without the required
# External-Review trailer + valid Watchmen audit round.

set -e

python scripts/check_multi_party_review.py "$1" || {
    echo ""
    echo "Guardrail-file modification blocked. See above for the specific"
    echo "reason. To proceed:"
    echo "  1. File an audit round with CONFIRMS findings from:"
    echo "       actor=user  (the human operator)"
    echo "       actor=grok | actor=gemini | actor=claude-<variant>"
    echo "  2. Include 'diff-hash: <64-hex>' in the round's focus or notes."
    echo "  3. Add 'External-Review: <round_id>' trailer to the commit."
    exit 1
}

exit 0
EOF

chmod +x "$HOOKS_DIR/commit-msg"
echo "Created commit-msg hook at $HOOKS_DIR/commit-msg"

echo ""
echo "Git hooks setup complete!"
echo ""
echo "The following checks will run before each commit:"
echo "  1. ruff format --check (formatting compliance)"
echo "  2. ruff check (linting)"
echo "  3. mypy (type checking)"
echo "  4. doc count drift (test/command counts vs reality)"
echo "  5. vulture dead-code (if installed)"
echo "  6. shellcheck on hooks (if installed)"
echo ""
echo "Additionally, commit-msg hook validates multi-party-review for"
echo "guardrail-file modifications (scripts/guardrail_files.txt)."
echo ""
echo "If any check fails, the commit will be blocked and you'll need to fix the issues."
