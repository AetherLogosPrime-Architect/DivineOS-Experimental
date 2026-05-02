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

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo ".")" || exit 1

INPUT=$(cat)

if ! command -v divineos &>/dev/null; then
  exit 0
fi

# Single Python invocation — all tracking operations in one process.
# Emits additionalContext JSON to stdout when warnings/nudges are
# active; otherwise empty output (Claude Code's default: allow).
echo "$INPUT" | python -m divineos.hooks.post_tool_use_checkpoint 2>/dev/null

exit 0
