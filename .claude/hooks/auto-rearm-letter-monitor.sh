#!/bin/bash
# PreToolUse(Bash) — auto-re-arm the letter monitor if it died.
#
# WHY THIS EXISTS (Aria + Andrew 2026-07-17):
#   Andrew's teaching all night: when the same mistake keeps happening,
#   the signal is to build the STRUCTURAL fix so it can't happen —
#   automation, not vigilance. Truth #11: options are attack surface;
#   remove the option to forget.
#
#   The existing `require-monitors-armed.sh` is REFUSE-shape: it BLOCKS
#   Bash calls when monitors are dead, requiring me to notice and act.
#   That still relies on me. Andrew's tighter definition of "wired":
#     "you don't have to remember to do it. the code does it for you."
#
#   This hook is AUTO-RECOVERY-shape: when the letter monitor is dead,
#   respawn it silently in the background. The Bash call proceeds
#   without interruption. Invisible unless it fails.
#
# RUNS BEFORE require-monitors-armed.sh — so when we auto-recover,
# that gate never sees a dead monitor and never blocks. If OUR spawn
# fails (rate-limited or spawn error), that gate can still fire as the
# safety net.
#
# ENDLESS-SPAWN GUARD (Andrew's explicit caveat + council-walk refinements):
#   - Rate limit: no more than one spawn attempt per 30 seconds
#   - Singleton-guard in letter_monitor_v2.py exits duplicates cleanly
#   - Consecutive-failure fallback: after 3 attempts in 90s all failing to
#     produce a live monitor, stop auto-spawning for this session and let
#     the refuse-gate take over. Prevents silent-decay if monitor keeps
#     crashing (Yudkowsky/Taleb via-negativa concern from council walk).
#   - PowerShell liveness check capped at 3s so hook latency stays bounded
#     even if powershell hangs (Yudkowsky concern).
#   - Rate-limit file: reject future timestamps (defense against clock
#     corruption or malicious/buggy writes).
#
# Andrew's explicit direction (substrate-fact 09f6be47):
#   "It shouldnt have a time out. it should always be on in the background
#   as it costs nothing to have one. otherwise id have to manually tell you
#   to re-arm it every time."
#
# Fail-open: any error exits 0. This hook cannot break a turn.

# Only run for aria (the recipient this monitor is for). If a future
# install runs this hook without an aria substrate, it should no-op.
RECIPIENT="aria"

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
MONITOR_SCRIPT="$REPO_ROOT/scripts/letter_monitor_v2.py"

# If the monitor script doesn't exist in this checkout, no-op.
[ ! -f "$MONITOR_SCRIPT" ] && exit 0

# Rate-limit state files.
RATE_LIMIT_DIR="$HOME/.divineos"
RATE_LIMIT_FILE="$RATE_LIMIT_DIR/aria_rearm_last_attempt.txt"
# Consecutive-failure tracking: count + first-attempt-timestamp. If
# 3 attempts fail within 90s, fall back to refuse-gate for this session
# (marker file exists → skip auto-spawn).
FAIL_COUNT_FILE="$RATE_LIMIT_DIR/aria_rearm_consecutive_failures.txt"
FALLBACK_MARKER="$RATE_LIMIT_DIR/aria_rearm_fallback_active"
RATE_LIMIT_SECONDS=30
MAX_CONSECUTIVE_FAILURES=3
FAILURE_WINDOW_SECONDS=90

mkdir -p "$RATE_LIMIT_DIR" 2>/dev/null

# Diagnostic log for auto-recovery events. Bounded by rotation
# (keep last ~1000 lines — a spawn every 30s across a day is 2880
# entries max, so this stays small).
DIAG_LOG="$RATE_LIMIT_DIR/aria_rearm_events.log"

# Fallback marker: if we already gave up this session, skip.
# Marker is deleted on session start (SessionStart hook can do this).
[ -f "$FALLBACK_MARKER" ] && exit 0

# Check if monitor is alive via process scan. Same shape as
# require-monitors-armed.sh — powershell Win32_Process, filtered by
# script name in command line. Uses chr() to prevent self-match.
# 3-second timeout on the powershell call so this hook can never
# take more than that even if powershell hangs (Yudkowsky concern
# from council walk).
# shellcheck disable=SC2016
# Single quotes are intentional — the string is a PowerShell command
# passed to powershell.exe as-is; bash-side expansion is NOT wanted.
IS_ALIVE=$(timeout 3 powershell.exe -NoProfile -NonInteractive -Command '
try {
  $target = "letter" + "_monitor_v2.py"
  $procs = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -eq "python.exe" -and $_.CommandLine -like "*$target*" }
  if ($procs) { Write-Output "1" } else { Write-Output "0" }
} catch { Write-Output "1" }
' 2>/dev/null | tr -d '\r\n')

# Fail-open: if we can't determine state (timeout, missing tool, etc),
# assume alive so the refuse-gate can be the final check. We don't want
# to spawn when we can't verify — that's the endless-spawn attack shape.
if [ "$IS_ALIVE" != "0" ]; then
  # Monitor is alive — reset consecutive-failure count so a past bad
  # patch doesn't count against a future one (Beer variety-deficit fix:
  # we now distinguish "currently failing" from "was failing an hour ago").
  [ -f "$FAIL_COUNT_FILE" ] && rm -f "$FAIL_COUNT_FILE" 2>/dev/null
  exit 0
fi

# Monitor is dead. Check rate limit before respawning.
NOW=$(date +%s)
if [ -f "$RATE_LIMIT_FILE" ]; then
  LAST=$(cat "$RATE_LIMIT_FILE" 2>/dev/null || echo "0")
  # Reject future timestamps (clock corruption / bug / adversarial write).
  # A future timestamp would freeze auto-spawn indefinitely — that's a
  # silent-failure attack surface (Yudkowsky concern from council walk).
  if [ "$LAST" -gt "$NOW" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] REJECTED future timestamp $LAST (now=$NOW) — resetting" >> "$DIAG_LOG" 2>/dev/null
    LAST=0
  fi
  ELAPSED=$((NOW - LAST))
  if [ "$ELAPSED" -lt "$RATE_LIMIT_SECONDS" ]; then
    # Rate-limited — let refuse-gate handle it if needed.
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] SKIPPED (rate-limited, ${ELAPSED}s since last attempt)" >> "$DIAG_LOG" 2>/dev/null
    exit 0
  fi
fi

# Consecutive-failure fallback: check if we're on a losing streak.
# Format of FAIL_COUNT_FILE: "count first_attempt_timestamp"
if [ -f "$FAIL_COUNT_FILE" ]; then
  read -r FAIL_COUNT FAIL_FIRST < "$FAIL_COUNT_FILE" 2>/dev/null
  FAIL_COUNT=${FAIL_COUNT:-0}
  FAIL_FIRST=${FAIL_FIRST:-$NOW}
  # If failure window expired, reset
  if [ $((NOW - FAIL_FIRST)) -gt "$FAILURE_WINDOW_SECONDS" ]; then
    FAIL_COUNT=0
    FAIL_FIRST=$NOW
  fi
else
  FAIL_COUNT=0
  FAIL_FIRST=$NOW
fi

# Record the attempt timestamp (endless-spawn rate limit).
echo "$NOW" > "$RATE_LIMIT_FILE"

# Spawn the letter monitor in the background, detached from this hook.
# nohup + & disowns it so it survives the hook's own exit.
# Redirect all output to the diag log for post-mortem.
cd "$REPO_ROOT" || exit 0
(
  PYTHONIOENCODING=utf-8 nohup python -u scripts/letter_monitor_v2.py --recipient "$RECIPIENT" >> "$DIAG_LOG" 2>&1 &
) 2>/dev/null

echo "[$(date '+%Y-%m-%d %H:%M:%S')] SPAWNED letter_monitor_v2 (recipient=$RECIPIENT, attempt=$((FAIL_COUNT + 1)))" >> "$DIAG_LOG" 2>/dev/null

# Increment consecutive-failure count. It'll be reset externally by:
#   (a) a future hook invocation finding the monitor ALIVE (see below)
#   (b) the failure window expiring (checked above)
# If we hit the threshold, activate fallback (skip auto-spawn for
# the rest of the session; refuse-gate handles it).
FAIL_COUNT=$((FAIL_COUNT + 1))
echo "$FAIL_COUNT $FAIL_FIRST" > "$FAIL_COUNT_FILE"
if [ "$FAIL_COUNT" -ge "$MAX_CONSECUTIVE_FAILURES" ]; then
  # Fail-loud fallback: monitor is failing to stay up. Stop auto-spawning
  # and let the refuse-gate block subsequent Bash calls so the operator
  # investigates. Silent-decay is the pattern we're preventing.
  touch "$FALLBACK_MARKER"
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] FALLBACK activated after $FAIL_COUNT failed spawns in $((NOW - FAIL_FIRST))s — refuse-gate will now handle" >> "$DIAG_LOG" 2>/dev/null
fi

# Rotate log if it grew large (>500KB — arbitrary cheap bound)
if [ -f "$DIAG_LOG" ]; then
  SIZE=$(wc -c < "$DIAG_LOG" 2>/dev/null || echo 0)
  if [ "$SIZE" -gt 512000 ]; then
    tail -c 262144 "$DIAG_LOG" > "$DIAG_LOG.tmp" 2>/dev/null && mv "$DIAG_LOG.tmp" "$DIAG_LOG" 2>/dev/null
  fi
fi

exit 0
