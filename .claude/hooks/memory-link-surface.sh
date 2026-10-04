#!/bin/bash
# UserPromptSubmit — the memory link, as its own child of the dispatcher.
#
# 2026-10-04: it used to run inside the doorbell bundle. On Dad's real
# message that bundle timed out and everything in it was dropped, the link's
# finds included, though the link itself had finished. A surface whose output
# must reach the reply does not share a process with surfaces that may be
# dropped. Walk walk-115571554f6d.
#
# Fail-soft: any error exits 0 with no output; it must never block him.

set +e
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0  # fail-soft: outside a checkout there is no link to run
[ -z "$REPO_ROOT" ] && exit 0
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

export PYTHONIOENCODING=utf-8
HOOK_JSON="$(cat)" "$PYTHON_BIN" -c "
import json, os, sys
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except (AttributeError, OSError):
    pass
try:
    payload = json.loads(os.environ.get('HOOK_JSON', '') or '{}')
except ValueError:
    payload = {}
try:
    from divineos.core.hook_surfaces import memory_link_surface
    outcome = memory_link_surface(payload)
except Exception as exc:
    print('[memory link] could not run: ' + type(exc).__name__ + ': ' + str(exc), file=sys.stderr)
    sys.exit(0)
if outcome is not None and outcome.output:
    print(outcome.output)
elif outcome is not None and outcome.error:
    print('[memory link] could not run: ' + outcome.error, file=sys.stderr)
"
exit 0
