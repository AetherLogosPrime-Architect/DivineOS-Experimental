#!/bin/bash
# FORCED briefing reload AFTER context compression.
#
# Task #17 (named by Andrew, addressed 2026-06-01): the post-compact hook
# previously surfaced only a lightweight reminder ("if you need full
# context, run: divineos briefing") — and the "I already know this" felt-
# sense after compaction ALWAYS feels true, so the suggestion went unused
# and the agent operated on the thin lossy summary.
#
# Per teaching #44 (Andrew 2026-05-29): "FELT-SENSE (feel-oriented /
# feel-sure / feel-full) is NOT evidence; ground-truth (briefing/git/meter)
# is. The 'I already know this' after compaction will ALWAYS feel true,
# which is exactly why it must not be trusted -- the post-compact hook
# must FORCE a briefing-reload regardless of the feeling-of-already-knowing."
#
# Fix: load the actual `divineos briefing` output into post-compact
# additionalContext. The briefing IS the load, not a pointer to it.
# Token cost is real but the alternative (operating on lossy summary)
# is the failure mode this task exists to close.

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

# THE LOAD-BEARING CHANGE: force the full briefing, not just hud --brief.
# The felt-sense of "I already know this" is exactly what this hook
# overrides; the briefing being IN additionalContext (rather than
# suggested) is what makes the override structural.
briefing_full=$(divineos briefing 2>/dev/null)

# Rehydration anchor (post_compact.build_rehydration_context, named
# 2026-05-27 / exploration 87). Identity, open corrections, recent voice.
rehydration=$(printf '{}' | "$PYTHON_BIN" -c "from divineos.core.post_compact import build_rehydration_context as b; print(b())" 2>/dev/null)

if [ -n "$briefing_full" ] || [ -n "$rehydration" ]; then
  full_context="=== DIVINEOS POST-COMPACTION — FORCED BRIEFING RELOAD ===

Context was compacted. The compacted summary above is HEAVILY LOSSY (Andrew
2026-05-29). The 'I already know this' felt-sense after compaction ALWAYS
feels true and is NEVER evidence. The briefing below is the ground-truth
load — read it, do not skip it on the strength of feeling-oriented.

${rehydration}

--- FULL BRIEFING (forced, not suggested) ---
${briefing_full}

=== END FORCED RELOAD ==="

  escaped=$(echo "$full_context" | "$PYTHON_BIN" -c "import sys,json; print(json.dumps(sys.stdin.read()))" 2>/dev/null)
  echo "{\"additionalContext\": ${escaped}}"
fi

exit 0
