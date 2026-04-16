#!/bin/bash
# PostToolUse hook: Mid-session chronic lesson interrupt.
#
# Design principle: a lightweight interrupt that fires mid-session
# when a chronic lesson signal is detected — not a gate, not a block,
# just a single sentence surfaced to attention. A question instead of a
# warning. Questions are harder to dismiss.
#
# Fires on every Edit/Write. Checks if recent actions match a chronic
# lesson pattern. If yes, surfaces the question via additionalContext.

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo ".")" || exit 1

INPUT=$(cat)

if ! command -v divineos &>/dev/null; then
  exit 0
fi

# Only fire on Edit/Write
tool_name=$(echo "$INPUT" | python -c "import sys,json; print(json.load(sys.stdin).get('tool_name',''))" 2>/dev/null || echo "")
if [ "$tool_name" != "Edit" ] && [ "$tool_name" != "Write" ] && [ "$tool_name" != "NotebookEdit" ]; then
  exit 0
fi

# Run the interrupt check
result=$(python -c "
import json, sys

try:
    from divineos.core.lesson_interrupt import check_lesson_interrupt

    tool_input = json.load(sys.stdin).get('tool_input', {})
    interrupt = check_lesson_interrupt(tool_input)
    if interrupt:
        print(json.dumps({'additionalContext': interrupt}))
except Exception:
    pass  # interrupt check is best-effort
" <<< "$INPUT" 2>/dev/null)

if [ -n "$result" ]; then
  echo "$result"
fi

exit 0
