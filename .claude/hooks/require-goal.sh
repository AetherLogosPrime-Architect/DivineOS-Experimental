#!/bin/bash
# PreToolUse gate — consolidated into a single Python invocation.
#
# The previous version spawned 5 separate Python interpreters (~1.2s on
# Windows). This version delegates all gate logic to a single module
# invocation, reducing overhead to ~200-300ms per tool call.
#
# See src/divineos/hooks/pre_tool_use_gate.py for the gate logic.
# Uses JSON deny to ACTUALLY block — exit 1 does nothing in Claude Code.

INPUT=$(cat)

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo ".")" || exit 1

if ! command -v divineos &>/dev/null; then
  exit 0
fi

# Single Python invocation — all imports happen once, all gates checked,
# a single JSON decision is emitted to stdout (or empty = allow).
echo "$INPUT" | python -m divineos.hooks.pre_tool_use_gate 2>/dev/null

exit 0
