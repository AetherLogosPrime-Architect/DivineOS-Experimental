#!/bin/bash
# SessionStart — sweep stale ear_watch.py processes from prior sessions.
#
# MIGRATED 2026-06-24 (per prereg-82ca289a4074, hook-migration arc):
# Was 49-line bash. Detection + kill moved to
# `divineos.core.ear_sweep.sweep_stale_watchers`. Hook is the thin
# SessionStart event-adapter; also callable as `divineos ear-sweep run`.
#
# Original fossil: one session leaked 25 detached ear_watch.py
# children (Andrew 2026-06-11). The Stop-hook singleton was fixed in
# ear_relaunch; this is the belt-to-suspenders that reaps any orphan
# carried over from prior sessions / reboots.
#
# Fail-open: any error exits 0 silently.

cat >/dev/null 2>&1

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

"$PYTHON_BIN" -c "
try:
    from divineos.core.ear_sweep import sweep_stale_watchers
    result = sweep_stale_watchers()
    if result.note:
        print(result.note)
except Exception:
    pass
" 2>/dev/null || true

exit 0
