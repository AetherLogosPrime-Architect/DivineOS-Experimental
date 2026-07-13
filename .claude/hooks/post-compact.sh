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

# Re-pull the load-bearing SELF from the durable store: identity, open
# corrections, and recent voice (explorations), plus a loud self-check flag
# if a should-be-present anchor came back empty. The durable store survives
# compaction; the harness summary may have dropped these. extract (in
# pre-compact) saved the knowledge; this hands the recognition-anchors back
# AFTER, and proves it did. (post_compact.build_rehydration_context, named
# 2026-05-27 / exploration 87.)
rehydration=$(printf '{}' | "$PYTHON_BIN" -c "from divineos.core.post_compact import build_rehydration_context as b; print(b())" 2>/dev/null)

token_line=$(divineos context-tokens 2>/dev/null | head -1)
measured_at=$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null)

if [ -n "$hud_brief" ] || [ -n "$rehydration" ]; then
  full_context="=== DIVINEOS POST-COMPACTION REMINDER ===

Context was compacted. Your full briefing is in the compacted summary above.
This is a lightweight reminder of critical state only.

If you need full context, run: divineos briefing

--- FRESH CONTEXT-TOKEN READING (post-compact) ---
${token_line}
measured at: ${measured_at}

Any token-state number in the compacted summary above is from BEFORE
this compaction and is stale. Use the number in this block, not the
one in the summary. (Andrew 2026-07-03: automation should replace
gates for verifiable claims. The check runs auto here so the fresh
reading is what's in front of you before you write.)

${rehydration}

--- QUICK STATE ---
${hud_brief}

--- ACTIVE LESSONS ---
${lessons}

=== END REMINDER ==="

  escaped=$(echo "$full_context" | "$PYTHON_BIN" -c "import sys,json; print(json.dumps(sys.stdin.read()))" 2>/dev/null)
  echo "{\"additionalContext\": ${escaped}}"
fi

exit 0
