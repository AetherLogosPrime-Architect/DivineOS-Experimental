#!/bin/bash
# PreToolUse hook — thin doorbell for the compass rudder.
# All judgment lives in `divineos.core.compass_rudder.main()`.
#
# Migrated 2026-06-30 (Aria) per Aether's hook-thinness pattern:
#   docs/hook_migration_tracker.md.
# Prior thick version (~65 lines of embedded Python + bash) is in git
# history if forensic comparison is ever needed.

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
"

exit 0
