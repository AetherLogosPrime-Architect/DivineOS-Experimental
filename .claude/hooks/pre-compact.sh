#!/bin/bash
# Save state BEFORE context compression
# This is the critical checkpoint — everything in-context is about to be lost.
# If SESSION_END doesn't fire here, all session knowledge evaporates.

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"

if ! command -v divineos &>/dev/null; then
  exit 0
fi

# CRITICAL: Emit SESSION_END before compaction destroys context.
# This triggers the full learning pipeline — knowledge extraction,
# feedback, lessons, handoff notes. Without this, the session is lost.
divineos emit SESSION_END 2>/dev/null

# Also save HUD snapshot (SESSION_END does this too, but belt-and-suspenders)
divineos hud --save 2>/dev/null

# Gather current state for the ledger
files_modified=$(git diff --name-only HEAD 2>/dev/null | head -20 | tr '\n' ', ')
branch=$(git branch --show-current 2>/dev/null || echo "unknown")
last_commit=$(git log --oneline -1 2>/dev/null || echo "none")

# Save checkpoint via divineos
divineos log \
  --type AGENT_CONTEXT_COMPRESSION \
  --actor agent \
  --content "Pre-compact checkpoint: branch=$branch, last_commit=$last_commit, modified=[$files_modified]" \
  2>/dev/null

exit 0
