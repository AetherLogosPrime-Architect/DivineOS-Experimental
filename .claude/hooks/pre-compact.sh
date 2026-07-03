#!/bin/bash
# Save state BEFORE context compression
# This is the critical checkpoint — everything in-context is about to be lost.
# If extraction doesn't fire here, all session knowledge evaporates.
#
# 2026-07-02 Fable audit finding #5: this hook previously called bare
# `divineos extract` / `divineos hud --save` / `divineos log` without
# sourcing _lib.sh. On a stale-venv / wrong-python condition — the exact
# class _lib.sh was built to eliminate across 11 other hooks in round-2
# — extract exits non-zero, a line goes into a log file nobody watches,
# and the hook exits 0 → workflow uninterrupted, session knowledge gone.
#
# Fix: route through find_divineos_python like every other divineos-
# importing hook, and make extract failure LOUD via stderr banners the
# operator will actually see. This is the one hook where fail-loud
# beats fail-open: a lost checkpoint is not recoverable, and a visible
# banner is the lesser cost than silent knowledge evaporation.

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo ".")" || exit 0

# Source _lib.sh for find_divineos_python. If sourcing fails, we cannot
# even resolve which python has divineos — emit a LOUD banner so the
# operator sees that pre-compact save is compromised, then exit 0 so
# compaction itself still proceeds (silent knowledge loss is worse than
# the compaction going through with a visible warning).
# shellcheck disable=SC1091
if ! source "$(git rev-parse --show-toplevel)/.claude/hooks/_lib.sh" 2>/dev/null; then
    echo "" >&2
    echo "  !!! PRE-COMPACT: _lib.sh sourcing failed — cannot resolve python" >&2
    echo "  !!! Session knowledge extraction is NOT running for this compaction" >&2
    echo "  !!! Check .claude/hooks/_lib.sh exists and is readable" >&2
    echo "" >&2
    exit 0
fi

PYTHON_BIN="$(find_divineos_python)"
if [ -z "$PYTHON_BIN" ]; then
    echo "" >&2
    echo "  !!! PRE-COMPACT: find_divineos_python returned empty" >&2
    echo "  !!! No python with divineos installed found — extraction NOT running" >&2
    echo "  !!! Session knowledge from this compaction will be LOST" >&2
    echo "  !!! Fix: activate project venv or run 'pip install -e .' in project root" >&2
    echo "" >&2
    exit 0
fi

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
#
# Extract failure was previously logged to $save_log only. Now it also
# emits a loud stderr banner so the operator sees the failure in the
# live output rather than only after grepping the log file later.
extract_ok=1
{
  echo "=== pre-compact save @ $stamp ==="
  if "$PYTHON_BIN" -m divineos extract; then
    echo "=== extract OK ==="
  else
    extract_exit=$?
    echo "=== EXTRACT FAILED (exit $extract_exit) — session knowledge may be lost ==="
    extract_ok=0
  fi
  # HUD snapshot (extract does this too, but belt-and-suspenders)
  "$PYTHON_BIN" -m divineos hud --save
  echo "=== save complete ==="
} >"$save_log" 2>&1

# Fail-loud on extract failure — the operator sees this even if the
# log file is never opened. Silent extract failure was the vector Fable
# named as the specific class the fix targets.
if [ "$extract_ok" -eq 0 ]; then
    echo "" >&2
    echo "  !!! PRE-COMPACT: divineos extract FAILED (see $save_log for details)" >&2
    echo "  !!! Session knowledge from this compaction may be LOST" >&2
    echo "  !!! Consider re-running 'divineos extract' manually before continuing" >&2
    echo "" >&2
fi

# Gather current state for the ledger
files_modified=$(git diff --name-only HEAD 2>/dev/null | head -20 | tr '\n' ', ')
branch=$(git branch --show-current 2>/dev/null || echo "unknown")
last_commit=$(git log --oneline -1 2>/dev/null || echo "none")

# Save checkpoint via divineos (record where the save log landed so a
# failed/partial save is auditable after the fact, not lost to /dev/null)
"$PYTHON_BIN" -m divineos log \
  --type AGENT_CONTEXT_COMPRESSION \
  --actor agent \
  --content "Pre-compact checkpoint: branch=$branch, last_commit=$last_commit, save_log=$save_log, modified=[$files_modified], extract_ok=$extract_ok" \
  2>/dev/null

exit 0
