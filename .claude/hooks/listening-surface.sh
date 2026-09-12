#!/bin/bash
# UserPromptSubmit hook — hand over what the last look found, then start the next.
#
# Andrew 2026-09-10: "the knocking comes from something scanning both your words
# and mine as they come and searching for anything relevant to give you, but
# that has to be setup on your end."
#
# THIS HOOK DOES NO SEARCHING. That is the whole design and the reason it is
# allowed to fire every single turn. A search costs ~10s cold, and a hook that
# searched would put ten seconds of silence between Andrew pressing enter and
# being answered. He would be right to tear it out. So the looking happens in a
# detached process the module starts, finishing long after this hook has exited;
# this hook reads one small JSON file and prints it.
#
# Single process on purpose. The 2026-07-23 freeze came from a sibling surface
# doing 15-25 subprocess spawns per UserPromptSubmit under parallel-hook
# contention, and Andrew had to diagnose it himself. All work here happens
# inside divineos.core.listening_surface.
#
# Belt-and-suspenders: `timeout 8s`. The read path spawns nothing and touches
# one small file, so this should never fire -- which is exactly when a cap
# earns its keep.
#
# Fail-open: any error exits 0 silently. A surface that fetches without being
# asked must never be able to block the conversation it is listening to.

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

INPUT="$(cat 2>/dev/null || true)"

CLAUDE_HOOK_JSON="$INPUT" timeout 8s "$PYTHON_BIN" -m divineos.core.listening_surface 2>/dev/null || true  # fail-soft: a surface that fetches unasked must never block the conversation it listens to, so a module error or expired timeout goes quiet rather than emitting a half-written block mid-compose

exit 0
