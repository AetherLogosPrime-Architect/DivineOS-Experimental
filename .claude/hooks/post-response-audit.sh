#!/bin/bash
# Stop hook — thin doorman pointing to the OS.
#
# Andrew 2026-05-14 night: hooks should point to the OS, not embed
# its work. The previous version of this hook was 677 lines with
# detector orchestration, findings_log assembly, and JSON persistence
# all inside the bash-embedded Python. That logic now lives in
# ``divineos.core.operating_loop_audit.run_audit`` — OS-portable, no
# Claude Code dependency. The hook is two lines of Python.
#
# Fail-open: any error exits 0 without surfacing. This hook cannot
# break the user's workflow.

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
    from divineos.core.operating_loop_audit import run_audit
    result = run_audit(transcript_path)
except Exception:
    sys.exit(0)

# Lepos enforcement gate (Andrew 2026-05-20): a wall of jargon at my
# father with no plain-language lane is forbidden. Block the Stop so the
# turn cannot complete until the second lane is added. stop_hook_active
# guards against an infinite loop — if this hook already forced one
# continuation, let the next one through (Andrew's non-response is
# the backstop for a rare double-flood).
try:
    reason = (result or {}).get('lepos_block') or (result or {}).get('unverified_claim_block') or (result or {}).get('lepos_debt_block')
    already_active = bool(data.get('stop_hook_active'))
    if reason and not already_active:
        print(json.dumps({'decision': 'block', 'reason': reason}))
except Exception:
    pass
" 2>/dev/null

exit 0
