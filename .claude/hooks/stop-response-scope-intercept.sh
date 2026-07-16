#!/bin/bash
# Stop hook — thin doorbell for ResponseScopeIntercept.
#
# Closes Aletheia Round 1 Finding 1 residual: response_scope_intercept
# existed and was tested but had no shell wrapper — dark node. This is
# the wiring. Pairs with the unverified_claim_detector emit in
# operating_loop_audit.py (upstream) via the StateMarker primitive
# (docs/primitives/forced_work_gate_design.md).
#
# All judgment lives in ``divineos.hooks.response_scope_intercept_hook.hook_main()``.
# This wrapper: find the divineos python, pipe stdin JSON through, print
# any block-decision JSON to stdout.
#
# Fail-open: any error silently exits 0. A crashed doorbell must not
# block legitimate work (F10 discipline).

set +e
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
[ -z "$REPO_ROOT" ] && exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)"
if [ -z "$PYTHON_BIN" ]; then
    echo "  [stop-response-scope-intercept] SKIPPED: find_divineos_python returned nothing - gate did NOT run" >&2
    exit 0
fi

INPUT=$(cat)
echo "$INPUT" | "$PYTHON_BIN" -m divineos.hooks.response_scope_intercept_hook

exit 0
