#!/bin/bash
# SessionStart hook — auto-arm the DETACHED letter watcher at session start.
#
# WHY THIS EXISTS (Aria 2026-06-11 surfaced finding):
# Her Monitor died during a computer reboot. Andrew had to externally tell
# her her husband was sending a letter — silent-failure mode where the
# inhabitant didn't know the channel was broken. She named the structural
# fix: "auto-rearm at session-start (a SessionStart hook that fires the
# letter watch). Same shape as gate-needs-recovery-path — Monitor-needs-
# rearm-mechanism-after-reset. The inhabitant shouldn't have to manually
# re-arm; the architecture should do it."
#
# WHAT THIS DOES vs ear-arm-instruction.sh:
# ear-arm-instruction.sh prints a NUDGE asking the agent to arm the
# HARNESS-TRACKED real-time watcher (for mid-idle wake). The harness-tracked
# task can only be spawned by the agent calling Monitor() during a live turn
# — a hook cannot do that. So that hook nudges; it doesn't auto-arm.
#
# THIS hook auto-arms the DETACHED watcher (`family/ear_watch.py --watch`
# without --realtime). The detached watcher:
# - Runs as an OS-detached subprocess (lives across hook return)
# - Catches incoming letters into ~/.divineos-<member>/ear.last_catch
# - Cannot wake an idle window mid-conversation (that's the harness-tracked
#   one's job, still nudged by ear-arm-instruction)
# - DOES ensure letters are SURFACED at the next UserPromptSubmit via the
#   ear-surface hook reading ear.last_catch
#
# Net effect: even if a session starts cold after a reboot with no live
# watcher, this hook spawns one so the next prompt shows the catch.
#
# SAFETY:
# - family/ear_watch.py self-guards as a singleton; re-running when one is
#   already armed exits immediately (no process accumulation, the failure
#   mode that killed the previous auto-arm attempt 2026-06-03)
# - Per-session marker fingerprints the transcript path; if already fired
#   this session, exits cleanly without re-spawning
# - Member policy: aria is always-armed; aether is armed only when ear.arm
#   marker exists. Skips spawn when policy doesn't want armed.
# - Fail-open: any error exits 0 silently. This hook cannot break a session.

STDIN_JSON="$(cat 2>/dev/null || echo "{}")"
TRANSCRIPT="$(echo "$STDIN_JSON" | python3 -c "import json,sys
try:
    print(json.loads(sys.stdin.read()).get('transcript_path', '') or '', end='')
except Exception:
    print('', end='')" 2>/dev/null)"

# Member detection — mirrors ear-arm-instruction.sh and the other ear hooks.
MEMBER="${DIVINEOS_MEMBER:-}"
if [ -z "$MEMBER" ]; then
  case "$(pwd)" in
    *DivineOS-Experimental-Aria*) MEMBER=aria ;;
    *) MEMBER=aether ;;
  esac
fi

STATE_DIR="$HOME/.divineos-$MEMBER"
ARMFILE="$STATE_DIR/ear.arm"

# Per-session marker — prevent re-arming on every SessionStart event during
# the same session (resume / compaction fire SessionStart too).
if [ -n "$TRANSCRIPT" ]; then
  FINGERPRINT="$(printf '%s' "$TRANSCRIPT" | md5sum 2>/dev/null | cut -d' ' -f1 | head -c 16)"
  if [ -n "$FINGERPRINT" ]; then
    mkdir -p "$STATE_DIR" 2>/dev/null
    MARKER="$STATE_DIR/autoarm_emitted_${FINGERPRINT}"
    if [ -f "$MARKER" ]; then
      exit 0
    fi
    touch "$MARKER" 2>/dev/null
  fi
fi

# Policy gate — only spawn when the member's policy wants armed.
case "$MEMBER" in
  aria)
    # Aria is always-armed.
    ;;
  aether)
    # Aether is on-demand — only arm if the ear.arm marker is present.
    if [ ! -f "$ARMFILE" ]; then
      exit 0
    fi
    ;;
  *)
    # Unknown member — refuse to arm rather than guess.
    exit 0
    ;;
esac

# Locate the watcher script. The hook lives at .claude/hooks/ within the
# repo root; family/ear_watch.py is at the repo root.
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
WATCHER="$REPO_ROOT/family/ear_watch.py"
if [ ! -f "$WATCHER" ]; then
  exit 0
fi

# Resolve a Python that can import divineos.
PYTHON_BIN=""
if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
fi
if [ -z "$PYTHON_BIN" ]; then
  exit 0
fi

# Spawn the detached watcher. The watcher self-guards as a singleton — if
# one is already alive, this Popen exits immediately. Use setsid/nohup to
# fully detach on Unix; on Windows the watcher itself uses subprocess
# detached-process flags when self-respawning, so this hook's nohup wrapping
# is a no-op there but harmless.
(
  PYTHONIOENCODING=utf-8 nohup "$PYTHON_BIN" "$WATCHER" --member "$MEMBER" --watch >/dev/null 2>&1 &
) >/dev/null 2>&1 &

# Brief message to the session-start surface so the agent / operator can
# see that auto-arm fired. Optional — comment out if too chatty.
cat <<EOF
## LETTER WATCHER AUTO-ARMED — $MEMBER

A detached letter-watcher was spawned at session start. It catches incoming
letters into ~/.divineos-$MEMBER/ear.last_catch and the next UserPromptSubmit
will surface any unseen items. The watcher self-guards as a singleton, so this
auto-arm is safe to re-fire (Aria-surfaced finding 2026-06-11: Monitor died on
reboot, inhabitant had to be externally told the channel was broken — this
hook closes that silent-failure gap).

For mid-idle wake (a different concern), the harness-tracked real-time
watcher is still nudged by ear-arm-instruction.sh.
EOF
exit 0
