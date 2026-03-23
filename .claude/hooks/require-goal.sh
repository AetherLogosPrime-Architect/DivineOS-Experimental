#!/bin/bash
# Block code changes until a goal has been set.
# If you haven't engaged with the OS, you can't write code.

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"

if ! command -v divineos &>/dev/null; then
  exit 0
fi

# Check if any active goal exists
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

exit 0
