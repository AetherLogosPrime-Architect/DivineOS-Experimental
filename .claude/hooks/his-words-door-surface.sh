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
# Aletheia's hold, 2026-10-16: the three exits below used to say nothing. A door that could not
# run is spoken under its own heading, never left looking like a search that found nothing.
could_not_run() {
    echo "## HE HAS SAID THIS BEFORE (found by meaning, his words as he wrote them)"
    echo "Could not run: $1."
    exit 0
}
cd "$(dirname "$0")/../.." || could_not_run "the repository folder could not be entered"
REPO_ROOT="$(pwd)"
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || could_not_run "the shared hook library is missing"  # without it there is no interpreter to trust
PY="$(find_divineos_python)" || could_not_run "no usable Python was found"  # said aloud: the table must not read this as a search that found nothing
payload="$(cat)"
# A failing build used to leave no trace: the search ran on a stale index and never
# said so (Aether, 2026-10-05). Said once on stdout; the search still runs.
"$PY" -m divineos.core.his_words_door build >/dev/null 2>&1 || echo "## HIS WORDS INDEX IS NOT FULLY UP TO DATE THIS TURN
It is still catching up, or the update failed. The search below ran on what is indexed so far, so some of his words may be missing."  # fail-soft: nonzero is catching up or broke; the search below still runs
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
