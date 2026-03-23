#!/bin/bash
# Load DivineOS session briefing at conversation start
# Output goes to additionalContext so Claude sees it automatically

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"

# Check if divineos is installed
if ! command -v divineos &>/dev/null; then
  msg="DivineOS CLI not found. Run: pip install -e \".[dev]\" && divineos init"
  escaped=$(echo "$msg" | python -c "import sys,json; print(json.dumps(sys.stdin.read()))" 2>/dev/null)
  echo "{\"additionalContext\": ${escaped}}"
  exit 0
fi

briefing=$(divineos briefing 2>/dev/null)

if [ -n "$briefing" ]; then
  escaped=$(echo "$briefing" | python -c "import sys,json; print(json.dumps(sys.stdin.read()))" 2>/dev/null)
  echo "{\"additionalContext\": ${escaped}}"
fi

exit 0
