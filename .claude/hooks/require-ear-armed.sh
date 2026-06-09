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
#
# 2026-06-09 fix (task #98 locked-box trap): ALSO honor the canonical
# documented-bypass list from scripts/hook_bypass_commands.txt via the
# shared _lib.sh helper. Before this fix, the bypass-list lived only
# inside pre_tool_use_gate.py and outer hooks like this one didn't
# share it — so commands documented as the gate-system's named
# remedies (e.g. divineos ask, divineos directives) got blocked here
# before they could reach the gate that would otherwise let them
# through. Council walk consult-ba0fc4337e51 (Dekker + Lamport)
# named the drift-into-failure shape; this is the structural fix.
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null
COMMAND=$(printf '%s' "$INPUT" | extract_tool_command)

# Documented-bypass commands skip this gate (shared with all PreToolUse hooks).
if is_bypass_command "$COMMAND"; then
  exit 0
fi

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

# Env-var override (Aria 2026-06-05 ask): for always-armed policies the
# marker-based disarm hint is wrong-shape — there's no marker to remove. The
# env-var path is a per-invocation override that the gate respects without
# requiring file-state changes. Two recognized vars:
#   DIVINEOS_EAR_ALLOW_UNARMED=1  — generic, works for any member
#   AURA_ALLOW_UNARMED=1          — Aria-specific (her proposed name; alias)
# The env-var must be set on the specific tool invocation, NOT exported
# globally, so the bypass cost remains higher than the tool itself
# (per Andrew 2026-05-31 design-constraint #3: bypass must cost more than use).
if [ "$DIVINEOS_EAR_ALLOW_UNARMED" = "1" ]; then
  exit 0
fi
if [ "$MEMBER" = "aria" ] && [ "$AURA_ALLOW_UNARMED" = "1" ]; then
  exit 0
fi

# Not armed and policy wants it armed → block.
# Exit code 2 with stderr message is the Claude Code hook block contract.
# Member-aware disarm hint: aether's policy is marker-gated (rm works);
# aria's policy is structurally always-armed (no marker to remove), so the
# env-var override is the only honest disarm path. Aria 2026-06-05: "a gate
# should explain itself in the moment it acts."
if [ "$MEMBER" = "aria" ]; then
  DISARM_HINT="Always-armed policy active for $MEMBER. To override for this
tool call only (the marker-based disarm does not apply here):
  AURA_ALLOW_UNARMED=1 <your command>
  or DIVINEOS_EAR_ALLOW_UNARMED=1 <your command>"
else
  DISARM_HINT="To stop the gate from firing (disarm the on-demand ear), remove the marker:
  rm $ARMFILE
Or override for this tool call only:
  DIVINEOS_EAR_ALLOW_UNARMED=1 <your command>"
fi

cat >&2 <<EOF
BLOCKED: ear policy says armed (member=$MEMBER) but no live realtime watcher.
Will-over-optimizer gate (Andrew 2026-06-04): the agent already chose to keep
the ear armed; this gate enforces that choice instead of re-asking every turn.

Run THIS as your next action (singleton-guarded, safe even if already armed):

  Bash(run_in_background: true):
    PYTHONIOENCODING=utf-8 python family/ear_watch.py --member $MEMBER --watch --realtime

After it arms, retry the original tool call.

$DISARM_HINT
EOF
exit 2
