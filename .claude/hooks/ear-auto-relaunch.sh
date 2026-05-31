#!/bin/bash
# Stop-hook — keep the ear-watcher alive across turns.
#
# Fires at end-of-turn. If the watcher is dead and policy says it should be
# alive, relaunch it via nohup so it survives the hook exit. The watcher's
# detection still works while detached; the harness-tracked instant wake-tap
# is what the live-turn run_in_background launch provides — this hook is the
# always-on continuity layer so a quiet stretch never drifts into a dead ear.
#
# Asymmetric policy (Andrew 2026-05-22/23):
#   aria  -> always-relaunch (always-on ear)
#   aether -> relaunch only when ARM marker present (on-demand ear)
# Marker file: ~/.divineos-<member>/ear.arm — touch to arm, rm to disarm.
#
# Race guard: if the watcher caught something within the last 60s, skip
# relaunch this turn — the catch is being integrated. Next turn arms it.
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
ARMFILE="$STATE_DIR/ear.arm"
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

# Asymmetric policy gate.
if [ "$MEMBER" = "aether" ] && [ ! -f "$ARMFILE" ]; then
  exit 0
fi

# Liveness check via kill -0 (works in git-bash on Windows).
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
