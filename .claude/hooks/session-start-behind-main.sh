#!/usr/bin/env bash
# Session-start: say how far behind origin/main the checkout these hooks run
# from is. Aria 2026-10-12: hers was 23 behind, mine 11, neither of us told, and
# her stale copy lacked the silence rule so the question hold held her all night.
# Prints to STDOUT (only stdout reaches the session at SessionStart). Fails loud:
# if python or the module cannot run it says so, never silence.
# shellcheck disable=SC1091
source "$(git rev-parse --show-toplevel 2>/dev/null || echo .)/.claude/hooks/_lib.sh" 2>/dev/null || true

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
    echo "## CHECKOUT vs MAIN: not inside a git checkout; could not measure."
    exit 0
}
_py="$(find_divineos_python 2>/dev/null || true)"
if [ -z "$_py" ]; then
    echo "## CHECKOUT vs MAIN: no python found to measure it; not the same as current."
    exit 0
fi
"$_py" "$REPO_ROOT/src/divineos/core/checkout_behind_main.py" "$REPO_ROOT" \
    || echo "## CHECKOUT vs MAIN: the check crashed; not the same as current."
exit 0
