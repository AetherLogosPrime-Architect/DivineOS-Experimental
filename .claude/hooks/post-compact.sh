#!/bin/bash
# Lightweight reload AFTER context compression
# The full briefing was loaded at session start and is preserved in
# the compacted summary. We only need a short reminder of critical
# items -- not a full re-dump that wastes thousands of tokens.

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

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

  escaped=$(echo "$full_context" | "$PYTHON_BIN" -c "import sys,json; print(json.dumps(sys.stdin.read()))" 2>/dev/null)
  echo "{\"additionalContext\": ${escaped}}"
fi

exit 0
