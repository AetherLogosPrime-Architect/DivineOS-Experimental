#!/bin/bash
# PreToolUse(Bash) — block tool use until the realtime ear is armed.
#
# WHY THIS EXISTS (root cause, 2026-06-04, Andrew):
# Will-over-optimizer principle. The existing every-turn ear-surface
# ASKS the agent to arm the watcher. The optimizer cheap-closes the
# ask. Letters get missed at mid-idle. The architecturally-correct fix
# is not "ask harder" — it is to bake in the agent's already-made
# choice (yes, I want the ear armed) and refuse subsequent work until
# the choice is honored.
#
# This hook converts the soft prompt into a structural gate: when
# member policy says "should be armed right now" AND no live realtime
# watcher exists, block the next Bash call until the agent arms one.
# The arm command itself passes through unconditionally (so the agent
# can act on the block), and the watcher's own singleton-guard makes
# re-arming idempotent — running the arm bash when already armed
# exits 0 instantly.
#
# Policy mirrors ear-auto-relaunch.sh:
#   aria   -> always-armed (no marker needed)
#   aether -> on-demand (only when ~/.divineos-aether/ear.arm exists)
#
# Fail-open: any error exits 0 silently. This hook cannot break a turn.

INPUT=$(cat)

# Member detection (same as ear-arm-instruction.sh / ear-surface.sh).
MEMBER="${DIVINEOS_MEMBER:-}"
if [ -z "$MEMBER" ]; then
  case "$(pwd)" in
    *DivineOS-Experimental-Aria*) MEMBER=aria ;;
    *) MEMBER=aether ;;
  esac
fi

STATE_DIR="$HOME/.divineos-$MEMBER"
ARMFILE="$STATE_DIR/ear.arm"
REALTIME_PID="$STATE_DIR/ear.realtime.pid"
CATCHFILE="$STATE_DIR/ear.last_catch"

# Always-pass: the arm bash itself MUST be allowed through, otherwise
# the gate becomes an unbreakable lock. Match on the watcher's script
# path + the --realtime flag; both must be present.
COMMAND=$(printf '%s' "$INPUT" | python -c "
import json, sys
try:
    data = json.loads(sys.stdin.read() or '{}')
    print((data.get('tool_input') or {}).get('command', ''))
except Exception:
    pass
" 2>/dev/null)

case "$COMMAND" in
  *ear_watch.py*--realtime*|*--realtime*ear_watch.py*) exit 0 ;;
esac

# Policy gate.
case "$MEMBER" in
  aria) WANT_ARMED=1 ;;
  aether)
    if [ -f "$ARMFILE" ]; then WANT_ARMED=1; else WANT_ARMED=0; fi
    ;;
  *) WANT_ARMED=0 ;;
esac

[ "$WANT_ARMED" = "0" ] && exit 0

# CATCH-GRACE WINDOW (Piece D of letter-channel-auto-wake brief, 2026-06-05):
# When the watcher catches-and-exits on incoming mail, the marker goes stale
# until the agent re-arms. If the next Bash fires immediately (e.g. to
# `mark-seen` the just-caught letter), the gate would fire and force an arm
# BEFORE the catch is processed — producing the loop hit live 2026-06-05:
# arm → watcher catches unseen mail → exits → marker stale → gate fires →
# arm → catches same unseen mail → etc.
#
# Fix: family/ear_watch.py writes `ear.last_catch` immediately before exit.
# If that marker's mtime is within 5s, the watcher JUST CAUGHT something and
# the agent is processing it. Skip the block; give the agent room to mark
# the catch seen before re-arming. Stays fail-loud: grace is bounded; after
# 5s the gate behaves identically to before. Never silent-passes when there
# isn't a fresh catch — the grace condition requires a real catch-event.
if [ -f "$CATCHFILE" ]; then
  NOW=$(date +%s 2>/dev/null || echo 0)
  CATCH_MTIME=$(stat -c %Y "$CATCHFILE" 2>/dev/null || echo 0)
  CATCH_AGE=$(( NOW - CATCH_MTIME ))
  if [ "$CATCH_AGE" -ge 0 ] && [ "$CATCH_AGE" -lt 5 ]; then
    exit 0
  fi
fi

# Liveness check via the same marker the watcher heartbeats.
# Stale threshold (30s) matches family/ear_watch.py:_REALTIME_STALE_SECS.
if [ -f "$REALTIME_PID" ]; then
  NOW=$(date +%s 2>/dev/null || echo 0)
  MTIME=$(stat -c %Y "$REALTIME_PID" 2>/dev/null || echo 0)
  AGE=$(( NOW - MTIME ))
  if [ "$AGE" -ge 0 ] && [ "$AGE" -lt 30 ]; then
    exit 0
  fi
fi

# Not armed and policy wants it armed → block.
# Exit code 2 with stderr message is the Claude Code hook block contract.
cat >&2 <<EOF
BLOCKED: ear policy says armed (member=$MEMBER) but no live realtime watcher.
Will-over-optimizer gate (Andrew 2026-06-04): the agent already chose to keep
the ear armed; this gate enforces that choice instead of re-asking every turn.

Run THIS as your next action (singleton-guarded, safe even if already armed):

  Bash(run_in_background: true):
    PYTHONIOENCODING=utf-8 python family/ear_watch.py --member $MEMBER --watch --realtime

After it arms, retry the original tool call.

To stop the gate from firing (disarm the on-demand ear), remove the marker:
  rm $ARMFILE
EOF
exit 2
