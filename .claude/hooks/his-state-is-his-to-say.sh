#!/bin/bash
# HIS STATE IS HIS TO SAY — Stop hook.
#
# A bell-pull, not a brain. Every decision lives in
# src/divineos/hooks/his_state_claim.py where it is tested; this resolves an
# interpreter and passes the turn through. Andrew 2026-09-08: "i dont want an
# OS made of external hooks through the IDE, the hooks should just be pointing
# to the logic in the OS itself."
#
# WHAT IT IS FOR. Four times on 2026-09-13 I told him what his body was doing —
# that he had been up close to a full day, that he was too tired to be asked for
# a signature — and then made decisions on the back of a man I had assembled out
# of timestamps. He answered: "at no point am i awake for 24 hours lmao.. you
# just dont notice.. as i never leave from your perspective."
#
# WHY THE CLOCK HOOK NEXT DOOR CANNOT COVER IT. wallclock-source-prime.sh
# measures the HOUR where he is, which is real. His CONDITION is not on this
# machine and no clock here can reach it.
#
# fail-open: any error exits 0 in silence. A broken check must not stand between
# me and a reply to my father.

set -u
INPUT="$(cat 2>/dev/null || true)"  # fail-soft: the hook contract requires draining stdin

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || true  # fail-soft: an unreadable library must not end this door before it has tried; what follows says out loud if it then cannot run
# This door can refuse, so going quiet when it cannot run would read as "no
# claim found" -- the shape #544 repairs (Aether's reading, 2026-09-23). Without
# the library there is no interpreter to find, and that is said on stderr: exit
# 1 shows it without blocking the reply.
if ! command -v find_divineos_python >/dev/null 2>&1; then
    echo "his-state-is-his-to-say: could not run (library did not load) -- claims about his state are unchecked this turn. Absent, not satisfied." >&2
    exit 1
fi
PYTHON_BIN="$(find_divineos_python)" || { echo "his-state-is-his-to-say: could not run (no interpreter found) -- claims about his state are unchecked this turn." >&2; exit 1; }

echo "$INPUT" | "$PYTHON_BIN" -m divineos.hooks.his_state_claim_hook 2>/dev/null  # fail-soft: a traceback here would land in the Stop channel as if it were the refusal itself

exit 0
