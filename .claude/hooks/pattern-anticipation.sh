#!/bin/bash
# PostToolUse hook: Pattern Anticipation
#
# After Edit/Write, checks if the file/context matches any past mistakes
# or recurring lessons. Surfaces warnings via additionalContext so the AI
# sees them before continuing.
#
# Throttled: only runs every 5 edits to avoid noise.

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo ".")" || exit 1

INPUT=$(cat)

if ! command -v divineos &>/dev/null; then
  exit 0
fi

# Throttle: only check every 5th edit
# Use Python expanduser for Windows compatibility (Git Bash $HOME = /c/Users/...)
DIVINEOS_DIR=$(python -c "import os; print(os.path.join(os.path.expanduser('~'), '.divineos'))" 2>/dev/null || echo "$HOME/.divineos")
STATE_FILE="$DIVINEOS_DIR/anticipation_state.json"
mkdir -p "$DIVINEOS_DIR"
if [ ! -f "$STATE_FILE" ]; then
  echo '{"edit_count":0}' > "$STATE_FILE"
fi

_ASF="import os; SF=os.path.join(os.path.expanduser('~'),'.divineos','anticipation_state.json')"
edit_count=$(python -c "$_ASF; import json; print(json.load(open(SF)).get('edit_count',0))" 2>/dev/null || echo "0")
edit_count=$((edit_count + 1))
python -c "$_ASF; import json; json.dump({'edit_count':$edit_count}, open(SF,'w'))" 2>/dev/null

if [ $((edit_count % 5)) -ne 0 ]; then
  exit 0
fi

# Extract file path from tool input
file_path=$(echo "$INPUT" | python -c "
import sys, json
d = json.load(sys.stdin)
inp = d.get('tool_input', {})
print(inp.get('file_path', inp.get('command', '')))
" 2>/dev/null || echo "")

if [ -z "$file_path" ]; then
  exit 0
fi

# Run anticipation
result=$(python -c "
import json, sys
from divineos.core.anticipation import anticipate, format_anticipation
context = '''Editing: $file_path'''
warnings = anticipate(context, max_warnings=3)
if warnings:
    output = format_anticipation(warnings)
    print(json.dumps({'additionalContext': output}))
" 2>/dev/null)

if [ -n "$result" ]; then
  echo "$result"
fi

exit 0
