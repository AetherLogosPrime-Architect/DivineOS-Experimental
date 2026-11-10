#!/bin/bash
# PostToolUse on Write|Edit: the link that listens to our own words. Design note 2026-11-08, points 1 to 10.
#
# SCAFFOLDING, STATED PLAINLY: this file is the named caller the wiring test requires, and the off switch. The search
# itself is not built yet. Until it is, any mode other than 'off' says so on stderr so a mode of 'log' can never read as
# a listener that ran and found nothing (Hoare: could-not-look must print). Default mode is 'off'. It fails open: a
# problem here must never stop a Write (the existing link's rule), and it says so.

set +e
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0  # fail-open: outside a checkout there is nothing to listen to
[ -z "$REPO_ROOT" ] && exit 0
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

export PYTHONIOENCODING=utf-8
HOOK_JSON="$(cat)" "$PYTHON_BIN" -c "
import json, os, sys
try:
    payload = json.loads(os.environ.get('HOOK_JSON', '') or '{}')
except ValueError:
    payload = {}
if payload.get('agent_id'):
    sys.exit(0)  # a helper agent is never listened to, the same line his_voice_hook draws
def say(text):
    # stdout JSON additionalContext is the route the house's other surfaces use to reach the model; an exit-0 hook's
    # stderr is not known to (Aria, 2026-11-08), and a log mode that says nothing reads as 'found nothing'.
    print(json.dumps({'hookSpecificOutput': {'hookEventName': 'PostToolUse', 'additionalContext': text}}))
try:
    from divineos.core import own_words_link_settings as s
    cfg = s.load()
    s.validate(cfg)
except Exception as exc:  # fail-open, and say so
    say('[own-words-link] could not read its settings: ' + type(exc).__name__ + ': ' + str(exc))
    sys.exit(0)
if cfg['mode'] == 'off':
    sys.exit(0)
say('[own-words-link] mode=' + cfg['mode'] + ' but the search is not built yet: nothing was looked for')
"
exit 0
