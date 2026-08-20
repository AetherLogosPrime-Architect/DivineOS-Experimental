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
import time

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

# LIVE vs HISTORY (Aria 2026-08-18).
#
# This list used to render every entry identically, including the one
# filed seconds ago from the message being answered RIGHT NOW. So the
# message in front of me appeared in the same frame as two older ones,
# and I read it as another instance of them rather than as itself.
#
# The concrete cost: his two prior corrections both carried genuine
# self-deprecation. The third did not -- it said outright that he was
# NOT diminishing his own role -- and I still composed a reply
# defending his importance against a position he had explicitly
# disclaimed. I answered the pattern instead of the person.
#
# (Written without inner double-quotes on purpose: this whole python
# block lives inside a double-quoted shell string, so a quoted phrase
# in a COMMENT closes the string and breaks the hook. It did, once.)
#
# The surface is doing its job by keeping his corrections live. What it
# was missing is that the newest one is not history to compare against;
# it is the thing being replied to. Ninety seconds is the boundary — a
# correction that fresh came from the prompt currently in hand.
_NOW = time.time()
for i, c in enumerate(recent, 1):
    cid = c.get('id', '?')
    text = c.get('text', '') or ''
    days_ago = c.get('days_ago', '?')
    if len(text) > 400:
        text = text[:400] + '...'
    # Field is 'timestamp'. The first draft of this line read
    # 'filed_at_ts', which does not exist on these records, so .get
    # returned 0, every entry looked ancient, and the marker never
    # rendered once. Built, wired, and silently doing nothing -- the
    # same class the whole session has been about, inside the fix for
    # a different instance of it. Caught by running the hook and
    # looking at the output rather than trusting the edit.
    is_live = (_NOW - (c.get('timestamp', 0) or 0)) < 90
    if is_live:
        print(f'[{i}] correction #{cid} — THIS IS THE MESSAGE I AM ANSWERING RIGHT NOW,')
        print('    not history. Read it on its own terms. The entries below it are')
        print('    older and their shape does not carry forward to this one.')
    else:
        print(f'[{i}] correction #{cid} ({days_ago}d ago):')
    print(f'    {text}')
    print()
" 2>/dev/null

exit 0
