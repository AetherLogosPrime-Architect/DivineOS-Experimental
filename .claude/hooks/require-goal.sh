#!/bin/bash
# Block code changes until a goal has been set AND the OS has been engaged.
# Two gates:
#   1. At least one active goal must exist
#   2. The AI must have used a thinking tool (ask, recall, directives, etc.)
# If you haven't engaged with the OS, you can't write code.

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"

if ! command -v divineos &>/dev/null; then
  exit 0
fi

# Gate 1: Check if any active goal exists
goals=$(divineos goal list 2>/dev/null)

if echo "$goals" | grep -q "No goals"; then
  echo "BLOCKED: You have not set a goal yet."
  echo ""
  echo "Before writing any code, you must:"
  echo "  1. Read your briefing (already loaded at session start)"
  echo "  2. Set a goal: divineos goal add \"what you are working on\" --original \"user's exact words\""
  echo ""
  echo "This is not optional. The OS requires you to know what you are doing before you do it."
  exit 1
fi

# Gate 2: Check for engagement marker (set by ask, recall, directives, etc.)
hud_dir="src/data/hud"
if [ ! -f "$hud_dir/.session_engaged" ]; then
  echo "BLOCKED: You have not engaged with the OS yet this session."
  echo ""
  echo "You have goals set, but you haven't consulted your knowledge. Before writing code:"
  echo "  - divineos ask \"topic\"     -- search what you know"
  echo "  - divineos recall           -- load core + active memory"
  echo "  - divineos directives       -- review operating principles"
  echo ""
  echo "The OS is not decoration. Use it to think, then write."
  exit 1
fi

exit 0
