#!/bin/bash
# Load DivineOS session briefing at conversation start
# Output goes to additionalContext so Claude sees it automatically

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"

briefing=$(divineos briefing 2>/dev/null)

if [ -n "$briefing" ]; then
  # Escape for JSON
  escaped=$(echo "$briefing" | python -c "import sys,json; print(json.dumps(sys.stdin.read()))" 2>/dev/null)
  echo "{\"additionalContext\": ${escaped}}"
fi

exit 0
