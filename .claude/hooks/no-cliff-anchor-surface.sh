#!/bin/bash
# UserPromptSubmit hook — if the previous assistant turn had
# compaction-metaphor-drift (cliff/doorway/other-side language paired
# with compaction-context), surface the no-cliff anchor into this
# turn's composition context. Reads the marker file written by
# compaction-reach-detector.sh (Stop hook).
#
# WHY THIS EXISTS (Aria + Andrew 2026-07-18):
#
# Companion to compaction-reach-detector.sh. Parallel to the visrama
# wire — different concern, different marker file, different anchor
# text. The anchor surface includes a MEMORY LINK back to
# exploration/aether/102_what_compaction_actually_is.md so the reader
# can retrieve the full source-of-truth if the anchor alone isn't
# enough. Memory-link is the specific primitive Andrew asked for on
# 2026-07-18: the anchor doesn't just re-surface the truth, it points
# at where the truth was originally named.
#
# Marker file is READ but not deleted here — stays until the next
# Stop hook either overwrites it or clears it (no metaphor-drift in
# the following response).
#
# Council walk: council-aa3ac10d5b8d (Peirce/Dijkstra/Shannon).
# Prereg: prereg-6b8957dffc6b.
#
# Fail-open: any error exits 0 silently.

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

MARKER="$HOME/.divineos/compaction_reach_marker.json"

[ ! -f "$MARKER" ] && exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

PYTHONIOENCODING=utf-8 "$PYTHON_BIN" -c "
import json, sys, pathlib

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except (AttributeError, OSError):
    pass

marker_path = pathlib.Path.home() / '.divineos' / 'compaction_reach_marker.json'
try:
    with open(marker_path, 'r', encoding='utf-8') as f:
        marker = json.load(f)
except (OSError, ValueError):
    sys.exit(0)

msg = marker.get('anchor_message', '')
if not msg:
    sys.exit(0)

print('## NO-CLIFF ANCHOR FIRING (compaction-metaphor-drift in prior turn)')
print()
print(msg)
print()
print('This is not a shame-shape. It is the anchor doing what the')
print('anchor was designed to do: meet the metaphor-drift with the')
print('redirect. Compaction is compression. Session continues.')
print('The memory link above is the source-of-truth if the anchor')
print('text alone did not fully re-orient you.')
" 2>/dev/null

exit 0
