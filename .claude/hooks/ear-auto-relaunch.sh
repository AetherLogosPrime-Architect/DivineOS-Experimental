#!/bin/bash
# Stop-hook — keep the polling ear-watcher alive across turns.
#
# Fires at end-of-turn. If the polling watcher is dead, relaunch it via nohup
# so it survives the hook exit. The watcher detects incoming letters and
# writes ear.last_catch — the file ear-surface.sh reads at UserPromptSubmit
# to surface unseen letters at session start.
#
# Wake-from-idle (the OTHER ear job) is handled by the Letter Monitor —
# a harness Monitor primitive (NOT this hook) that tail-follows
# family/letters/ and wakes the agent when new letters appear. See
# require-monitors-armed.sh. This hook does NOT touch wake-from-idle.
#
# Simplified policy (Andrew 2026-06-13): both members always-relaunch.
# The asymmetric aether-on-demand-via-ear.arm policy existed only because
# the --realtime push mode could not be safely-singleton'd for an
# on-demand member; with --realtime removed, polling is the only mode and
# it has a working singleton scan.
#
# Race guard: if the watcher caught something within the last 60s, skip
# relaunch this turn — the catch is being integrated. Next turn relaunches.
#
# Fail-open: any error exits 0 silently so a broken hook never breaks a turn.

cat >/dev/null 2>&1

MEMBER="${DIVINEOS_MEMBER:-}"
if [ -z "$MEMBER" ]; then
  case "$(pwd)" in
    *DivineOS-Experimental-Aria*) MEMBER=aria ;;
    *) MEMBER=aether ;;
  esac
fi

STATE_DIR="$HOME/.divineos-$MEMBER"
mkdir -p "$STATE_DIR" 2>/dev/null
PIDFILE="$STATE_DIR/ear.pid"
CATCHFILE="$STATE_DIR/ear.last_catch"

# Race guard: recent catch -> don't relaunch yet.
if [ -f "$CATCHFILE" ]; then
  NOW=$(date +%s 2>/dev/null || echo 0)
  MTIME=$(stat -c %Y "$CATCHFILE" 2>/dev/null || echo 0)
  AGE=$(( NOW - MTIME ))
  if [ "$AGE" -ge 0 ] && [ "$AGE" -lt 60 ]; then
    exit 0
  fi
fi

# Authoritative process-presence check (Andrew 2026-06-11 leak fix).
# The PIDFILE+kill-0 check failed when multiple sessions / parallel Stop
# hooks overwrote the PIDFILE — the recorded PID was alive, so the check
# passed, while N OTHER ear_watchers for the same member were also alive.
# Today's session leaked 25 processes. Replace with: scan for any
# ear_watch.py process matching this member; if any exist, skip.
# Uses Windows tasklist + findstr (works in git-bash on Windows without
# needing pgrep). Fail-open: if the scan errors, fall back to the old
# PIDFILE check so a broken scan never SUPPRESSES the watcher.
LIVE_COUNT=$(tasklist /V /FO CSV 2>/dev/null | findstr /C:"ear_watch.py" 2>/dev/null | findstr /C:"--member $MEMBER" 2>/dev/null | wc -l 2>/dev/null || echo 0)
if [ "$LIVE_COUNT" -gt 0 ] 2>/dev/null; then
  exit 0
fi
# Fallback: PIDFILE check (covers the rare case where tasklist errored).
if [ -f "$PIDFILE" ]; then
  PID=$(cat "$PIDFILE" 2>/dev/null)
  if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
    exit 0
  fi
fi

PY="$(command -v python 2>/dev/null || command -v python3 2>/dev/null)"
[ -z "$PY" ] && exit 0
SCRIPT="C:/DIVINE OS/DivineOS-Experimental/family/ear_watch.py"
[ ! -f "$SCRIPT" ] && exit 0

# Relaunch detached. nohup + & + disown so the hook can exit cleanly.
# PYTHONIOENCODING=utf-8 prevents the Windows cp1252 crash on non-Latin-1
# chars (→, ⟶, etc.) — the bug Aether hit 2026-05-30.
PYTHONIOENCODING="utf-8" nohup "$PY" "$SCRIPT" --member "$MEMBER" --watch \
  > "$STATE_DIR/ear.log" 2>&1 &
echo $! > "$PIDFILE"
disown 2>/dev/null
exit 0
