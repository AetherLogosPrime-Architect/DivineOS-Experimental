#!/bin/bash
# Stop -- runs his_words_stop.py (his own past words, brought to my reply before
# it reaches him) with the house's own interpreter finder. Bare `python` here is
# whichever tree installed last, which is not necessarily this one.
#
# Loud, never silent (walk-14f1a5a2567e): if no interpreter can be found, say so
# in the same note the hook itself writes when it breaks; his-words-door-surface.sh
# reads that note at the table on the next turn.
cd "$(dirname "$0")/../.." || exit 0
MARK="${HIS_WORDS_STOP_MARK:-$HOME/.divineos/his_words_stop_broke.txt}"
source .claude/hooks/_lib.sh 2>/dev/null || {
  mkdir -p "$(dirname "$MARK")" 2>/dev/null
  echo "his_words_stop could not start: the shared hook library did not load" >"$MARK" 2>/dev/null
  exit 0 # fail-soft: the note above is the loud part, and a Stop hook must never take the reply down
}
PY="$(find_divineos_python)" || {
  mkdir -p "$(dirname "$MARK")" 2>/dev/null
  echo "his_words_stop could not start: no usable interpreter found" >"$MARK" 2>/dev/null
  exit 0 # fail-soft: the note above is the loud part, and a Stop hook must never take the reply down
}
exec "$PY" .claude/hooks/his_words_stop.py
