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

PYTHON_BIN="$(command -v python || command -v python3)" || exit 0

"$PYTHON_BIN" - <<'PYEOF' 2>/dev/null
try:
    from divineos.core.noticing import mark_turn_start

    mark_turn_start()
except Exception:
    pass
PYEOF

exit 0
