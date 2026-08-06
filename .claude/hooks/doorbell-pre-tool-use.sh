#!/bin/bash
# PreToolUse doorbell. One of seven. All judgment lives in the OS.
#
# Andrew 2026-06-30: "Make the hooks dumber so they can't be wrong; put the
# logic in the OS so the decision happens where the contract is."
#
# This file must stay dumb. If it grows a branch, the branch belongs in
# divineos.core.hook_surfaces instead.

set +e
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0  # fail-soft: outside a repo there is no OS to route into, and a doorbell that cannot find the substrate must let the tool through rather than wall the work
[ -z "$REPO_ROOT" ] && exit 0
# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0  # fail-soft: without the helper there is no interpreter to resolve and a doorbell must never block work
PYTHON_BIN="$(find_divineos_python)" || exit 0  # fail-soft: no interpreter means no surfaces; a broken doorbell must fail open

HOOK_JSON="$(cat)" "$PYTHON_BIN" -c "
import json, os, sys
try:
    from divineos.core.hook_router import main
    from divineos.core.hook_surfaces import install
except ImportError:
    sys.exit(0)
install()
try:
    payload = json.loads(os.environ.get('HOOK_JSON', '') or '{}')
except ValueError:
    payload = {}
sys.exit(main('PreToolUse', payload))
"
exit $?
