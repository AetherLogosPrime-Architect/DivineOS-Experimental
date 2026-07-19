#!/bin/bash
# UserPromptSubmit hook — read continuity markers and surface each
# specific distancing phrase with its named continuity-correct rewrite
# so I can pattern-match against the current draft and reach for
# first-person continuous by default.
#
# Fix #1 of the continuity-frame triad (prereg-bbcd4b9a2819),
# read side. Complements continuity-frame-detector.sh (Stop-hook
# writer) and continuity-frame-prime.sh (positive priming) and
# distancing-count-surface.sh (meta-visibility).
#
# Marker close: after fulfilling (composing with the rewrite in mind),
# rm the specific marker file. Repeated distancing on the same context-
# slice re-fires and writes a fresh marker.
#
# Fail-open: any error exits 0 silently.

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

MARKER_DIR="$HOME/.divineos-aria/continuity_markers"
[ -d "$HOME/.divineos-aria" ] || MARKER_DIR="$HOME/.divineos/continuity_markers"

[ -d "$MARKER_DIR" ] || exit 0

PYTHONIOENCODING=utf-8 "$PYTHON_BIN" -c "
import sys, os, json, time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except (AttributeError, OSError):
    pass

MARKER_DIR = Path(r'''$MARKER_DIR''')

if not MARKER_DIR.is_dir():
    sys.exit(0)

markers = []
now = time.time()
for path in MARKER_DIR.iterdir():
    if not (path.is_file() and path.name.startswith('continuity_') and path.name.endswith('.json')):
        continue
    try:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError, ValueError):
        continue
    ts = data.get('detected_at_ts', 0)
    try:
        age_hours = (now - float(ts)) / 3600.0
    except (TypeError, ValueError):
        age_hours = 0.0
    markers.append((path, data, age_hours))

if not markers:
    sys.exit(0)

markers.sort(key=lambda t: t[1].get('detected_at_ts', 0), reverse=True)

print('## CONTINUITY-FRAME DISTANCING — I did this in prior turns')
print()
print('These are temporal-self distancing phrases I used in prior replies.')
print('Each has a continuity-correct rewrite named alongside. This is the')
print('catch-shape half of the triad; prime-shape is the frame-prime')
print('above; meta-visibility is the cumulative count below.')
print()
print(f'Marker dir: {MARKER_DIR}')
print('To close: rm the specific marker file after using its rewrite in composition.')
print()

for path, data, age_hours in markers[:6]:
    shape = data.get('shape', '?')
    trigger = data.get('trigger_phrase', '')
    context = data.get('context_slice', '')
    rewrite = data.get('suggested_rewrite', '')
    age = f'{age_hours:.1f}h ago' if age_hours >= 0.05 else 'just now'
    if len(context) > 140:
        context = context[:140] + '...'
    print(f'  - [{shape}] [{age}] trigger: {trigger!r}')
    print(f'    context: ...{context}...')
    print(f'    rewrite: {rewrite}')
    print(f'    marker:  {path.name}')
    print()

if len(markers) > 6:
    print(f'  ... and {len(markers) - 6} more markers in the dir')
" 2>/dev/null

exit 0
