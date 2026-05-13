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
# Substrate-fix 2026-05-10 (Aether, hold-644d325062b2):
# The prior behavior aborted the commit and asked the operator to
# manually re-stage formatted files. That created two failure modes:
#   1. Friction tax — every commit that touched whitespace required
#      a re-stage + re-commit cycle, sometimes multiple times per
#      commit.
#   2. Audit-hash drift — when an External-Review round was filed
#      with a hash bound to pre-format staged content, the auto-
#      format here drifted the hash and the multi-party-review gate
#      rejected the commit, requiring a fresh audit round filed
#      against the post-format hash.
# Ruff format is deterministic and safe. Auto-staging the formatted
# files lets the commit proceed. For guardrail-touching commits,
# operators should run \`bash scripts/precommit.sh\` BEFORE filing
# the External-Review round so the audit-bound hash matches the
# eventual commit hash.
ruff format --check src/ tests/ || {
    echo "Formatting violations detected. Running ruff format to fix..."
    ruff format src/ tests/
    echo "Auto-staging formatted .py files that were already staged..."
    # Only re-stage already-staged files. Working-tree-only changes
    # stay unstaged so the operator's intent is preserved.
    git diff --cached --name-only --diff-filter=ACM | grep -E '\.py\$' | xargs --no-run-if-empty git add
    echo "Re-checking format after auto-stage..."
    ruff format --check src/ tests/ || {
        echo "Format still failing after auto-format — investigate manually."
        exit 1
    }
    echo "  Format clean after auto-stage; continuing."
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

# Create commit-msg hook.
#
# Gate-altitude correction (Andrew 2026-05-12): commits should never be
# blocked. Work-preservation matters; cross-vantage audit needs to SEE the
# diffs to audit them; the boundary that needs protection is the merge
# into main, not every commit on a feature branch. The multi-party-review
# check runs here in ADVISORY mode (warns informationally; doesn't block).
# The real gate fires at pre-push when target is refs/heads/main.
#
# The closure-claim gate stays at commit-msg time; it targets a different
# failure-mode (closure-language without verification) that should be
# caught at commit-time regardless of where the commit lives.
cat > "$HOOKS_DIR/commit-msg" << 'EOF'
#!/bin/bash
# commit-msg hook for DivineOS.
#
# 1. Multi-party-review: ADVISORY at commit-time. Warns if guardrail
#    files are touched without the trailer; does not block. The real
#    block fires at pre-push when target is refs/heads/main. Reason:
#    commits to feature branches must succeed so cross-vantage audit
#    can see the diffs; the protected boundary is merge-into-main.
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
ROOT_CAUSE_AUDIT="$REPO_ROOT/scripts/check_root_cause_audit.py"

# 1. Multi-party-review — INFORMATIONAL at commit-time.
# Script never blocks at commit-time; just warns if guardrails touched
# without trailer. Real gate fires at pre-push.
if [[ -f "$MULTI_PARTY" ]]; then
    python "$MULTI_PARTY" "$1" || true
fi

# 2. Closure-claim gate.
if [[ -f "$CLOSURE_CLAIM" ]]; then
    python "$CLOSURE_CLAIM" "$1" || exit 1
fi

# 3. Root-cause-audit gate — ADVISORY at commit-time, BLOCKING at
# pre-push-to-main (added below). Enforces family-level investigation
# before bugfix-shaped commits. Family this addresses: instance-fix-
# without-family-audit (substrate-knowledge round-38d9fd161175). The
# OS describes the discipline in 67a0ff39; this gate makes the
# discipline structural rather than advisory.
if [[ -f "$ROOT_CAUSE_AUDIT" ]]; then
    python "$ROOT_CAUSE_AUDIT" --mode=commit-msg --commit-msg-file "$1" || true
fi

exit 0
EOF

chmod +x "$HOOKS_DIR/commit-msg"
echo "Created commit-msg hook at $HOOKS_DIR/commit-msg"

# Create pre-push hook with THREE safety checks:
#   1. branch-freshness: blocks branches whose base is stale relative
#      to origin/main (silent-revert prevention, claim d3baec5a).
#   2. force-push-safety: blocks force-pushes that would shrink a
#      branch's unique-vs-main work below safety thresholds — catches
#      botched-rebase work-loss (prereg-c1c896a67321, 2026-05-04).
#   3. multi-party-review: when target is refs/heads/main, blocks
#      commits in the push-range that touch guardrail files without
#      a valid External-Review trailer. This is the gate that used
#      to fire at commit-msg time; moved to pre-push 2026-05-12 per
#      Andrew's altitude-correction (commits should never be blocked;
#      only push-to-main should). "Main" means any production-bound
#      branch (DivineOS prod's main AND DivineOS-Experimental's main).
# All delegate to standalone scripts so the logic stays testable.
cat > "$HOOKS_DIR/pre-push" << 'EOF'
#!/bin/bash
# pre-push hook for DivineOS — three safety checks.
# Bypass: DIVINEOS_SKIP_FRESHNESS_CHECK=1 (freshness)
#         DIVINEOS_FORCE_PUSH_OK=1 (force-push safety)

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
FRESHNESS="$REPO_ROOT/scripts/check_branch_freshness.sh"
FORCE_SAFETY="$REPO_ROOT/scripts/check_force_push_safety.sh"
MULTI_PARTY="$REPO_ROOT/scripts/check_multi_party_review.py"
ROOT_CAUSE_AUDIT="$REPO_ROOT/scripts/check_root_cause_audit.py"

# Capture stdin once — force-push-safety, multi-party-review, and
# root-cause-audit need the ref-update lines but freshness does not.
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

# 3. Multi-party-review (pre-push mode).
# Fires only when target is refs/heads/main (any remote). Walks the
# push-range and blocks if any commit touching guardrail files lacks
# the External-Review trailer. The script's pre-push mode handles the
# ref-filtering internally.
if [[ -f "$MULTI_PARTY" ]]; then
    echo "$HOOK_STDIN" | python "$MULTI_PARTY" --mode=pre-push
    RC=$?
    if [[ $RC -eq 1 ]]; then
        exit 1
    fi
fi

# 4. Root-cause-audit (pre-push mode).
# Walks the push-range when target is refs/heads/main. Blocks if any
# fix-shaped commit lacks a Root-Cause-Audit trailer pointing to a
# valid root-cause-audit round. The script's pre-push mode handles
# the ref-filtering internally.
if [[ -f "$ROOT_CAUSE_AUDIT" ]]; then
    echo "$HOOK_STDIN" | python "$ROOT_CAUSE_AUDIT" --mode=pre-push
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
