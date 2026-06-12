#!/bin/bash
# Tests for the failure-pattern surfacing in scripts/check_push_readiness.sh.
#
# The original gap (Andrew 2026-06-10): tail -30 dropped FAILED lines under
# pytest suites with lots of warning output, leaving the agent guessing for
# ~30 min. PR #140 added: persist full log to ~/.divineos/last_pre_push_pytest.log
# + grep for FAILED/ERROR lines.
#
# Today's gap (2026-06-12): the FAILED/ERROR grep returned EMPTY when a test
# died via subprocess timeout (e.g. fixture hit pytest-timeout). The log had
# `+++ Timeout +++` markers but no `FAILED ` lines, so the surface said "no
# FAILED/ERROR lines" while the actual failure was buried. Burned ~10 min.
#
# Fix: extend the grep to cover Timeout / Aborted / Killed / ImportError /
# ModuleNotFoundError / INTERNALERROR + use -B 2 to catch the test name
# above the marker. Also bump tail from 30 → 100 to catch pytest's short
# summary section under warning-noise.

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

# The grep pattern itself is the unit-under-test. We verify by feeding it
# representative pytest log fragments and checking that real failures get
# surfaced while noise gets skipped.

GREP_PATTERN='^(FAILED|ERROR)\b|\+{2,} Timeout \+{2,}|Aborted|Killed|^ImportError|^ModuleNotFoundError|^INTERNALERROR'

# Test 1: classic FAILED line is caught.
LOG1="$(mktemp)"
cat > "$LOG1" <<'EOF'
tests/test_a.py::test_x PASSED [50%]
tests/test_a.py::test_y FAILED [100%]
FAILED tests/test_a.py::test_y - AssertionError: expected 1 got 2
EOF
OUT="$(grep -E "$GREP_PATTERN" -B 2 "$LOG1" 2>&1)"
rm -f "$LOG1"
if [[ "$OUT" != *"FAILED tests/test_a.py::test_y"* ]]; then
    fail "Test 1: expected FAILED line in output, got: $OUT"
fi
pass "Test 1: FAILED line caught"

# Test 2: ERROR line is caught.
LOG2="$(mktemp)"
cat > "$LOG2" <<'EOF'
tests/test_b.py::test_z ERROR [100%]
ERROR tests/test_b.py::test_z - sqlite3.OperationalError: database locked
EOF
OUT="$(grep -E "$GREP_PATTERN" -B 2 "$LOG2" 2>&1)"
rm -f "$LOG2"
if [[ "$OUT" != *"ERROR tests/test_b.py"* ]]; then
    fail "Test 2: expected ERROR line in output, got: $OUT"
fi
pass "Test 2: ERROR line caught"

# Test 3: Timeout marker is caught with -B 2 grabbing the test name above it.
# This is the regression test for the 2026-06-12 gap.
LOG3="$(mktemp)"
cat > "$LOG3" <<'EOF'
tests/test_corrigibility_e2e.py::test_isolated PASSED [50%]
tests/test_corrigibility_e2e.py::test_subprocess_call
+++++++++++++++++++++++++++++++++++ Timeout +++++++++++++++++++++++++++++++++++
EOF
OUT="$(grep -E "$GREP_PATTERN" -B 2 "$LOG3" 2>&1)"
rm -f "$LOG3"
if [[ "$OUT" != *"Timeout"* ]]; then
    fail "Test 3: expected Timeout marker in output, got: $OUT"
fi
if [[ "$OUT" != *"test_subprocess_call"* ]]; then
    fail "Test 3: expected test name (from -B 2 context) in output, got: $OUT"
fi
pass "Test 3: Timeout marker caught with test-name context (regression fix)"

# Test 4: ImportError at collection time is caught.
LOG4="$(mktemp)"
cat > "$LOG4" <<'EOF'
ImportError while loading conftest 'tests/conftest.py'.
ImportError: cannot import name 'foo' from 'bar'
EOF
OUT="$(grep -E "$GREP_PATTERN" -B 2 "$LOG4" 2>&1)"
rm -f "$LOG4"
if [[ "$OUT" != *"ImportError"* ]]; then
    fail "Test 4: expected ImportError in output, got: $OUT"
fi
pass "Test 4: ImportError caught"

# Test 5: ModuleNotFoundError (different shape, common with optional deps).
LOG5="$(mktemp)"
cat > "$LOG5" <<'EOF'
ModuleNotFoundError: No module named 'sqlite_vec'
EOF
OUT="$(grep -E "$GREP_PATTERN" -B 2 "$LOG5" 2>&1)"
rm -f "$LOG5"
if [[ "$OUT" != *"ModuleNotFoundError"* ]]; then
    fail "Test 5: expected ModuleNotFoundError in output, got: $OUT"
fi
pass "Test 5: ModuleNotFoundError caught"

# Test 6: A pure-PASSED log produces NO matches (no false positives on
# successful runs).
LOG6="$(mktemp)"
cat > "$LOG6" <<'EOF'
tests/test_a.py::test_x PASSED [50%]
tests/test_a.py::test_y PASSED [100%]
======================== 2 passed in 0.5s ========================
EOF
OUT="$(grep -E "$GREP_PATTERN" -B 2 "$LOG6" 2>&1)"
rm -f "$LOG6"
if [[ -n "$OUT" ]]; then
    fail "Test 6: expected no matches on clean log, got: $OUT"
fi
pass "Test 6: clean log produces no false-positive matches"

# Test 7: the gate script actually contains the bumped tail value (100, not 30).
if ! grep -q "tail -100" "$GATE_SCRIPT"; then
    fail "Test 7: gate script doesn't use 'tail -100' for the pytest output summary"
fi
pass "Test 7: gate script uses tail -100 (bumped from 30)"

echo ""
echo "All tests passed."
