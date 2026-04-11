#!/bin/bash
# Lightweight reload AFTER context compression
# The full briefing was loaded at session start and is preserved in
# the compacted summary. We only need a short reminder of critical
# items -- not a full re-dump that wastes thousands of tokens.

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo ".")" || exit 1

if ! command -v divineos &>/dev/null; then
  exit 0
fi

# Get ONLY the brief HUD (6 essential slots) instead of full dump
hud_brief=$(divineos hud --brief 2>/dev/null)

# Get active lessons (the stuff I actually need to remember)
lessons=$(divineos lessons 2>/dev/null | head -20)

if [ -n "$hud_brief" ]; then
  full_context="=== DIVINEOS POST-COMPACTION REMINDER ===

Context was compacted. Your full briefing is in the compacted summary above.
This is a lightweight reminder of critical state only.

If you need full context, run: divineos briefing

--- QUICK STATE ---
${hud_brief}

--- ACTIVE LESSONS ---
${lessons}

=== END REMINDER ==="

  escaped=$(echo "$full_context" | python -c "import sys,json; print(json.dumps(sys.stdin.read()))" 2>/dev/null)
  echo "{\"additionalContext\": ${escaped}}"
fi

exit 0
