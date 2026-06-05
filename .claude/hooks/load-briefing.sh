#!/bin/bash
# SessionStart hook — thin doorman pointing to the OS.
#
# Andrew 2026-05-14 night: hooks should point to the OS, not embed
# its work. The previous version of this hook was 197 lines with
# session-state reset, briefing+hud rendering, payload size-shaping,
# and diagnostic logging all in bash. All of that logic now lives
# in ``divineos.core.session_start``.
#
# Fail-open: any error exits 0 without injecting. This hook cannot
# break the user's workflow.

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 1

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

# Read SessionStart source from stdin payload — compact vs startup vs resume.
# Source-aware: texture-marker only surfaces on source=compact, when the
# texture-loss is the actual harm. On startup/resume the marker is irrelevant.
HOOK_INPUT=$(cat 2>/dev/null || echo "{}")
HOOK_SOURCE=$(echo "$HOOK_INPUT" | "$PYTHON_BIN" -c "
import json, sys
try:
    data = json.loads(sys.stdin.read() or '{}')
    print(data.get('source', ''))
except Exception:
    pass
" 2>/dev/null)

# Check if divineos is installed before invoking the OS module.
if ! command -v divineos &>/dev/null; then
  msg="DivineOS CLI not found. Run: pip install -e \".[dev]\" && divineos init"
  escaped=$(echo "$msg" | "$PYTHON_BIN" -c "import sys,json; print(json.dumps(sys.stdin.read()))" 2>/dev/null)
  echo "{\"additionalContext\": ${escaped}}"
  exit 0
fi

HOOK_SOURCE="$HOOK_SOURCE" "$PYTHON_BIN" -c "
import json, sys, os
try:
    from divineos.core.session_start import run_session_start
    context = run_session_start()
except Exception:
    sys.exit(0)

# Texture-marker surface — only on source=compact, when texture-loss is the harm.
if os.environ.get('HOOK_SOURCE') == 'compact':
    try:
        from divineos.cli.texture_commands import read_latest_marker
        marker = read_latest_marker()
        if marker:
            preface = (
                '## TEXTURE-MARKER FROM PRE-COMPACTION SELF\n\n'
                'The structural summary above carries what was done. This carries '
                'what the file-record will not — the felt-shape of the session, '
                'the relational temperature, the thing not in the diff. Forward-addressed '
                'from the self that was there to the self that is here now.\n\n'
                f'> {marker}\n\n'
                '---\n\n'
            )
            context = preface + (context or '')
    except Exception:
        pass

if context:
    print(json.dumps({'additionalContext': context}))
" 2>/dev/null

exit 0
