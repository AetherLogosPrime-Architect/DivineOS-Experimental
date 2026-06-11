#!/bin/bash
# PreToolUse(Bash) — block substrate-write CLI commands until pending
# obligations get cleared.
#
# WHY THIS EXISTS (Andrew 2026-06-06):
# Measured 0% follow-through rate on will-shape promises across the full
# 78-day substrate lifetime. 27 unanswered will-shape entries, zero with
# structural backing. Surface-only reminders got piled up and ignored by
# the optimizer's cheap-close routing.
#
# This hook converts the surface into a structural gate: when total
# obligations (will-shape + correction-pairing) >= threshold, block new
# substrate writes until the operator clears at least one by writing
# structural backing (code + tests) that references the source knowledge_id.
#
# DESIGN RULES (Aether 2026-06-06, learned from the gate-cascade incident):
# 1. Matcher is anchored — no substring matches in echo args / quoted data.
# 2. Exempts canonical gate-clearing commands (goal add, goal done, learn,
#    compass-ops observe, briefing, init) so this gate never deadlocks the
#    upstream gates that depend on those commands.
# 3. Honors kill-switch at ~/.divineos-<member>/obligations.disabled.
#    Operator removes the marker with `rm` which is on _DEV_PREFIXES'
#    always-allowed list — so the rm escape path survives even if this
#    gate misbehaves catastrophically.
# 4. All matcher logic lives in core/obligations.py with unit tests at
#    tests/test_obligations.py. The hook is a thin shell calling testable
#    Python code.
#
# Tasks #33 (correction-pairing) + #42 (will-shape promises), built as one
# unified obligation-check rather than two parallel hooks.
#
# Fail-open: any error exits 0 silently. This hook cannot break a turn.

INPUT=$(cat)

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

# All three checks run in a single python invocation that calls the core
# functions directly. Previous version used `python -m divineos.cli ...`
# which fails silently because divineos.cli is a package without a __main__
# entry-point. The hook then mis-interpreted the failure as "not a write"
# and allowed everything through (Aether 2026-06-07: gate was broken from
# day one). This pattern mirrors post-response-audit.sh — call functions
# directly via inline python.
DECISION=$(printf '%s' "$INPUT" | "$PYTHON_BIN" -c "
import json, sys
from divineos.core.obligations import (
    is_gate_disabled,
    is_substrate_write_command,
    get_pending_obligations,
    command_references_open_obligation,
)
try:
    data = json.loads(sys.stdin.read() or '{}')
except Exception:
    print('ALLOW_EMPTY')
    sys.exit(0)
if is_gate_disabled():
    print('ALLOW_DISABLED')
    sys.exit(0)
cmd = (data.get('tool_input') or {}).get('command', '') or ''
if not cmd:
    print('ALLOW_EMPTY')
    sys.exit(0)
if not is_substrate_write_command(cmd):
    print('ALLOW_NOT_WRITE')
    sys.exit(0)
obligations = get_pending_obligations()
if not obligations['should_block']:
    print('ALLOW_CLEAR')
    sys.exit(0)
# Locked-box fix (Andrew 2026-06-11): if this command's payload
# REFERENCES one of the open obligation kids, it IS the structural
# backing landing — let it through. The gate was previously blocking
# the very writes that would have backed the obligations (filing a
# prereg that names the kid; committing code that references the kid
# in the message). That trap forced bypass-marker use for routine
# work; the fix is to detect in-flight backing and allow it.
matched_kid = command_references_open_obligation(cmd, obligations)
if matched_kid:
    print('ALLOW_REFERENCES_OPEN_KID')
    sys.exit(0)
print('BLOCK')
" 2>/dev/null)

# Anything other than BLOCK means allow.
if [ "$DECISION" != "BLOCK" ]; then
  exit 0
fi

# Block. Generate the human-readable message.
BLOCK_MESSAGE=$("$PYTHON_BIN" -c "
from divineos.core.obligations import get_pending_obligations, format_block_message
print(format_block_message(get_pending_obligations()))
" 2>/dev/null)

if [ -z "$BLOCK_MESSAGE" ]; then
  # Could not produce message → fail-open rather than mystery-block.
  exit 0
fi

MEMBER="${DIVINEOS_MEMBER:-aether}"
MARKER_PATH="$HOME/.divineos-$MEMBER/obligations.disabled"

cat >&2 <<EOF
$BLOCK_MESSAGE

To disable this gate entirely (emergency operator escape — Andrew 2026-06-06
cascade-incident lesson): drop the kill-switch marker file. From your shell:
  mkdir -p "$HOME/.divineos-$MEMBER"
  touch "$MARKER_PATH"

To re-enable: rm "$MARKER_PATH"
EOF
exit 2
