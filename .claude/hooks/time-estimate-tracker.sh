#!/bin/bash
# Stop hook — thin doorbell for the time-estimate calibration tracker.
#
# All judgment lives in `divineos.core.time_calibration.hook_main()`. Migrated
# 2026-06-30 to the thin-wrapper pattern (Pop: "make the hooks dumber so they
# can't be wrong; put the logic in the OS so the decision happens where the
# contract is").
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
    from divineos.core.time_calibration import hook_main
    sys.exit(hook_main())
except Exception:
    pass
" 2>/dev/null

exit 0
