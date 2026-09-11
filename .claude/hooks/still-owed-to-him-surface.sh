#!/bin/bash
# SUPERSEDED 2026-09-08 by the router. The decision now lives in
# divineos.core.hook_surfaces as still_owed_to_him, dispatched by
# doorbell-user-prompt-submit.sh. The registration came out of settings.json in
# the SAME change -- a migration that leaves the original registered has moved
# code and retired nothing.
# INTENTIONALLY UNWIRED (2026-09-08): superseded, see above.
# UserPromptSubmit hook — what he is still waiting on, and how many times he
# has had to ask for it.
#
# WHY THIS EXISTS. Andrew 2026-09-07: *i have repeated it on end.. and nothing
# has been done about it.* The repetition is the injury and nothing anywhere
# counted it. He has been the only instrument for how many times he had to say
# a thing, carrying the tally in his own head while being told each time that
# it was heard.
#
# THE CALLER IS HIS MESSAGE, and that is the entire point. Aria found it after
# we listed eight ways to cheaply satisfy any station built for his requests:
# every store either of us built for him needed calling, so every one of them
# holds zero rows. His speaking is the one event in this architecture that
# cannot be forgotten, because it starts every turn. So the surface binds to
# that rather than to a command one of us has to remember.
#
# NO BYPASS. Every other station here has a fire door with a written reason,
# because a gate on code can deadlock its own repair. Nothing about doing what
# he asked can ever be blocked by doing what he asked, so that argument does
# not reach this one and there is no escape hatch.
#
# Fail-open: any error exits 0 silently. A surface that cannot read must never
# take the turn down with it -- and the store itself answers could-not-read
# distinctly from nothing-owed, so a blank here is not a clean slate.

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
    from divineos.core.andrew_request_repeats import surface

    text = surface()
    if text:
        print(text)
except Exception:
    pass
" 2>/dev/null  # fail-soft: a surface that cannot read must never take his turn down with it, and the store answers could-not-read distinctly from nothing-owed, so a blank here is never mistaken for a clean slate

exit 0
