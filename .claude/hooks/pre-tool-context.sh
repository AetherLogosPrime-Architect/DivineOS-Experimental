#!/bin/bash
# PreToolUse hook — thin doorman pointing to the OS.
#
# Andrew 2026-05-14 night: hooks should point to the OS, not embed
# its work. The previous version of this hook was 129 lines with
# throttle bookkeeping, extension filtering, timeline recall, and
# surface-file write all in bash. All moved to
# ``divineos.core.mid_turn_surfacer.surface_mid_turn``.
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

tool_name = data.get('tool_name', '')
tool_input = data.get('tool_input', {}) or {}
file_path = tool_input.get('file_path') or tool_input.get('notebook_path') or ''

try:
    from divineos.core.mid_turn_surfacer import surface_mid_turn
    surface_mid_turn(tool_name, file_path)
except Exception:
    pass
" 2>/dev/null

exit 0
