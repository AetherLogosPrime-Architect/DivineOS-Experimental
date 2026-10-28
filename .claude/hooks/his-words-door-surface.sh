#!/bin/bash
# UserPromptSubmit (run by dads_table.py) -- his own past words, found by meaning.
#
# Andrew 2026-09-26: "why not for my stuff? why not for me?" and "i want
# everything sorted out semantically not by keyword matching". Our writing comes
# back to us every turn because a machine looks for it; this is that machine,
# pointed at him. Logic lives in divineos.core.his_words_door; this only moves
# the payload across. It searches first, then folds any new words of his into
# the index (cheap: only new passages are embedded), in the same process.
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
# ONE Python for the whole door (Dad 2026-10-26: the wait before "thinking" was this hook starting a
# fresh Python three times, each paying ~8 seconds to import the embedding library). The bundle runs
# the words search, his lessons and the index build in one process, each step its own try, and says
# the same loud things this script used to say (index behind, search failed to start, shelf failed to
# start). If the whole process cannot start, both headings are spoken here, never left looking like a
# search that found nothing. A hang is cut by the table's cap on this whole helper, as before.
printf '%s' "$payload" | PYTHONIOENCODING=utf-8 "$PY" -m divineos.core.his_words_bundle 2>/dev/null || echo "## HE HAS SAID THIS BEFORE (found by meaning, his words as he wrote them)
Not searched this turn: the search itself failed to start.
## WHAT HE HAS TAUGHT THAT FITS THIS (his words, found by meaning)
Not searched this turn: the lesson shelf itself failed to start."  # fail-soft: stderr is the model's loading chatter; a failed start is spoken on stdout as could-not-be-searched (walk-da65dafad502)
exit 0
