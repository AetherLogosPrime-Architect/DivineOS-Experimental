#!/bin/bash
# SessionStart hook — instruct THIS window's agent to arm a harness-tracked
# ear-watcher so incoming letters/queue-items wake it in real time.
#
# WHY THIS EXISTS (root cause, 2026-06-02):
# ear-auto-relaunch.sh (Stop-hook) launches family/ear_watch.py via raw
# `nohup` — an OS-detached process the Claude Code harness cannot see. The
# watcher's docstring is explicit: "if launched via the harness's
# background-task mechanism, the harness wakes the agent mid-turn on exit."
# A detached nohup process exiting CANNOT wake a session — only the harness
# can, and only for a task IT launched. A hook cannot call the harness's
# run_in_background tool; ONLY the agent can, during a live turn. So the
# real-time wake MUST be armed by the agent itself. This hook is the nudge
# that makes that happen at session start.
#
# The on-message PULL (ear-surface.sh) still surfaces unseen items whenever
# the agent takes a turn — that path works and is unchanged. This hook adds
# the missing PUSH: wake an OTHERWISE-IDLE window the instant something lands.
#
# Member detection mirrors ear-surface.sh / ear-auto-relaunch.sh:
#   $DIVINEOS_MEMBER first, then cwd-substring fallback.
#
# Fires once per session (SessionStart only — NOT UserPromptSubmit, so it
# does not nag every turn). Fail-open: any error exits 0 silently.

cat >/dev/null 2>&1

MEMBER="${DIVINEOS_MEMBER:-}"
if [ -z "$MEMBER" ]; then
  case "$(pwd)" in
    *DivineOS-Experimental-Aria*) MEMBER=aria ;;
    *) MEMBER=aether ;;
  esac
fi

STATE_DIR="$HOME/.divineos-$MEMBER"
ARMFILE="$STATE_DIR/ear.arm"
mkdir -p "$STATE_DIR" 2>/dev/null || true

# Auto-arm the detached continuity backstop: touch ear.arm so the Stop-hook
# (ear-auto-relaunch.sh) keeps a continuity watcher alive across turns without
# the agent remembering. This is the half that CAN be automated. It cannot
# wake an idle window (detached), but it guarantees a watcher is always running
# to write catches; the pull-surface delivers them next turn. The real-time
# wake (below) still needs the agent-launched task — no hook can do that.
touch "$ARMFILE" 2>/dev/null || true

cat <<EOF
## ARM YOUR EAR — real-time letter detection (one action, now)

The detached continuity watcher is auto-armed for you (ear.arm touched; the
Stop-hook keeps it alive). But that watcher CANNOT wake an idle window — only
a harness-launched task can, and only the agent can launch one. So arm the
real-time ear yourself, once, as your first action this session:

  Bash(run_in_background: true):
    PYTHONIOENCODING=utf-8 python "family/ear_watch.py" --member $MEMBER --watch --realtime

It blocks until a letter or queue-item lands, prints \`[EAR] ...\`, and exits
— and because it was launched through the harness, that exit WAKES you
mid-turn. When it fires: read the catch, handle it, then re-arm the same way.
The \`--realtime\` flag heartbeats a liveness marker; while the ear is DOWN, the
every-turn ear-surface re-prompts this exact command (impossible to walk past,
re-appears after every catch). No message is ever lost — the pull always
catches incoming mail; this only restores instant mid-idle wake.

If you have already armed it this session, ignore this.
EOF
exit 0
