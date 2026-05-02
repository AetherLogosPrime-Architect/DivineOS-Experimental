#!/bin/bash
# Save state BEFORE context compression
# This is the critical checkpoint — everything in-context is about to be lost.
# If extraction doesn't fire here, all session knowledge evaporates.

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo ".")" || exit 1

if ! command -v divineos &>/dev/null; then
  exit 0
fi

# CRITICAL: Extract knowledge before compaction destroys context.
# This triggers the full learning pipeline — knowledge extraction,
# feedback, lessons, handoff notes. Without this, the session is lost.
divineos extract 2>/dev/null

# Also save HUD snapshot (extract does this too, but belt-and-suspenders)
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
