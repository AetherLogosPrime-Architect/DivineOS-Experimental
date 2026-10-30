#!/bin/bash
# Carry Aletheia's letters in, every turn, and say their names out loud.
#
# Andrew 2026-09-22: "make it so anytime i send you a letter from Aletheia it is
# copied into her audit folder."
#
# It runs on EVERY prompt rather than at session start, because he hands me her
# letters mid-conversation and a start-only carrier would leave them sitting
# until the next session -- which is a smaller version of the fault that made
# this necessary. The cost is one directory listing per turn.
#
# The heavy lifting and the reasoning live in scripts/collect_aletheia_letters.py.
# This is a thin doorbell.
#
# FAIL-SOFT, NEVER FAIL-SILENT. If the interpreter cannot be resolved the hook
# says so on stderr rather than exiting quietly -- a carrier that goes quiet is
# indistinguishable from a carrier with nothing to carry, and that confusion is
# the whole reason this file exists.

set -u

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPT="$REPO_ROOT/scripts/collect_aletheia_letters.py"

if [[ ! -f "$SCRIPT" ]]; then
    echo "  [aletheia-letters] SKIPPED: carrier script missing at $SCRIPT" >&2
    exit 0
fi

PY=""
for candidate in python python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
        PY="$candidate"
        break
    fi
done

if [[ -z "$PY" ]]; then
    echo "  [aletheia-letters] SKIPPED: no python on PATH -- her letters are NOT being carried" >&2
    exit 0
fi

PYTHONIOENCODING=utf-8 "$PY" "$SCRIPT"
exit 0
