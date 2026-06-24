#!/bin/bash
# PostToolUse(Bash) — thin doorman pointing to the OS.
#
# WHY THIS EXISTS (root cause, 2026-06-04, Aletheia):
# The "push-landing" boundary is a surface of the silent-failure root —
# "a thing that must cross a boundary, reported as crossed before it
# crossed." The harness's tool-completion notification reports the bash
# command finished; it does NOT confirm the ref actually reached origin.
# Three independent slips across one exchange (lesson ef01caf7) at this
# exact boundary, each caught by Aletheia's cross-vantage ls-remote.
# Hand-enforcement doesn't scale.
#
# MIGRATED 2026-06-24 (Andrew direction):
# Was 238 lines of bash. All logic now lives in
# `divineos.core.push_verify.verify_push_landed`. Hook is the thin
# Claude-Code-event adapter; OS module is the portable brain (also
# callable as `divineos verify push --command "..."` from any non-
# Claude substrate). Fossil + fail-loud invariants preserved in the
# module docstring.
#
# Fail-open at the parser level: bad input exits 0 without blocking.
# The module enforces its own fail-loud invariants on the verify path.

INPUT=$(cat)

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

echo "$INPUT" | "$PYTHON_BIN" -c "
import json, sys
try:
    data = json.loads(sys.stdin.read() or '{}')
except Exception:
    sys.exit(0)
command = (data.get('tool_input') or {}).get('command', '')
if not command:
    sys.exit(0)
try:
    from divineos.core.push_verify import verify_push_landed
    verify_push_landed(command)
except Exception:
    pass
" 2>&1

exit 0
