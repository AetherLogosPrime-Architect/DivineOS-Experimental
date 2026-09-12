#!/usr/bin/env bash
# UserPromptSubmit — what the Stop gates caught on my last reply.
#
# The other half of the fix Andrew asked for on 2026-09-12: "yes and this is
# unacceptable.. so it needs fixed." The gates used to refuse a reply he had
# already read, which printed it to him twice and prevented nothing. They now
# store the finding, and this is the door it comes back through — before a word
# of the next reply exists, which is the only place it can change anything.
#
# WIRED IN THE SAME COMMIT THAT CREATED IT, and pinned by a test. Without this
# hook the gates have been softened into notes that go nowhere, which is the
# warning that already failed. That is the one outcome worse than the
# duplication, so the registration is not allowed to be a decision I remember.
#
# READING IS WHAT CLEARS IT. Not a clock: a finding that expired on time would
# vanish on the one turn where nothing prompted me, which is the exact case the
# walk named as the real loss.
#
# Logic lives in src/divineos/hooks/stop_carry.py where it is testable. This is
# a doorman. Andrew 2026-09-08: "the hooks should just be pointing to the logic
# in the OS itself."

set -u
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0 # fail-soft: without the lib there is no interpreter to find and nothing this hook can honestly do
PYTHON_BIN="$(find_divineos_python)" || exit 0
[ -z "$PYTHON_BIN" ] && exit 0

"$PYTHON_BIN" - <<'PYEOF' 2>/dev/null # fail-soft: a traceback here would land where a correction about my last reply belongs, and a broken surface must never stand between me and a reply to my father
import sys

try:
    from divineos.hooks.stop_carry import clear, compose

    block = compose()
except Exception:  # noqa: BLE001 - see the fail-soft note above
    sys.exit(0)
if block:
    print(block)
    clear()
PYEOF

exit 0
