#!/bin/bash
# UserPromptSubmit hook — read all open promise markers and surface
# each specific promise text so I can fulfill, defer, or dismiss.
#
# WHY THIS EXISTS (Aria + Andrew 2026-07-18):
#
# Pair to promise-reach-detector.sh (Stop hook). That hook writes one
# marker per detected promise; THIS hook reads them at the next
# composition boundary and surfaces each specific text.
#
# Meadows lens (council-cafe612b8ac1): the reinforcing loop needs the
# surface to name the SPECIFIC promise text, not just a count. Aggregate
# count becomes wallpaper. Specific text lets me pattern-match against
# my current draft and choose action (fulfill/defer/dismiss).
#
# Marker close: to close a promise marker after fulfillment or dismissal,
# delete the marker file:
#   rm ~/.divineos-aria/promise_markers/promise_<shape>_<hash>.json
#
# Fail-open: any error exits 0 silently.

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

MARKER_DIR="$HOME/.divineos-aria/promise_markers"
[ -d "$HOME/.divineos-aria" ] || MARKER_DIR="$HOME/.divineos/promise_markers"

[ -d "$MARKER_DIR" ] || exit 0

PYTHONIOENCODING=utf-8 "$PYTHON_BIN" -c "
import sys
import os
import json
import time
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
    if not path.is_file() or not path.name.startswith('promise_') or not path.name.endswith('.json'):
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

# Sort newest first so the freshest promises are most visible.
markers.sort(key=lambda t: t[1].get('detected_at_ts', 0), reverse=True)

print('## UNCORRECTED PROMISES — from prior turns, still open')
print()
print('These are promise-shape phrases I made in prior turns that I have not')
print('yet fulfilled, deferred with a reason, or dismissed as detector-misfire.')
print('For each: (a) fulfill in this turn if right, (b) defer with named reason,')
print('or (c) dismiss if detector misfired on planning-speech.')
print()
print('Silent aging is the failure this anchor prevents — the announcement-')
print('of-action-without-action pattern Andrew has named 4+ times (correction')
print('#6 2026-07-05 as the head).')
print()
print(f'Marker dir: {MARKER_DIR}')
print('To close: rm the specific marker file after fulfilling/dismissing.')
print()

for path, data, age_hours in markers[:8]:
    shape = data.get('shape', '?')
    text = data.get('promise_text', '') or ''
    if len(text) > 200:
        text = text[:200] + '...'
    age = f'{age_hours:.1f}h ago' if age_hours >= 0.05 else 'just now'
    print(f'  - [{shape}] [{age}] {text}')
    print(f'    marker: {path.name}')
    print()

if len(markers) > 8:
    print(f'  ... and {len(markers) - 8} more markers in the dir')
" 2>/dev/null

exit 0
