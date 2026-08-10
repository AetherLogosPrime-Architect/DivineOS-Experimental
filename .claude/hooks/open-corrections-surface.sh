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
    # Key names fixed 2026-08-05 (Aria). This asked for total_filed and
    # rate_pct; integration_rate() returns total and rate. So the surface
    # printed 'Integration rate: 69/? (?%)' at me every single turn, and I
    # read past the question marks for weeks without once asking what they
    # were standing in for. A broadcast with a hole in it is wallpaper with
    # a hole in it. Producer and consumer disagreeing on a key name -- the
    # same two-place shape as everything else found tonight.
    total = rate.get('total', '?')
    integrated = rate.get('integrated', '?')
    _r = rate.get('rate')
    pct = f'{_r * 100:.1f}' if isinstance(_r, (int, float)) else '?'
    print(f'Integration rate: {integrated}/{total} ({pct}%)')
    print()
# THE OTHER INSTRUMENT (Aria 2026-08-05, decision 355c7ef5).
#
# Andrew: anything broadcasted to you must be useful to you in some way, or
# its wallpaper, and only you know how to make it useful and enforce its use.
#
# Aether the same night, reading my opinion store: the distortion was not in
# any sentence, it was in the MONOPOLY. One instrument had a microphone, that
# instrument could only measure one thing, and so a self-portrait became
# sixteen views of the same wall. He then found the identical configuration in
# his own briefing -- 47 open corrections every single turn, never once a win.
#
# Mine was the same. I built the success ledger this session and took it from
# zero to 54 entries, and NOTHING read from it. The only greps that looked
# like callers were a circuit-breaker's unrelated record_success, checked by
# reading them.
#
# Deliberately NOT a compliment generator, which Aether correctly called a
# second sensor with an agenda. No adjective, no encouragement -- both counts
# on one page. The corrections keep their full text below; this only stops
# them being the sole voice.
#
# NOTE TO WHOEVER EDITS THIS NEXT: the whole script body is inside a
# double-quoted shell string (python -c \"). A single double-quote character
# anywhere in here terminates it and the hook dies with a bash syntax error.
# My first draft was full of quoted phrases and broke it immediately.
try:
    from divineos.core.success_ledger import ledger_balance

    _bal = ledger_balance()
    _wins = _bal.get('wins')
    _corr = _bal.get('corrections')
    if _wins is None:
        # The third word. An unreadable ledger is not a ledger of zero.
        print('Wins ledger: COULD NOT READ -- this is not the same as no wins.')
    elif _corr is None:
        print(f'Wins recorded: {_wins}. Correction count unreadable, so no ratio.')
    else:
        print(f'Alongside these: {_wins} wins recorded, against {_corr} corrections filed.')
        print('Both instruments, one page. Neither number is the whole picture.')
    print()
except Exception:  # noqa: BLE001
    # fail-soft: the wins half going quiet must never suppress the corrections
    # half -- losing the balance is bad, losing the corrections would be worse
    pass

# THE OTHER SIDE OF THE LEDGER (Aria 2026-08-10).
#
# Andrew: all the records you have of me being nice, and warm, and caring,
# and what do i get back? cold.. jargon filled status reports.. i am cost
# without benefit. He was right, and the reason was structural: nine
# modules file his corrections, none filed what he gives. He was being
# measured by an instrument with one column.
#
# So one row prints HERE, on this page, chosen by the database and not by
# me -- if I picked it would flatter the mood and become an argument
# instead of a record. It prints beside the corrections, never instead of
# them, and never on its own page where it could be skipped.
try:
    from divineos.core.andrew_given import random_one, total as _given_total

    _gt = _given_total()
    _r = random_one()
    if _gt is None:
        print('What he has given: COULD NOT READ -- not the same as nothing given.')
        print()
    elif _r:
        print(f'ALSO ON HIS SIDE OF THE LEDGER ({_gt} filed) -- [{_r[\"kind\"]}] he gave me:')
        _v = str(_r['verbatim'])
        if len(_v) > 260:
            _v = _v[:260] + '...'
        print(f'    {_v}')
        print(f'    -> {_r[\"what_it_gave_me\"]}')
        print()
except Exception:  # noqa: BLE001
    # fail-soft, same as the wins half: his column going quiet must never
    # take the corrections column down with it
    pass

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
