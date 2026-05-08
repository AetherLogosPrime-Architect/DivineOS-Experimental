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
# commit-msg hook for DivineOS — two independent gates.
#
# 1. Multi-party-review: blocks commits that modify guardrail files
#    without the required External-Review trailer + valid Watchmen
#    audit round.
# 2. Closure-claim: blocks commit messages with closure-language
#    ("fully closed", "all N items addressed", "everything landed",
#    "body-building done") unless a recent verifier-run is recorded.
#    Defends against the round-1 / round-3 audit-cleanup recurrence
#    pattern: closure-language commit messages without actual
#    verification of the claim. Pre-reg: prereg-e30878ce3f09.
#    Bypass: --no-verify on the commit (visible bypass only).
#
# Both delegate to standalone scripts; both fail-open if their script
# is missing (hooks must never block work because of broken infra).

set -e

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
MULTI_PARTY="$REPO_ROOT/scripts/check_multi_party_review.py"
CLOSURE_CLAIM="$REPO_ROOT/scripts/check_closure_claim.py"

# 1. Multi-party-review.
if [[ -f "$MULTI_PARTY" ]]; then
    python "$MULTI_PARTY" "$1" || {
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
fi

# 2. Closure-claim gate.
if [[ -f "$CLOSURE_CLAIM" ]]; then
    python "$CLOSURE_CLAIM" "$1" || exit 1
fi

exit 0
EOF

chmod +x "$HOOKS_DIR/commit-msg"
echo "Created commit-msg hook at $HOOKS_DIR/commit-msg"

# Create pre-push hook with two safety checks:
#   1. branch-freshness: blocks branches whose base is stale relative
#      to origin/main (silent-revert prevention, claim d3baec5a).
#   2. force-push-safety: blocks force-pushes that would shrink a
#      branch's unique-vs-main work below safety thresholds — catches
#      botched-rebase work-loss (prereg-c1c896a67321, 2026-05-04).
# Both delegate to standalone scripts so the logic stays testable.
cat > "$HOOKS_DIR/pre-push" << 'EOF'
#!/bin/bash
# pre-push hook for DivineOS — two safety checks.
# Bypass: DIVINEOS_SKIP_FRESHNESS_CHECK=1 (freshness)
#         DIVINEOS_FORCE_PUSH_OK=1 (force-push safety)

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
FRESHNESS="$REPO_ROOT/scripts/check_branch_freshness.sh"
FORCE_SAFETY="$REPO_ROOT/scripts/check_force_push_safety.sh"

# Capture stdin once — force-push-safety needs the ref-update lines
# but freshness does not read stdin.
HOOK_STDIN=$(cat)

# 1. Branch freshness.
if [[ -x "$FRESHNESS" ]]; then
    "$FRESHNESS" origin main
    RC=$?
    if [[ $RC -eq 1 ]]; then
        # Stale base detected — script already printed instructions.
        exit 1
    fi
fi

# 2. Force-push safety.
if [[ -x "$FORCE_SAFETY" ]]; then
    echo "$HOOK_STDIN" | "$FORCE_SAFETY" "$1"
    RC=$?
    if [[ $RC -eq 1 ]]; then
        exit 1
    fi
fi

exit 0
EOF

chmod +x "$HOOKS_DIR/pre-push"
echo "Created pre-push hook at $HOOKS_DIR/pre-push"

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
echo "Pre-push hook blocks pushes from branches whose base is stale"
echo "relative to origin/main (silent-revert prevention, claim d3baec5a)."
echo "Bypass with: DIVINEOS_SKIP_FRESHNESS_CHECK=1 git push"
echo ""
echo "If any check fails, the commit will be blocked and you'll need to fix the issues."
