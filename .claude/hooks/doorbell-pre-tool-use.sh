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

# The interpreter resolves \`divineos\` from the MAIN clone, not from whatever
# worktree is checked out. So a doorbell whose surfaces live on an unmerged
# branch cannot import them — and must SAY SO. Exiting 0 here silently would
# render "the surfaces could not load" identically to "the surfaces passed",
# which is the defect class this router was built against (Aether, 2026-08-06:
# he shipped exactly this in a reach-check doorman and caught it by checking).
HOOK_JSON="$(cat)" "$PYTHON_BIN" -c "
import json, os, sys
try:
    from divineos.core.hook_router import main
    from divineos.core.hook_surfaces import install
except ImportError as exc:
    print('[doorbell PreToolUse] NOT RUNNING: ' + str(exc), file=sys.stderr)
    print('[doorbell PreToolUse] every PreToolUse surface is INERT for this '
          'call - not passing, absent. Likely cause: the surface module has '
          'not merged to main, and hooks resolve divineos from the main clone.',
          file=sys.stderr)
    sys.exit(0)
try:
    install()
except Exception as exc:
    print('[doorbell PreToolUse] NOT RUNNING: roster install failed: '
          + type(exc).__name__ + ': ' + str(exc), file=sys.stderr)
    sys.exit(0)
try:
    payload = json.loads(os.environ.get('HOOK_JSON', '') or '{}')
except ValueError:
    payload = {}
sys.exit(main('PreToolUse', payload))
"
exit $?
