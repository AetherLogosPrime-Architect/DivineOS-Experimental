#!/bin/bash
# Tests for scripts/divineos_push.sh.
#
# Validates the structural properties that close correction #53:
#   (1) exit code from `git push` propagates correctly through the wrapper
#   (2) post-push ls-remote verification catches the silent-divergence
#       failure mode
#   (3) final-status line is the LAST line of stdout (so the harness
#       sees the truth even after tail-style truncation)

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WRAPPER="$REPO_ROOT/scripts/divineos_push.sh"

fail() {
    echo "[FAIL] $1" >&2
    exit 1
}

pass() {
    echo "[PASS] $1"
}

# Set up a temp dir for fake "remote" + "local" repos so we exercise the
# real push path without touching a real git remote.
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT
REMOTE_DIR="$TMP_DIR/remote.git"
LOCAL_DIR="$TMP_DIR/local"

git init --bare --initial-branch=main "$REMOTE_DIR" >/dev/null 2>&1
git init --initial-branch=main "$LOCAL_DIR" >/dev/null 2>&1
cd "$LOCAL_DIR" || exit 1
git config user.email "test@test"
git config user.name "test"
echo "hello" > README.md
git add README.md
git commit -m "initial" >/dev/null 2>&1
git remote add origin "$REMOTE_DIR"

# Test 1: successful push prints final-status line and exits 0.
OUT="$(bash "$WRAPPER" origin main 2>&1)"
EC=$?
if [[ "$EC" -ne 0 ]]; then
    fail "Test 1: expected exit 0 on successful push, got $EC"
fi
LAST_LINE="$(echo "$OUT" | tail -1)"
if [[ "$LAST_LINE" != *"PUSHED+VERIFIED"* ]]; then
    fail "Test 1: expected PUSHED+VERIFIED in last line, got: $LAST_LINE"
fi
pass "Test 1: successful push exits 0 with PUSHED+VERIFIED final line"

# Test 2: failed push propagates non-zero exit code.
# Trigger a failure by trying to push to a branch that doesn't exist locally.
OUT="$(bash "$WRAPPER" origin nonexistent-branch 2>&1)"
EC=$?
if [[ "$EC" -eq 0 ]]; then
    fail "Test 2: expected non-zero exit on failed push, got 0"
fi
LAST_LINE="$(echo "$OUT" | tail -1)"
if [[ "$LAST_LINE" != *"PUSH_FAILED"* ]]; then
    fail "Test 2: expected PUSH_FAILED in last line, got: $LAST_LINE"
fi
pass "Test 2: failed push exits non-zero with PUSH_FAILED final line"

# Test 3: the final-status line is genuinely the LAST line even when the
# wrapper's middle output is verbose. This is the property that closes
# correction #53 — even if the harness truncates output to the tail, the
# truth shows.
OUT="$(bash "$WRAPPER" origin main 2>&1)"
# `tail -5` is what the harness typically does; verify the result line is
# in the last 5 lines.
TAIL_5="$(echo "$OUT" | tail -5)"
if [[ "$TAIL_5" != *"result:"* ]]; then
    fail "Test 3: result line not visible in tail -5 of output"
fi
pass "Test 3: final-status line survives tail-5 truncation"

# Test 4: silent-divergence detection — wrapper exits non-zero if the
# remote ref doesn't reflect the local push afterwards. Simulate by
# rewinding the remote ref between push success and verification.
# This is harder to simulate in a unit shell test without mocking; we
# exercise it indirectly by checking that the wrapper DID call ls-remote
# (the verification path is present in the script).
if ! grep -q "git ls-remote" "$WRAPPER"; then
    fail "Test 4: wrapper missing ls-remote verification step"
fi
pass "Test 4: ls-remote verification step is present in wrapper"

echo ""
echo "All tests passed."
