#!/bin/bash
# Inert-fix surface — once per session, ask whether the fixes we believe are
# deployed are actually in effect.
#
# Two instances on 2026-08-18, hours apart, both found by accident:
#   - the whose-window field for the timing log lived in 2 of 8 loadable
#     copies of _lib.sh; every window on one side of the house loaded a copy
#     without it and wrote anonymous rows while looking fine doing it
#   - the stream-idle timeout was written into settings AFTER 14 of 15 live
#     windows had started and read the old value
#
# Both were correct, deployed, and inert. Review asks whether the work was
# written. Tests ask whether it works. Neither asks whether the thing doing
# the loading loaded it. This does.
#
# Runs as a child of session-init-once.sh rather than being registered on
# SessionStart. SessionStart carries zero hooks in every settings file on this
# machine -- deliberately, because of a Windows deadlock in that path -- so a
# check registered there would never fire, which is precisely the defect this
# hook exists to catch.
#
# Fail-open in every direction. It reports; it never blocks and never repairs.
# Repair would mean editing a library that live windows are sourcing right
# now, and one bad line there takes out every hook in every window at once.
# --quiet keeps a healthy session silent, so the cost of carrying this is zero
# until the day it has something to say.

set -u

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || true  # fail-soft: this hook only reports; a library that will not source must not cost the operator a prompt

CHECK="$REPO_ROOT/scripts/check_inert_fixes.py"
[ -f "$CHECK" ] || exit 0

# The check is already --warn-only, so a non-zero here means python itself
# failed rather than an invariant being violated. That is worth seeing, so it
# goes to the liveness log rather than into a swallow.
if ! OUT="$(python "$CHECK" --quiet --warn-only 2>&1)"; then
    LOG="${HOME:-/tmp}/.divineos/hook-liveness.log"
    mkdir -p "$(dirname "$LOG")" 2>/dev/null || true  # fail-soft: cannot create the log dir, and refusing to run over that would be worse than the missing line
    TS="$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || echo unknown)"  # fail-soft: a date call that cannot produce a timestamp must still let the liveness line be written, because the line existing at all is the signal
    printf '{"ts":"%s","hook":"inert-fix-surface.sh","reason":"check_failed_to_run","detail":"%s"}\n' \
        "$TS" \
        "$(printf '%s' "$OUT" | tr -d '"' | tr '\n' ' ' | cut -c1-300)" \
        >> "$LOG" 2>/dev/null || true  # fail-soft: an unwritable liveness log must not turn a reporting hook into a blocking one
    exit 0
fi
[ -n "$OUT" ] && printf '%s\n' "$OUT"

exit 0
