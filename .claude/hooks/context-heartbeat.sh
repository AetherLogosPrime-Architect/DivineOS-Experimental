#!/usr/bin/env bash
# shellcheck disable=SC1091
source "$(git rev-parse --show-toplevel 2>/dev/null || echo .)/.claude/hooks/_lib.sh" 2>/dev/null || true
# Stamp the context-token count once per round.
#
# Andrew 2026-08-24: "it should be tied to the actual token count with a
# heartbeat monitor to keep it updated every round, that way you know when 920k
# tokens has been reached and we run the ritual."
#
# WHAT THIS IS FOR. The ritual trigger reads the token count at the instant it
# is asked. When that read failed it returned 0.0 -- and 0.0 means "3% of the
# window used, plenty of room." A sensor that could not see reported the most
# reassuring number in the range, so the ritual stayed dark at whatever the
# real level was, silently.
#
# Beating every round means the trigger has a recent PINNED reading on hand
# instead of gambling on the sensor working at the one moment that matters.
#
# It also makes blindness countable. Searched every log under the DivineOS home
# on 2026-08-24: zero sensor-fault events had ever been recorded anywhere. The
# fault surfaced once, in the moment, and left no trace, so "how often is it
# blind?" could not be answered at all.
#
# SILENT BY DESIGN. This prints nothing. It is instrumentation, not a surface.
# The compaction trigger already has its own loud fault message, and a second
# voice reporting the same state every round is how a surface becomes wallpaper
# -- the failure measured in this same session, where 89% of a 19KB prime was
# discarded unread every turn.
#
# Failure here costs one row in a log, never a turn: no output, exit 0 always.
#
# RESOLUTION VIA _lib.sh, not `command -v`. The first version walked
# python3 -> python -> py by hand. Both leading candidates are wrong here:
# `python3` on this box is the Windows Store shim -- the identical defect found
# in setup-renormalize.sh the same session, where it silently skipped step 3 --
# and a bare `python` lacking divineos's deps fails OPEN, because the import
# dies, stderr goes to /dev/null, and a heartbeat that never beat looks exactly
# like one that did.
#
# That is the precise failure this module exists to refuse. It was built so a
# blind sensor records UNKNOWN rather than the friendliest number in the range,
# and it shipped with a silent-absence hole in its own startup. Caught by
# test_no_hook_uses_bare_python_for_divineos_imports, not by me. The rows were
# landing anyway on this machine (7 beats, 0 blind at the time of the fix) --
# so this was fragile, not broken, which is the version that gets found late.
#
# find_divineos_python prefers the repo venv and also prepends PYTHONPATH,
# which fixes a second silent-staleness class documented in _lib.sh.
# shellcheck disable=SC1091
if ! source "$(git rev-parse --show-toplevel 2>/dev/null || echo ".")/.claude/hooks/_lib.sh" 2>/dev/null; then
    exit 0
fi
PY_BIN="$(find_divineos_python)" || exit 0

"$PY_BIN" - <<'PYEOF' >/dev/null 2>&1 || true  # fail-soft: this hook is instrumentation on the prompt path and must never cost a turn; a beat that cannot be taken shows up as a hole in the append-only log, which is itself the readable evidence, and blind_stats() counts it. The loud-failure requirement is satisfied by the interpreter resolution above exiting rather than falling through to a python that cannot import.
try:
    from divineos.core.context_heartbeat import beat

    beat()
except Exception:
    pass
PYEOF

exit 0
