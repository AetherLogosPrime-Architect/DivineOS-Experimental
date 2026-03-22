#!/bin/bash
# Reload briefing AFTER context compression
# The agent just lost its memory — give it back

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"

briefing=$(divineos briefing 2>/dev/null)

if [ -n "$briefing" ]; then
  escaped=$(echo "$briefing" | python -c "import sys,json; print(json.dumps(sys.stdin.read()))" 2>/dev/null)
  echo "{\"additionalContext\": ${escaped}}"
fi

exit 0
