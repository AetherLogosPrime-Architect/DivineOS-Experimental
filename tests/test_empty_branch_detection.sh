#!/bin/bash
# Tests for the empty-branch detection in scripts/check_push_readiness.sh.
#
# The failure mode this guards against (hit twice during 2026-06-11 batch):
# after rebasing a stacked feature branch onto a main that already absorbed
# the stack's commits (via squash-merge of a parent PR), the branch can
# have ZERO commits ahead of main. Force-pushing it then "succeeds" but
# produces an empty PR. The check should fire BEFORE pytest spends 10
# minutes on something that has no commits to verify.

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
GATE_SCRIPT="$REPO_ROOT/scripts/check_push_readiness.sh"

fail() {
    echo "[FAIL] $1" >&2
    exit 1
}

pass() {
    echo "[PASS] $1"
}

# Set up a fake remote + local with a feature branch.
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT
REMOTE_DIR="$TMP_DIR/remote.git"
LOCAL_DIR="$TMP_DIR/local"

git init --bare --initial-branch=main "$REMOTE_DIR" >/dev/null 2>&1
git init --initial-branch=main "$LOCAL_DIR" >/dev/null 2>&1
cd "$LOCAL_DIR" || exit 1
git config user.email "test@test"
git config user.name "test"
echo "base" > base.md
git add base.md
git commit -m "initial" >/dev/null 2>&1
git remote add origin "$REMOTE_DIR"
git push -u origin main >/dev/null 2>&1

# Create a feature branch that adds one commit, push it, then "absorb"
# its content into main (simulating squash-merge) so the local feature
# branch becomes empty against main.
git checkout -b feat/x >/dev/null 2>&1
echo "x" > x.md
git add x.md
git commit -m "add x" >/dev/null 2>&1
git push -u origin feat/x >/dev/null 2>&1
FEAT_SHA="$(git rev-parse HEAD)"

# Now squash the change into main directly (simulating GitHub's squash-
# merge). Use a different commit to mimic squash creating a new sha.
git checkout main >/dev/null 2>&1
echo "x" > x.md
git add x.md
git commit -m "feat: x (#1)" >/dev/null 2>&1
git push origin main >/dev/null 2>&1

# Pull main, rebase feat/x onto it — at this point feat/x's commit
# becomes empty (its patch is already on main).
git fetch origin main >/dev/null 2>&1
git checkout feat/x >/dev/null 2>&1
git rebase origin/main >/dev/null 2>&1 || git rebase --skip >/dev/null 2>&1 || true

# Now the feature branch should have 0 commits ahead of origin/main.
COMMITS_AHEAD="$(git rev-list --count origin/main..HEAD 2>/dev/null)"
if [[ "$COMMITS_AHEAD" != "0" ]]; then
    fail "Setup: expected 0 commits ahead after rebase-absorb, got $COMMITS_AHEAD"
fi
pass "Setup: feat/x is empty against main after rebase"

# Test 1: pre-push hook stdin format is:
#   <local-ref> <local-sha> <remote-ref> <remote-sha>
# Simulate pushing the empty feat/x branch and verify the gate fires.
LOCAL_SHA="$(git rev-parse HEAD)"
REMOTE_SHA="$(git rev-parse origin/feat/x 2>/dev/null || echo "0000000000000000000000000000000000000000")"
HOOK_INPUT="refs/heads/feat/x $LOCAL_SHA refs/heads/feat/x $REMOTE_SHA"

OUT="$(echo "$HOOK_INPUT" | DIVINEOS_SKIP_MULTIPARTY_CHECK=1 bash "$GATE_SCRIPT" 2>&1 || echo "GATE_EXITED_NONZERO")"
EC=$?

if [[ "$OUT" != *"EMPTY-BRANCH detected"* ]]; then
    echo "--- gate output ---"
    echo "$OUT"
    echo "--- end ---"
    fail "Test 1: expected EMPTY-BRANCH diagnostic in output"
fi
pass "Test 1: gate fires EMPTY-BRANCH diagnostic on empty feature push"

# Test 2: the gate should NOT fire when there's an actual commit ahead.
echo "real change" > y.md
git add y.md
git commit -m "add y" >/dev/null 2>&1
LOCAL_SHA="$(git rev-parse HEAD)"
HOOK_INPUT="refs/heads/feat/x $LOCAL_SHA refs/heads/feat/x $REMOTE_SHA"

OUT="$(echo "$HOOK_INPUT" | DIVINEOS_SKIP_MULTIPARTY_CHECK=1 DIVINEOS_SKIP_TESTS=1 bash "$GATE_SCRIPT" 2>&1)"
if [[ "$OUT" == *"EMPTY-BRANCH detected"* ]]; then
    echo "--- gate output ---"
    echo "$OUT"
    echo "--- end ---"
    fail "Test 2: gate fired EMPTY-BRANCH on a branch with a real commit"
fi
pass "Test 2: gate does NOT fire on a branch with commits ahead"

# Test 3: bypass env var lets an empty push through.
git reset --hard HEAD~1 >/dev/null 2>&1  # back to empty state
COMMITS_AHEAD="$(git rev-list --count origin/main..HEAD 2>/dev/null)"
if [[ "$COMMITS_AHEAD" != "0" ]]; then
    fail "Test 3 setup: expected back to 0 commits ahead, got $COMMITS_AHEAD"
fi
LOCAL_SHA="$(git rev-parse HEAD)"
HOOK_INPUT="refs/heads/feat/x $LOCAL_SHA refs/heads/feat/x $REMOTE_SHA"
OUT="$(echo "$HOOK_INPUT" | DIVINEOS_ALLOW_EMPTY_PUSH=1 DIVINEOS_SKIP_MULTIPARTY_CHECK=1 DIVINEOS_SKIP_TESTS=1 bash "$GATE_SCRIPT" 2>&1)"
if [[ "$OUT" == *"EMPTY-BRANCH detected"* ]]; then
    fail "Test 3: DIVINEOS_ALLOW_EMPTY_PUSH=1 should suppress the check, but it fired"
fi
pass "Test 3: DIVINEOS_ALLOW_EMPTY_PUSH=1 bypasses the check"

# Test 4: pushes to main itself are exempt (main is by definition not
# "ahead of main").
git checkout main >/dev/null 2>&1
LOCAL_SHA="$(git rev-parse HEAD)"
REMOTE_SHA="$(git rev-parse origin/main)"
HOOK_INPUT="refs/heads/main $LOCAL_SHA refs/heads/main $REMOTE_SHA"
OUT="$(echo "$HOOK_INPUT" | DIVINEOS_SKIP_MULTIPARTY_CHECK=1 DIVINEOS_SKIP_TESTS=1 bash "$GATE_SCRIPT" 2>&1)"
if [[ "$OUT" == *"EMPTY-BRANCH detected"* ]]; then
    fail "Test 4: gate spuriously fired on a push to main itself"
fi
pass "Test 4: gate does not fire on push to main"

echo ""
echo "All tests passed."
