#!/bin/bash
# PreToolUse hook — thin doorbell for the no-verify cost-escalation gate.
#
# SUPERSEDED 2026-08-25 by the router. The decision now lives in
# `divineos.core.hook_surfaces.no_verify_cost_surface`, which calls
# `no_verify_cost.decide()` directly — `main()` below exists only to move that
# decision across a process boundary the router removes.
#
# Unregistered from settings.json in the same commit as the retirement.
#
# WHY IT MOVED, and it is the `except Exception: pass` at the bottom of this
# file. A raised decision exits 0 and prints nothing, which is byte-identical to
# this gate examining the command and approving it. The find-python failure
# above it is declared loudly (Aletheia 2026-07-09) — so this hook had one
# honest failure mode and one silent one, and the silent one was the one the
# canonical pattern told it to have. That pattern is corrected in
# docs/hook_migration_tracker.md; 27 hooks in this tree still carry the shape.
#
# Kept on disk, not deleted, per the incremental-migration rule.
#
# All judgment lives in `divineos.core.no_verify_cost.main()`. This script
# only locates a working python via _lib.sh and shells to the OS module.
# Migrated 2026-06-30 (Pop: "make the hooks dumber so they can't be wrong;
# put the logic in the OS so the decision happens where the contract is").
#
# Fail-open: any error exits 0 silently. Never breaks the workflow.

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
    echo "  [no-verify-cost-escalation] SKIPPED: find_divineos_python returned nothing - gate did NOT run" >&2
    exit 0
fi

"$PYTHON_BIN" -c "
import sys
try:
    from divineos.core.no_verify_cost import main
    sys.exit(main())
except Exception:
    pass
" 2>/dev/null

exit 0
