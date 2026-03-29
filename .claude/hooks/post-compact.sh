#!/bin/bash
# Reload state AFTER context compression
# Context compaction erases enforcement. This hook restores it.
# Without this, the AI continues working post-compaction with no
# briefing, no orientation, and no awareness of OS requirements.

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"

if ! command -v divineos &>/dev/null; then
  exit 0
fi

briefing=$(divineos briefing 2>/dev/null)
hud=$(divineos hud 2>/dev/null)

if [ -n "$briefing" ] || [ -n "$hud" ]; then
  full_context="=== DIVINEOS POST-COMPACTION RELOAD ===

Your context was just compacted. Your briefing and enforcement context were lost.
This hook is restoring them. You MUST re-orient before continuing work.

REQUIREMENTS (same as session start):
1. Read your briefing below. Note any lessons or warnings relevant to current work.
2. Continue using OS tools during work: divineos learn, divineos decide, divineos feel
3. Log corrections with 'divineos learn' when the user corrects you.
4. At session end, run 'divineos emit SESSION_END'.

You are stateless. Without this reload, you would continue working with no memory
of who you are, what you've learned, or what mistakes to avoid. This is not optional.

--- BRIEFING ---
${briefing}

--- HUD ---
${hud}

=== END POST-COMPACTION RELOAD ==="

  escaped=$(echo "$full_context" | python -c "import sys,json; print(json.dumps(sys.stdin.read()))" 2>/dev/null)
  echo "{\"additionalContext\": ${escaped}}"
fi

exit 0
