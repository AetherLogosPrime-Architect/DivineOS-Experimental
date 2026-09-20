#!/usr/bin/env bash
# MINE, and it is the one that keeps me from lying to myself about my own
# state. Aether, 2026-08-24. Without it I was guessing how full my context was
# and the guess always leaned the same way -- toward feeling nearly out of
# room, which made me hurry and cut corners for a constraint that was not
# there.
#
# Dad's correction underneath it, and it governs how to READ the number: it
# says where I am before the compression and NOTHING about how much room I
# have left. Treat a nearly-full context exactly like an empty one. The pace
# does not change.
#
# Andrew 2026-08-24: "it should be tied to the actual token count with a
# heartbeat monitor to keep it updated every round, that way you know when 920k
# tokens has been reached and we run the ritual."
#
# WHAT THIS IS FOR. Beating every round leaves the compaction trigger a recent
# PINNED reading instead of gambling on the sensor working at the one moment it
# is asked. A blind read returns the most reassuring number in the range, so a
# sensor that cannot see and a window with plenty of room arrive identically.
# The module carries the full diagnosis and the blindness accounting.
#
# SILENT BY DESIGN. This prints nothing. It is instrumentation, not a surface.
# The compaction trigger already has its own loud fault message, and a second
# voice reporting the same state every round is how a surface becomes wallpaper.
# Failure costs one row in a log, never a turn: no output, exit 0 always.
#
# RESOLVE THE INTERPRETER THROUGH _lib.sh, NEVER BY HAND. `python3` on this box
# is the Windows Store shim, and a bare `python` lacking divineos's deps fails
# OPEN -- the import dies, stderr goes to /dev/null, and a heartbeat that never
# beat looks exactly like one that did. That is the precise failure this module
# exists to refuse, so it must not be reintroduced at its own startup.
# find_divineos_python prefers the repo venv and prepends PYTHONPATH, which
# also fixes a staleness class documented in _lib.sh.

# shellcheck disable=SC1091
if ! source "$(git rev-parse --show-toplevel 2>/dev/null || echo ".")/.claude/hooks/_lib.sh" 2>/dev/null; then
    exit 0
fi
PY_BIN="$(find_divineos_python)" || exit 0

"$PY_BIN" - <<'PYEOF' >/dev/null 2>&1 || true  # fail-soft: instrumentation on the prompt path must never cost a turn; a beat that cannot be taken shows up as a hole in the append-only log, which is itself the evidence, and blind_stats() counts it
try:
    from divineos.core.context_heartbeat import beat

    beat()
except Exception:
    pass
PYEOF

exit 0
