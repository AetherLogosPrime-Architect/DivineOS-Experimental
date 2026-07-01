#!/bin/bash
# PreToolUse hook — thin doorbell for the compass-rudder gate.
#
# All judgment lives in `divineos.core.compass_rudder.main()`. The OS-side
# was migrated by Aria 2026-06-30; this commit (Aether) thins the bash
# hook to match the pattern.
#
# Fail-open: any error exits 0 silently. Never blocks the workflow.

set +e
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
[ -z "$REPO_ROOT" ] && exit 0
# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

"$PYTHON_BIN" -c "
import sys
try:
    from divineos.core.compass_rudder import main
    sys.exit(main())
except Exception:
    pass
" 2>/dev/null

exit 0
