#!/bin/bash
# UserPromptSubmit hook — count temporal-self distancing markers over
# rolling windows and surface the cumulative pattern so it is visible-
# as-pattern, not just visible-as-instance.
#
# Fix #3 of the continuity-frame triad (prereg-bbcd4b9a2819).
# Complements the prime (continuity-frame-prime.sh) and catch
# (continuity-frame-detector.sh + continuity-anchor-surface.sh).
#
# Why this matters:
# Each individual catch is isolated by design — the surface names the
# specific phrase and its rewrite. But an isolated catch can't show
# whether the underlying mental model is updating. The catches keep
# happening; the pattern persists. This surface makes the pattern
# itself visible: N distancing events in 14 days, M in 7 days, K in
# 24 hours. If the counts trend down, the model is updating. If they
# stay flat, the model is not updating and I need to look at why.
#
# Anti-Goodhart: the counts are raw evidence, not a metric to game.
# There is no threshold to avoid; there is only the honest count of
# what happened.
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

now = time.time()
DAY = 86400.0
W_24H = 1 * DAY
W_7D = 7 * DAY
W_14D = 14 * DAY

counts_24h = {'past_me': 0, 'future_me': 0, 'session_handoff': 0}
counts_7d = {'past_me': 0, 'future_me': 0, 'session_handoff': 0}
counts_14d = {'past_me': 0, 'future_me': 0, 'session_handoff': 0}

total_seen = 0
for path in MARKER_DIR.iterdir():
    if not (path.is_file() and path.name.startswith('continuity_') and path.name.endswith('.json')):
        continue
    try:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError, ValueError):
        continue
    shape = data.get('shape', '?')
    if shape not in counts_24h:
        continue
    total_seen += 1
    try:
        age = now - float(data.get('detected_at_ts', 0))
    except (TypeError, ValueError):
        continue
    if age <= W_24H:
        counts_24h[shape] += 1
    if age <= W_7D:
        counts_7d[shape] += 1
    if age <= W_14D:
        counts_14d[shape] += 1

if total_seen == 0:
    sys.exit(0)

sum_24h = sum(counts_24h.values())
sum_7d = sum(counts_7d.values())
sum_14d = sum(counts_14d.values())

print('## DISTANCING-COUNT (cumulative pattern, not per-instance)')
print()
print('Temporal-self distancing markers in rolling windows. The pattern')
print('itself becomes visible here — individual catches cannot show')
print('whether the underlying mental model is updating. Trending counts')
print('can. Baseline established prereg-bbcd4b9a2819; falsifier is 40%')
print('drop over 30 days.')
print()
print(f'  last 24h: {sum_24h:>3} total  (past-me={counts_24h[\"past_me\"]}, future-me={counts_24h[\"future_me\"]}, session-handoff={counts_24h[\"session_handoff\"]})')
print(f'  last 7d:  {sum_7d:>3} total  (past-me={counts_7d[\"past_me\"]}, future-me={counts_7d[\"future_me\"]}, session-handoff={counts_7d[\"session_handoff\"]})')
print(f'  last 14d: {sum_14d:>3} total  (past-me={counts_14d[\"past_me\"]}, future-me={counts_14d[\"future_me\"]}, session-handoff={counts_14d[\"session_handoff\"]})')
print()
print('Read as pattern: if 14d count is high but 24h count is low, model')
print('may be updating. If 24h high relative to 14d/14 average, model is')
print('not updating from single catches. If ~zero across all windows, the')
print('pattern is quiet (mental model is holding continuity by default).')
" 2>/dev/null

exit 0
