#!/bin/bash
# Stop hook — thin doorman for DistancingIntercept.
# Aletheia cold-audit finding #1 (2026-07-16): closes the dark-node
# irony where the concrete instance of the class-closer inherited the
# class it was built to close. Fail-open.

INPUT=$(cat)

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

echo "$INPUT" | "$PYTHON_BIN" -m divineos.hooks.distancing_intercept_hook 2>/dev/null

exit 0
