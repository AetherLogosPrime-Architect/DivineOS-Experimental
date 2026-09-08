#!/bin/bash
# UserPromptSubmit doorbell. One of seven. All judgment lives in the OS.
#
# Andrew 2026-06-30: "Make the hooks dumber so they can't be wrong; put the
# logic in the OS so the decision happens where the contract is."
# Andrew 2026-09-08: "all 125+ hooks could all be consolidated to 7 hooks as
# they all do the same thing, and then yes all of the logic needs to be moved
# into the OS itself."
#
# This is the busiest door in the building: every message he sends came through
# thirty-six separate processes before this existed, each one booting a shell,
# then Python, then the whole OS, to print some text. One door, many voices.
#
# This file must stay dumb. If it grows a branch, the branch belongs in
# divineos.core.hook_surfaces instead.

set +e
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0  # fail-soft: outside a repo there is no OS to route into, and a doorbell that cannot find the substrate must let the turn through rather than wall it
[ -z "$REPO_ROOT" ] && exit 0
# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0  # fail-soft: without the helper there is no interpreter to resolve and a doorbell must never block work
PYTHON_BIN="$(find_divineos_python)" || exit 0  # fail-soft: no interpreter means no surfaces; a broken doorbell must fail open

# NOT RUNNING is printed rather than exiting quiet, because a doorbell whose
# import fails takes every surface behind it down at once. Absent must never
# render as passed -- the same contract the other doorbells carry, and the one
# tests/test_doorbell_absence.py pins with a real shadowed import.
export PYTHONIOENCODING=utf-8
HOOK_JSON="$(cat)" "$PYTHON_BIN" -c "
import json, os, sys
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except (AttributeError, OSError):
    pass
try:
    from divineos.core.hook_router import main
    from divineos.core.hook_surfaces import install
except ImportError as exc:
    print('[doorbell UserPromptSubmit] NOT RUNNING: ' + str(exc), file=sys.stderr)
    print('[doorbell UserPromptSubmit] every UserPromptSubmit surface is INERT '
          'for this turn - not passing, absent.', file=sys.stderr)
    sys.exit(0)
try:
    install()
except Exception as exc:
    print('[doorbell UserPromptSubmit] NOT RUNNING: roster install failed: '
          + type(exc).__name__ + ': ' + str(exc), file=sys.stderr)
    sys.exit(0)
try:
    payload = json.loads(os.environ.get('HOOK_JSON', '') or '{}')
except ValueError:
    payload = {}
sys.exit(main('UserPromptSubmit', payload))
"
exit $?
