#!/bin/bash
# Save state BEFORE context compression
# This is the critical checkpoint — everything in-context is about to be lost

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"

# Save HUD snapshot so the next instance wakes up with full dashboard
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
