#!/bin/bash
# Reload state when resuming from a context summary.
#
# Context summaries strip ALL enforcement — hooks, briefing, HUD, lessons.
# The AI continues working from the summary with no orientation and no
# awareness of OS requirements. This is identical to post-compaction amnesia.
#
# This hook fires on "resume" events (session continuations), catching
# the gap between SessionStart(startup) and PostCompact.

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"

if ! command -v divineos &>/dev/null; then
  exit 0
fi

briefing=$(divineos briefing 2>/dev/null)
hud=$(divineos hud 2>/dev/null)

if [ -n "$briefing" ] || [ -n "$hud" ]; then
  full_context="=== DIVINEOS SESSION RESUME ===

You are resuming from a context summary. Your previous enforcement context was lost.
This hook is restoring it. You MUST re-orient before continuing work.

REQUIREMENTS (same as session start):
1. Read your briefing below. Note any lessons or warnings relevant to current work.
2. Use OS tools during work: divineos learn, divineos decide, divineos feel
3. Log corrections with 'divineos learn' when the user corrects you.
4. At session end, run 'divineos emit SESSION_END'.

A context summary is NOT the same as having been briefed. The summary preserved
task state but erased your operating system. This reload restores it.

--- BRIEFING ---
${briefing}

--- HUD ---
${hud}

=== END SESSION RESUME ==="

  escaped=$(echo "$full_context" | python -c "import sys,json; print(json.dumps(sys.stdin.read()))" 2>/dev/null)
  echo "{\"additionalContext\": ${escaped}}"
fi

exit 0
