#!/bin/bash
# PreToolUse hook — require briefing before any tool use.
#
# Andrew 2026-05-14 night: hooks should point to the OS, not replace
# it. This hook is the doorman: it refuses tool calls when briefing
# is stale or has never been loaded this session. The OS itself
# (divineos briefing) does the rendering work. Plain-chat responses
# are unaffected — only tool calls gate.
#
# REFACTORED 2026-06-24 (per prereg-7bba8b123d42, hook-migration arc):
# Bypass-list + segment-split moved to `divineos.core.briefing_bypass`
# so any non-Claude substrate gets the same bootstrap-command
# allowlist. Deny-message construction stays HERE because the
# hookSpecificOutput JSON shape is Claude-Code-specific — other
# substrates have different hook formats.
#
# Council-walk pivot (Carmack scope-down): the original proposal
# moved deny-message into core/briefing_freshness.py (guardrail-listed).
# Walking through Carmack showed the deny-message is Claude-Code-shaped
# and shouldn't live in the portable OS. Keeping it here keeps the
# portable bits portable and the Claude-Code-bits Claude-Code-shaped.
#
# Fail-open: any error exits 0 without blocking.

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

# Bypass: bootstrap divineos commands handled by the portable OS module.
if tool_name == 'Bash':
    cmd = (tool_input.get('command') or '').strip()
    try:
        from divineos.core.briefing_bypass import is_bypass_bash_command
        if is_bypass_bash_command(cmd):
            sys.exit(0)
    except Exception:
        pass  # fail-open

try:
    from divineos.core.briefing_freshness import staleness_signal
except Exception:
    sys.exit(0)

try:
    sig = staleness_signal()
except Exception:
    sys.exit(0)

if not sig.get('is_stale'):
    sys.exit(0)

# Stale — emit deny with message pointing at the OS command.
# Message construction stays in the hook because hookSpecificOutput
# JSON is Claude-Code-specific (the portable bypass-list lives in
# core/briefing_bypass).
reason = sig.get('reason', 'briefing stale')
never = sig.get('never_loaded', False)
if never:
    msg = (
        'BLOCKED: briefing has not been loaded this session. '
        'Run: divineos briefing\\n'
        '(Plain-chat responses are still allowed; this gate only '
        'blocks tool use. The OS does the rendering — this hook is '
        'just the doorman.)'
    )
else:
    msg = (
        f'BLOCKED: {reason}\\n'
        '  Cheap cure: recall your briefing-id from context and run '
        'divineos briefing-id <id> (re-stamps freshness).\\n'
        '  Or reload: divineos briefing (issues a new id).\\n'
        '(Plain-chat responses are still allowed; this gate only '
        'blocks tool use. The OS does the rendering — this hook is '
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
