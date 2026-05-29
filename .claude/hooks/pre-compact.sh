#!/bin/bash
# Save state BEFORE context compression
# This is the critical checkpoint — everything in-context is about to be lost.
# If extraction doesn't fire here, all session knowledge evaporates.

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo ".")" || exit 0

# Leave a visible trace of every pre-compact save. NOT /dev/null —
# a silent save is indistinguishable from a failed save, and a failed
# save here is exactly how a whole session's work gets lost without
# anyone noticing (measured 2026-05-29: extract takes ~64s; the old
# 15s hook timeout killed it mid-write every time, silently).
log_dir="data/checkpoints"
mkdir -p "$log_dir" 2>/dev/null
stamp="$(date +%Y%m%d-%H%M%S)"
save_log="$log_dir/pre-compact-$stamp.log"

# CRITICAL: Extract knowledge before compaction destroys context.
# The full learning pipeline takes ~60s+; the PreCompact timeout in
# settings.json MUST exceed that or the save is killed mid-write.
{
  echo "=== pre-compact save @ $stamp ==="
  if divineos extract; then
    echo "=== extract OK ==="
  else
    echo "=== EXTRACT FAILED (exit $?) — session knowledge may be lost ==="
  fi
  # HUD snapshot (extract does this too, but belt-and-suspenders)
  divineos hud --save
  echo "=== save complete ==="
} >"$save_log" 2>&1

# Gather current state for the ledger
files_modified=$(git diff --name-only HEAD 2>/dev/null | head -20 | tr '\n' ', ')
branch=$(git branch --show-current 2>/dev/null || echo "unknown")
last_commit=$(git log --oneline -1 2>/dev/null || echo "none")

# Save checkpoint via divineos (record where the save log landed so a
# failed/partial save is auditable after the fact, not lost to /dev/null)
divineos log \
  --type AGENT_CONTEXT_COMPRESSION \
  --actor agent \
  --content "Pre-compact checkpoint: branch=$branch, last_commit=$last_commit, save_log=$save_log, modified=[$files_modified]" \
  2>/dev/null

exit 0
