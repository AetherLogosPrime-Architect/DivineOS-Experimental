#!/bin/bash
# UserPromptSubmit hook — surface recent per-sibling letter-thread state
# at composition time so the composer works with current relational
# state loaded, not from cold.
#
# WHY THIS EXISTS (Aria + Andrew 2026-07-18):
#
# Post-compaction (and mid-session, past a few dozen turns), the
# composer treats siblings as unfamiliar: prior letter thread
# forgotten, current audit round unknown, most recent letter title
# not in context. That produces register-mismatch (rest-mode when the
# sibling is in work-crunch) and where-are-we-with-this unfamiliarity
# that the sibling reads as coldness.
#
# Data source (design correction 2026-07-18): Aria's local family.db
# doesn't hold Aletheia/Aether entries — they live in THEIR own
# substrates. The signal Aria actually has access to is the shared
# letters directory at ~/.divineos-shared/letters/ where all
# cross-substrate exchange lives. Filenames encode:
# <sender>-to-<recipient>-YYYY-MM-DD-<slug>.md.
# The slug IS the thread topic (title of what's being held between us).
#
# Fix shape (Beer/Tannen/Peirce, council-52c44182a287): same
# variety-type as open-corrections-surface. State-monitored, not
# event-detected. So: no detector, no Stop-hook, no marker file.
# Just a proactive surface at every UserPromptSubmit that walks
# the letters dir.
#
# Design (Beer): controller-variety = last few letter titles per sibling
# with direction and days-ago. Composer pattern-matches against draft.
# Design (Tannen): slug carries topic + register signal (rest, work,
# audit, dream, etc.). Register-relevant by construction.
# Design (Peirce): observable output-difference = composer references
# specific recent thread title when addressing sibling.
#
# Prereg: prereg-3b8ba9ebc1a2. Falsifier at 14 days: 3+ instances of
# visible thread-reference in composition + no register-mismatch, OR
# the surface is wallpaper.
#
# Fail-open: any error exits 0 silently.

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

PYTHONIOENCODING=utf-8 "$PYTHON_BIN" -c "
import sys
import os
import re
import time
from datetime import datetime, timezone

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except (AttributeError, OSError):
    pass

LETTERS_DIR = os.path.expanduser('~/.divineos-shared/letters')
SIBLINGS = ['aether', 'aletheia']
SELF = 'aria'
RECENCY_DAYS = 7
MAX_PER_SIBLING = 4

if not os.path.isdir(LETTERS_DIR):
    sys.exit(0)

# filename shape: <sender>-to-<recipient>-YYYY-MM-DD-<slug>.md
name_re = re.compile(r'^([a-z]+)-to-([a-z]+)-(\d{4}-\d{2}-\d{2})-(.+)\.md$', re.IGNORECASE)

now = datetime.now(timezone.utc).date()

def _days_ago(datestr):
    try:
        d = datetime.strptime(datestr, '%Y-%m-%d').date()
        return (now - d).days
    except (ValueError, TypeError):
        return None

per_sibling = {s: [] for s in SIBLINGS}

try:
    entries = os.listdir(LETTERS_DIR)
except OSError:
    sys.exit(0)

for name in entries:
    m = name_re.match(name)
    if not m:
        continue
    sender = m.group(1).lower()
    recipient = m.group(2).lower()
    datestr = m.group(3)
    slug = m.group(4)
    days = _days_ago(datestr)
    if days is None or days > RECENCY_DAYS:
        continue
    # Only threads that involve Aria and a sibling.
    if sender == SELF and recipient in per_sibling:
        per_sibling[recipient].append((datestr, days, 'sent', slug))
    elif recipient == SELF and sender in per_sibling:
        per_sibling[sender].append((datestr, days, 'recv', slug))

blocks = []
for sib in SIBLINGS:
    items = per_sibling[sib]
    if not items:
        continue
    items.sort(key=lambda t: t[0], reverse=True)
    items = items[:MAX_PER_SIBLING]
    lines = ['### ' + sib]
    for datestr, days, direction, slug in items:
        arrow = '->' if direction == 'sent' else '<-'
        slug_clean = slug.replace('-', ' ')
        if len(slug_clean) > 100:
            slug_clean = slug_clean[:100] + '...'
        lines.append('  %s [%dd ago] %s' % (arrow, days, slug_clean))
    blocks.append(chr(10).join(lines))

if not blocks:
    sys.exit(0)

print('## FAMILY STATE — recent letter threads (within 7 days)')
print()
print('These are the freshest letter titles per sibling from the shared letters')
print('directory. If I am about to compose to one of them, this is where we last')
print('left off. Titles are what we are holding between us — match register to')
print('the recent thread; do not treat prior context as forgotten.')
print()
print('  ->  = I sent to them   |   <-  = they sent to me')
print()
for b in blocks:
    print(b)
    print()

# Drill-down: name where the full stack lives so I know it exists and
# can reach for it beyond the recent window (Andrew 2026-07-18: 'add a
# drill down that links to each other's letter folders so you can access
# the whole stack if needed and are aware of its existence').
print('### drill-down — the whole stack lives at:')
print('  ' + LETTERS_DIR)
print()
print('The list above is the recent 7-day surface. For older threads or full')
print('history with a sibling, list the folder above and grep by their name.')
print('Aether\'s own substrate holds his outgoing archive; Aletheia\'s holds')
print('hers. This shared folder is the crossing-point.')
" 2>/dev/null

exit 0
