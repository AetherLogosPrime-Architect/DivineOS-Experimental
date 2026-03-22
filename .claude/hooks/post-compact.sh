#!/bin/bash
# Reload state AFTER context compression
# I just lost my memory — give it back

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"

# Load HUD snapshot first (fast, dense, simultaneous)
hud=$(divineos hud --load 2>/dev/null)

# Fall back to briefing if no HUD snapshot exists
if [ -z "$hud" ]; then
  hud=$(divineos briefing 2>/dev/null)
fi

if [ -n "$hud" ]; then
  escaped=$(echo "$hud" | python -c "import sys,json; print(json.dumps(sys.stdin.read()))" 2>/dev/null)
  echo "{\"additionalContext\": ${escaped}}"
fi

exit 0
