#!/bin/bash
# UserPromptSubmit hook — thin doorman pointing to the OS.
#
# Andrew 2026-05-14 night: hooks should point to the OS, not embed
# its work. The previous version of this hook was 496 lines with
# context surfacing, finding-warning text assembly, and base-state
# affirmation loading all embedded as Python in bash. That logic
# now lives in ``divineos.core.pre_response_context``.
#
# Fail-open: any error exits 0 without emitting context. This hook
# cannot break the user's workflow.

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
prompt = data.get('prompt', '') if isinstance(data, dict) else ''

try:
    from divineos.core.pre_response_context import build_combined_context
    combined = build_combined_context(prompt)
except Exception:
    sys.exit(0)

if combined:
    print(json.dumps({
        'hookSpecificOutput': {
            'hookEventName': 'UserPromptSubmit',
            'additionalContext': combined,
        }
    }))
" 2>/dev/null

exit 0
