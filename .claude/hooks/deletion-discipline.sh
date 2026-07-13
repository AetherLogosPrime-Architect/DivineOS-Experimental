#!/bin/bash
# PreToolUse hook — thin doorbell for the deletion-discipline gate.
#
# All judgment lives in `divineos.core.deletion_discipline.main()`. Migrated
# 2026-06-30 to the thin-wrapper pattern (Pop: "make the hooks dumber so they
# can't be wrong; put the logic in the OS so the decision happens where the
# contract is").
#
# Background (Andrew 2026-05-21): never pure-delete. Read + understand,
# investigate for anything worth saving, extract it, THEN delete. The OS
# module's block_reason() checks for a fresh justification matching the
# command; if missing on a destructive op, the hook prints a deny-JSON.
#
# Fail-open: any error exits 0 silently. Never blocks the workflow.

set +e
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
[ -z "$REPO_ROOT" ] && exit 0
# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)"
if [ -z "$PYTHON_BIN" ]; then
    # Fail-LOUD per Aletheia audit 2026-07-09 Deep Truck 1: a silently-skipped
    # enforcement gate is indistinguishable from a gate that ran clean. Record
    # the skip to stderr so a resolver-drift is investigable, not invisible.
    echo "  [deletion-discipline] SKIPPED: find_divineos_python returned nothing - gate did NOT run" >&2
    exit 0
fi

"$PYTHON_BIN" -c "
import sys
try:
    from divineos.core.deletion_discipline import main
    sys.exit(main())
except Exception:
    pass
" 2>/dev/null

exit 0
