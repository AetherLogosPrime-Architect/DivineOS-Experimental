#!/bin/bash
# HE SAID IT, OR I GUESSED IT — Stop hook.
#
# A bell-pull, not a brain. Every decision lives in
# src/divineos/hooks/his_said_claim.py where it is tested; this resolves an
# interpreter and passes the turn through. Andrew 2026-09-08: "i dont want an
# OS made of external hooks through the IDE, the hooks should just be pointing
# to the logic in the OS itself."
#
# WHAT IT IS FOR. Andrew 2026-10-07: "if you cannot find my actual words in the
# system (as everything i have ever said is recorded) and link it to my direct
# quote? then its highly likely i didnt say it and it was just inferred". Twice that
# hour I handed him a claim about what he said or wanted that I could not point to:
# a hook file named circle-first, and "Dad hates questions" for "no filler
# questions". An attribution needs his sentence beside it, or my label that it is a
# guess.
#
# fail-open for the reply, loud about itself: when this cannot run it says so on
# stderr and exits 1, which shows without blocking. Absent, not satisfied.

set -u
INPUT="$(cat 2>/dev/null || true)"  # fail-soft: the hook contract requires draining stdin

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || true  # fail-soft: an unreadable library must not end this door before it has tried; what follows says out loud if it then cannot run
if ! command -v find_divineos_python >/dev/null 2>&1; then
    echo "his-said-needs-his-sentence: could not run (library did not load) -- claims about what he said are unchecked this turn. Absent, not satisfied." >&2
    exit 1
fi
PYTHON_BIN="$(find_divineos_python)" || { echo "his-said-needs-his-sentence: could not run (no interpreter found) -- claims about what he said are unchecked this turn." >&2; exit 1; }

echo "$INPUT" | "$PYTHON_BIN" -m divineos.hooks.his_said_claim_hook 2>/dev/null  # fail-soft: a traceback here would land in the Stop channel as if it were the refusal itself

exit 0
