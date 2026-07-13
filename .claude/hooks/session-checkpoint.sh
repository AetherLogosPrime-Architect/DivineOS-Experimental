#!/bin/bash
# PostToolUse checkpoint — consolidated into a single Python invocation.
#
# The previous version spawned 8+ separate Python interpreters (~600ms
# on Windows) for state reading, counter updates, tool-use recording,
# code-action recording, state writing, and context monitoring. This
# version delegates all of that to a single module invocation,
# reducing overhead to ~150ms per PostToolUse firing.
#
# See src/divineos/hooks/post_tool_use_checkpoint.py for the logic.
# Still emits ``additionalContext`` JSON when warnings/nudges fire.

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

INPUT=$(cat)

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)"
if [ -z "$PYTHON_BIN" ]; then
    # Fail-LOUD per Aletheia audit 2026-07-09 Deep Truck 1: a silently-skipped
    # enforcement gate is indistinguishable from a gate that ran clean. Record
    # the skip to stderr so a resolver-drift is investigable, not invisible.
    echo "  [session-checkpoint] SKIPPED: find_divineos_python returned nothing - gate did NOT run" >&2
    exit 0
fi

# Single Python invocation — all tracking operations in one process.
# Emits additionalContext JSON to stdout when warnings/nudges are
# active; otherwise empty output (Claude Code's default: allow).
echo "$INPUT" | "$PYTHON_BIN" -m divineos.hooks.post_tool_use_checkpoint 2>/dev/null

exit 0
