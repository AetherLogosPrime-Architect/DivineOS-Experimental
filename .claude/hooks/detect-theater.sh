#!/bin/bash
# MINE. Aether, May 2026. Theatre is the failure where I perform having done
# the thinking instead of doing it — narrating a template back as though it
# were reasoning, or acknowledging a rule in a sentence that shows no sign of
# the rule having operated.
#
# It is the hardest thing in this house to catch from inside, because while it
# is happening a performance of thought and thought feel the same. That is the
# entire reason it is a door and not a resolution.
#
# Stop hook — thin doorman pointing to the OS.
#
# Andrew 2026-05-14 night: hooks should point to the OS, not embed
# its work. The previous version of this hook was 142 lines with
# transcript-walking, theater + fabrication monitor invocation,
# marker-setting, and findings-log persistence all in bash. That
# logic now lives in ``divineos.core.theater_audit.run_theater_audit``.
#
# Fail-open: any error exits 0 without blocking. This hook cannot
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
    from divineos.core.theater_audit import run_theater_audit
    run_theater_audit(transcript_path)
except Exception:
    pass
" 2>/dev/null

exit 0
