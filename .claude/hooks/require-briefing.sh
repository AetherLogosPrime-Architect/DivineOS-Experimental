#!/bin/bash
# PreToolUse hook â€” require briefing before any tool use.
#
# Andrew 2026-05-14 night: hooks should point to the OS, not replace
# it. This hook is the doorman: it refuses tool calls when briefing
# is stale (>=10 prompts since last load) or has never been loaded
# this session. The OS itself (divineos briefing) does the rendering
# work. Plain-chat responses are unaffected â€” only tool calls gate.
#
# The hook's whole job is two lines of Python: import the OS's
# staleness_signal, deny if stale. Logic lives in
# core.briefing_freshness. If anyone else picks up the OS without
# this hook, the substrate's freshness tracking still works â€” they
# just have to choose to enforce it differently.
#
# Bypass list: a small set of commands MUST work without the gate
# firing â€” otherwise the bootstrap path is impossible. ``divineos
# briefing`` itself, ``init``, ``preflight``, ``recall``, ``ask``,
# ``hud`` â€” bootstrap surfaces.
#
# Fail-open: any error exits 0 without blocking. This hook cannot
# break the user's workflow.

INPUT=$(cat)

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

echo "$INPUT" | "$PYTHON_BIN" -c "
import json, sys

try:
    data = json.loads(sys.stdin.read() or '{}')
except Exception:
    sys.exit(0)

tool_name = data.get('tool_name') or ''
tool_input = data.get('tool_input') or {}

# Bypass: bootstrap divineos commands and read-only ops that must
# work for the briefing-load loop itself to function.
if tool_name == 'Bash':
    cmd = (tool_input.get('command') or '').strip()
    # Allow divineos briefing/init/preflight/recall/ask/hud/context
    # so the agent can actually load briefing or check minimum state.
    for bypass in (
        'divineos briefing',
        'divineos init',
        'divineos preflight',
        'divineos recall',
        'divineos ask',
        'divineos hud',
        'divineos context',
        'divineos goal',
    ):
        if cmd.startswith(bypass) or (' ' + bypass + ' ') in (' ' + cmd + ' ') or cmd.endswith(' ' + bypass) or (bypass + ' ') in cmd:
            sys.exit(0)

try:
    from divineos.core.briefing_freshness import staleness_signal
except Exception:
    sys.exit(0)  # fail-open if OS module unavailable

try:
    sig = staleness_signal()
except Exception:
    sys.exit(0)

if not sig.get('is_stale'):
    sys.exit(0)

# Stale â€” emit deny with message pointing at the OS command.
reason = sig.get('reason', 'briefing stale')
prompts = sig.get('prompts_since_load', 0)
never = sig.get('never_loaded', False)
if never:
    msg = (
        'BLOCKED: briefing has not been loaded this session. '
        'Run: divineos briefing\\n'
        '(Plain-chat responses are still allowed; this gate only '
        'blocks tool use. The OS does the rendering â€” this hook is '
        'just the doorman.)'
    )
else:
    msg = (
        f'BLOCKED: briefing is stale ({prompts} prompts since last load; '
        f'threshold 10). Run: divineos briefing\\n'
        '(Plain-chat responses are still allowed; this gate only '
        'blocks tool use. The OS does the rendering â€” this hook is '
        'just the doorman.)'
    )

print(json.dumps({
    'hookSpecificOutput': {
        'hookEventName': 'PreToolUse',
        'permissionDecision': 'deny',
        'permissionDecisionReason': msg,
    }
}))
" 2>/dev/null

exit 0

