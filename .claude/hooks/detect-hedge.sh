#!/bin/bash
# Stop hook — thin doorman pointing to the OS.
#
# Andrew 2026-05-14 night: hooks point to OS, OS does the work.
# Previous version was 97 lines with transcript walking, hedge_monitor
# invocation, and marker-setting embedded. All moved to
# ``divineos.core.hedge_audit.run_hedge_audit``.
#
# Fail-open: any error exits 0 without blocking.

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

transcript_path = data.get('transcript_path') or data.get('transcript')
if not transcript_path:
    sys.exit(0)

try:
    from divineos.core.hedge_audit import run_hedge_audit
    run_hedge_audit(transcript_path)
except Exception:
    pass
" 2>/dev/null

exit 0
