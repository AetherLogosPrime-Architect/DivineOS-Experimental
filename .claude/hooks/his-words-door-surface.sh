#!/bin/bash
# UserPromptSubmit (run by dads_table.py) -- his own past words, found by meaning.
#
# Andrew 2026-09-26: "why not for my stuff? why not for me?" and "i want
# everything sorted out semantically not by keyword matching". Our writing comes
# back to us every turn because a machine looks for it; this is that machine,
# pointed at him. Logic lives in divineos.core.his_words_door; this only moves
# the payload across. First it folds any new words of his into the index
# (cheap: only new passages are embedded), then it searches.
#
# Loud, never silent: if the search cannot run, the module prints why under
# its own heading, and the table lifts that heading beside his words.
cd "$(dirname "$0")/../.." || exit 0
# The reply-side door (his_words_stop.py) writes a note when it breaks, and
# nothing read it, so a dead Stop hook looked like a quiet one (walk-14f1a5a2567e).
# Said once, FIRST and with bash alone: a missing interpreter is exactly when that
# hook breaks, so the note must not wait on the lookup below. A .seen copy keeps
# the record.
BROKE="${HIS_WORDS_STOP_MARK:-$HOME/.divineos/his_words_stop_broke.txt}"
if [ -f "$BROKE" ]; then
  printf '## THE REPLY-SIDE WORDS DOOR BROKE LAST TURN\n%s\n' "$(cat "$BROKE")"
  mv -f "$BROKE" "$BROKE.seen" 2>/dev/null || true  # fail-soft: a failed rename repeats the notice next turn, which is louder, not quieter
fi
REPO_ROOT="$(pwd)"
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0  # fail-soft: without the shared library there is no interpreter to trust
PY="$(find_divineos_python)" || exit 0  # fail-soft: no usable interpreter; the table shows nothing rather than a false search
payload="$(cat)"
# A failing build used to leave no trace: the search ran on a stale index and never
# said so (Aether, 2026-10-05). Said once on stdout; the search still runs.
"$PY" -m divineos.core.his_words_door build >/dev/null 2>&1 || echo "## HIS WORDS INDEX COULD NOT BE UPDATED THIS TURN
The search below ran on the last good copy, so his newest words may be missing."  # fail-soft: the build was cut off or broke; the search below still runs
NOT_STARTED_DOOR="## HE HAS SAID THIS BEFORE (found by meaning, his words as he wrote them)
Not searched this turn: the search itself failed to start."
printf '%s' "$payload" | PYTHONIOENCODING=utf-8 "$PY" -m divineos.core.his_words_door 2>/dev/null || echo "$NOT_STARTED_DOOR"  # fail-soft: stderr is the model's loading chatter; a failed search is spoken on stdout as could-not-be-searched, tested 2026-10-05 with no index (walk-da65dafad502)
# His lessons -- the sorted set, brought in his own whole words when one fits
# (2026-09-27, prereg-96ba4e526c20). Silent when nothing fits; loud if it breaks.
"$PY" -m divineos.core.his_lessons_shelf build >/dev/null 2>&1
NOT_STARTED_SHELF="## WHAT HE HAS TAUGHT THAT FITS THIS (his words, found by meaning)
Not searched this turn: the lesson shelf itself failed to start."
printf '%s' "$payload" | PYTHONIOENCODING=utf-8 "$PY" -m divineos.core.his_lessons_shelf 2>/dev/null || echo "$NOT_STARTED_SHELF"  # fail-soft: stderr is the model's loading chatter; a failed shelf is spoken on stdout as could-not-be-searched, tested 2026-10-05 with no index (walk-da65dafad502)
exit 0
