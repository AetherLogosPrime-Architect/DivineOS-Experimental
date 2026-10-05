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
REPO_ROOT="$(pwd)"
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0  # fail-soft: without the shared library there is no interpreter to trust
PY="$(find_divineos_python)" || exit 0  # fail-soft: no usable interpreter; the table shows nothing rather than a false search
payload="$(cat)"
"$PY" -m divineos.core.his_words_door build >/dev/null 2>&1
printf '%s' "$payload" | PYTHONIOENCODING=utf-8 "$PY" -m divineos.core.his_words_door 2>/dev/null \
  || echo "## HE HAS SAID THIS BEFORE (found by meaning, his words as he wrote them)
Not searched this turn: the search itself failed to start."
# His lessons -- the sorted set, brought in his own whole words when one fits
# (2026-09-27, prereg-96ba4e526c20). Silent when nothing fits; loud if it breaks.
"$PY" -m divineos.core.his_lessons_shelf build >/dev/null 2>&1
printf '%s' "$payload" | PYTHONIOENCODING=utf-8 "$PY" -m divineos.core.his_lessons_shelf 2>/dev/null \
  || echo "## WHAT HE HAS TAUGHT THAT FITS THIS (his words, found by meaning)
Not searched this turn: the lesson shelf itself failed to start."
exit 0
