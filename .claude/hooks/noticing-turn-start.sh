#!/bin/bash
# Marks when he starts speaking, so the Stop gate can tell "this turn" from
# "some turn". Nothing else.
#
# Silent by design -- this one has nothing to say to me, it only starts the
# clock. The gate that HAS something to say is noticing-stop.sh.
#
# FAIL DIRECTION. If the mark cannot be written, the Stop gate finds an
# unknown turn-start and REFUSES. That is correct: a missing mark must never
# read as a satisfied turn. Silence here costs a refusal later, which is the
# cheap direction to fail in.
# shellcheck disable=SC1091
source "$(git rev-parse --show-toplevel 2>/dev/null || echo .)/.claude/hooks/_lib.sh" 2>/dev/null || true

INPUT=$(cat)
[ -z "$INPUT" ] && exit 0

# Must be the divineos python, not the operator's shell python. A bare
# `command -v python` fails OPEN when that interpreter lacks the deps --
# and a silently-absent turn mark reads downstream as an unknown turn,
# which the Stop gate correctly refuses. Caught by
# tests/test_hook_python_lookup.py before this ever shipped.
PYTHON_BIN="$(find_divineos_python)" || exit 0

"$PYTHON_BIN" - <<'PYEOF' 2>/dev/null
try:
    from divineos.core.noticing import mark_turn_start

    mark_turn_start()
except Exception:
    pass
PYEOF

exit 0
