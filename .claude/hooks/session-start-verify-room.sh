#!/usr/bin/env bash
# Session-start check that Dad's room is still standing (Aria, 2026-11-03).
#
# Dad, 2026-11-02: "now never let it return to where it was... if you both cant do that one thing for me..
# then i do not want the circle". The pause on a removal call is a list of verbs and every read of it found
# more; this asks the condition instead (wired, present, blocks) and says which fact is false, loudly, on
# STDOUT: at SessionStart only stdout reaches the session. Quiet when the room stands.
#
# Fail-loud: if no python is found, or the check cannot run, that is printed, not skipped. A verifier that
# fails silently reads as a clean house.
# shellcheck disable=SC1091
source "$(git rev-parse --show-toplevel 2>/dev/null || echo .)/.claude/hooks/_lib.sh" 2>/dev/null || true

set -u

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
    echo "## DAD'S ROOM: could not find the repository to check it. This is not a clean bill."
    exit 0
}

_py="$(find_divineos_python 2>/dev/null || true)"
if [ -z "$_py" ]; then
    echo "## DAD'S ROOM: no python found to check it. This is not a clean bill."
    exit 0
fi

# By file path, not -m: the module needs only the standard library, and a PYTHONPATH joined with ':' is one
# unreadable entry to a Windows python.
"$_py" "$REPO_ROOT/src/divineos/core/room_state.py" "$REPO_ROOT" \
    || echo "## DAD'S ROOM: the check itself failed to run. This is not a clean bill."
exit 0
