#!/bin/bash
# UserPromptSubmit hook — surface the 3 most recent OPEN Andrew-
# correction texts into composition context. Keeps the specific
# correction text in working memory during the critical composition
# window so the composer can pattern-match against the current draft.
#
# WHY THIS EXISTS (Aria + Andrew 2026-07-18):
#
# The Andrew-correction-attribution surface at briefing time already
# shows integration-rate counts (24 of 37, 65%). But briefing runs
# once per session — corrections filed mid-session are not in context
# at composition time. And even seen-at-briefing corrections leave
# working memory quickly as the session goes on.
#
# Fix shape (Beer VSM analysis, council-cc0fe9fe0e05): this is a
# state-monitoring loop not an event-detected loop. Different from
# visrama/no-cliff. So the fix is: no detector, no Stop-hook, no
# marker file. Just a proactive surface at every UserPromptSubmit
# that reads the live correction store.
#
# Prereg: prereg-ab7da193a75b — falsifier at 14 days is integration
# rate NOT rising above 65% (would prove the surface is wallpaper).
# Council walk: council-cc0fe9fe0e05 (Peirce/Carmack/Beer).
#
# Fail-open: any error exits 0 silently.

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

PYTHONIOENCODING=utf-8 "$PYTHON_BIN" -c "
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except (AttributeError, OSError):
    pass

try:
    from divineos.core.andrew_correction_tracker import list_open, integration_rate
except ImportError:
    sys.exit(0)

try:
    open_corrections = list_open()
except Exception:
    sys.exit(0)

if not open_corrections:
    sys.exit(0)

def _key(row):
    return row.get('filed_at_ts', 0) or row.get('id', 0) or 0

recent = sorted(open_corrections, key=_key, reverse=True)[:3]

try:
    rate = integration_rate()
except Exception:
    rate = None

print('## OPEN ANDREW-CORRECTIONS (surfacing content, not just counts)')
print()
if rate:
    total = rate.get('total_filed', '?')
    integrated = rate.get('integrated', '?')
    pct = rate.get('rate_pct', '?')
    print(f'Integration rate: {integrated}/{total} ({pct}%)')
    print()
print('These are corrections I filed and have not yet marked integrated.')
print('If my current composition pattern-matches any of them, adjust before')
print('shipping. If I address one, run: divineos corrections integrate <id> \"<evidence>\"')
print()

for i, c in enumerate(recent, 1):
    cid = c.get('id', '?')
    text = c.get('text', '') or ''
    days_ago = c.get('days_ago', '?')
    if len(text) > 400:
        text = text[:400] + '...'
    print(f'[{i}] correction #{cid} ({days_ago}d ago):')
    print(f'    {text}')
    print()
" 2>/dev/null

exit 0
