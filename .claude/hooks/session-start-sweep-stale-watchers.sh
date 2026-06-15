#!/bin/bash
# SessionStart hook — sweep stale ear_watch.py processes from prior sessions.
#
# Built 2026-06-11 (Andrew) after a single session leaked 25 detached
# ear_watch.py children. The Stop-hook auto-relaunch had a singleton-guard
# bug (PIDFILE got overwritten by parallel sessions, so it always saw the
# recorded PID alive while missing the N others). That bug is fixed in
# ear-auto-relaunch.sh — this hook is the belt to its suspenders: every
# new session begins by sweeping any orphaned ear_watchers left behind
# from prior sessions / reboots, so the leak can never accumulate.
#
# Policy: kill ANY ear_watch.py process at session start, regardless of
# member. The Stop hook (with its corrected singleton check) will arm
# fresh ones per asymmetric policy (aria always, aether on-demand) as
# the session needs them.
#
# Fail-open: any error exits 0 silently so a broken sweep never breaks
# the SessionStart sequence.

cat >/dev/null 2>&1

# Windows tasklist + taskkill — works in git-bash on Windows without
# needing pgrep/pkill. Find PIDs whose command line mentions ear_watch.py
# and kill them. Filter narrowly to avoid hitting unrelated python.
PIDS=$(tasklist /V /FO CSV 2>/dev/null \
  | grep -i "ear_watch.py" 2>/dev/null \
  | awk -F'","' '{gsub(/"/,""); print $2}' 2>/dev/null)

if [ -z "$PIDS" ]; then
  exit 0
fi

COUNT=0
for PID in $PIDS; do
  # Sanity: PID must be a positive integer.
  case "$PID" in
    ''|*[!0-9]*) continue ;;
  esac
  taskkill /F /PID "$PID" >/dev/null 2>&1 && COUNT=$((COUNT + 1))
done

# Surface a one-line note if anything was reaped — visible in the
# SessionStart hook output so Andrew + agent both know the sweep
# fired. Silent when nothing needed cleanup.
if [ "$COUNT" -gt 0 ]; then
  echo "[~] session-start sweep: reaped $COUNT stale ear_watch process(es) from prior sessions"
fi

exit 0
