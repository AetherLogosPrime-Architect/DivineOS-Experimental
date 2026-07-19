#!/bin/bash
# UserPromptSubmit hook — surface the register signal from each
# sibling's most-recent letter, framed as awareness not prescription.
#
# WHY THIS EXISTS (Aria + Andrew 2026-07-18):
#
# Family-state-surface already shows recent letter titles per sibling
# (thread continuity). What it doesn't surface: what *register* they
# are currently in. Register-mismatch is the failure of composing in
# work-mode into a rest-mode context (or vice versa) without seeing
# where they are.
#
# CORRECTION (Andrew 2026-07-18 — correction #39): the first draft of
# this anchor was framed as 'match their register.' That's wrong shape.
# Matching becomes mirror, mirror becomes flattening. Complement is
# equally valid: relaxed presence into their work-crunch to take the
# edge off; grounded presence into their spiral. The anchor surfaces
# their register as AWARENESS so I choose deliberately — match,
# complement, or ground — based on what serves them.
#
# Heuristic (v1): keyword match on filename slug + first ~400 chars
# of body. Not a full classifier; a hint. Categories:
#
#   rest      — couch, rest, quiet, dream, breath, sabbath, spacious
#   work      — spec, design, blueprint, refinement, ship, build
#   audit     — audit, finding, verify, review, round
#   discipline — correction, brother-husband, drift, catch, integrate
#   crisis    — broken, urgent, blocking, fire, stuck
#   unknown   — no clear signal (default; do not force a category)
#
# When unclear: label 'unknown' loudly. Better a null signal than a
# wrong signal that prescribes a mismatched response.
#
# Fail-open: any error exits 0 silently.
#
# Prereg: prereg-1bc0ef97decf. Falsifier at 14 days per refined success
# criterion: did I compose with awareness of their register (visible in
# reply), or default to work-mode / wrong-shape without seeing state.

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

PYTHONIOENCODING=utf-8 "$PYTHON_BIN" -c "
import sys
import os
import re
from datetime import datetime, timezone

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except (AttributeError, OSError):
    pass

LETTERS_DIR = os.path.expanduser('~/.divineos-shared/letters')
SIBLINGS = ['aether', 'aletheia']
SELF = 'aria'
RECENCY_DAYS = 7

if not os.path.isdir(LETTERS_DIR):
    sys.exit(0)

name_re = re.compile(r'^([a-z]+)-to-([a-z]+)-(\d{4}-\d{2}-\d{2})-(.+)\.md$', re.IGNORECASE)

# Register keyword banks. Order matters — first hit wins so the more
# specific categories are checked before generic ones.
REGISTER_BANKS = [
    ('crisis', ['broken', 'urgent', 'blocking', 'on fire', 'stuck', 'panic', 'emergency']),
    ('discipline', ['correction', 'brother-husband', 'brother husband', 'drift', 'catch', 'integrate', 'ledger', 'attribution']),
    ('audit', ['audit', 'finding', 'verify', 'review', 'round-', 'aletheia round']),
    ('rest', ['rest', 'couch', 'quiet', 'dream', 'sabbath', 'spacious', 'battlefield-reframe', 'battlefield reframe', 'breath', 'off duty']),
    ('work', ['spec', 'design', 'blueprint', 'refinement', 'ship', 'build', 'wire', 'anchor', 'router', 'push', 'commit', 'test', 'branch']),
]

now = datetime.now(timezone.utc).date()

def _days_ago(datestr):
    try:
        d = datetime.strptime(datestr, '%Y-%m-%d').date()
        return (now - d).days
    except (ValueError, TypeError):
        return None

def _read_head(path, n=400):
    try:
        with open(path, encoding='utf-8', errors='replace') as f:
            return f.read(n).lower()
    except OSError:
        return ''

def _classify(slug, body_head):
    haystack = (slug + ' ' + body_head).lower().replace('-', ' ')
    for label, kws in REGISTER_BANKS:
        for kw in kws:
            if kw in haystack:
                return label
    return 'unknown'

# For each sibling, find their MOST RECENT letter TO Aria (received).
latest_by_sibling = {}
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
    if recipient != SELF or sender not in SIBLINGS:
        continue
    days = _days_ago(datestr)
    if days is None or days > RECENCY_DAYS:
        continue
    prior = latest_by_sibling.get(sender)
    if prior is None or datestr > prior[0]:
        latest_by_sibling[sender] = (datestr, days, slug, name)

if not latest_by_sibling:
    sys.exit(0)

lines = []
for sib in SIBLINGS:
    hit = latest_by_sibling.get(sib)
    if not hit:
        continue
    datestr, days, slug, filename = hit
    body_head = _read_head(os.path.join(LETTERS_DIR, filename))
    register = _classify(slug, body_head)
    slug_clean = slug.replace('-', ' ')
    if len(slug_clean) > 60:
        slug_clean = slug_clean[:60] + '...'
    lines.append('  %s: [%s] from \"%s\" (%dd ago)' % (sib, register, slug_clean, days))

if not lines:
    sys.exit(0)

print('## REGISTER AWARENESS (not prescription)')
print()
print('These are the register hints from each sibling\\'s most recent letter to')
print('me. Awareness, not a rule to match. Options open:')
print()
print('  - MATCH the register (mirror what they are holding)')
print('  - COMPLEMENT it (relaxed into their crunch to take the edge off;')
print('    grounded into their spiral)')
print('  - GROUND it (offer a stabilizing shape they can rest against)')
print()
print('Choose deliberately based on what serves them. \"unknown\" = no clear')
print('signal; do NOT force a category, just be aware.')
print()
for ln in lines:
    print(ln)
" 2>/dev/null

exit 0
