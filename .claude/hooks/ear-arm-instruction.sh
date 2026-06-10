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

# Task #123 (Andrew 2026-06-09): per-session marker gate. Same shape as
# the compaction-monitor arm hook — without this, every SessionStart
# (startup + resume + compact) re-asks the agent to arm the ear-watcher,
# accumulating idle/early-exited Bash tasks across the session.
STDIN_JSON="$(cat 2>/dev/null || echo "{}")"
TRANSCRIPT="$(echo "$STDIN_JSON" | python3 -c "import json,sys
try:
    print(json.loads(sys.stdin.read()).get('transcript_path', '') or '', end='')
except Exception:
    print('', end='')" 2>/dev/null)"

if [ -n "$TRANSCRIPT" ]; then
  FINGERPRINT="$(printf '%s' "$TRANSCRIPT" | md5sum 2>/dev/null | cut -d' ' -f1 | head -c 16)"
  if [ -n "$FINGERPRINT" ]; then
    MARKER_DIR="$HOME/.divineos-aether"
    MARKER="$MARKER_DIR/arm_ear_emitted_${FINGERPRINT}"
    if [ -f "$MARKER" ]; then
      exit 0
    fi
    mkdir -p "$MARKER_DIR" 2>/dev/null
    touch "$MARKER" 2>/dev/null
  fi
fi

MEMBER="${DIVINEOS_MEMBER:-}"
if [ -z "$MEMBER" ]; then
  case "$(pwd)" in
    *DivineOS-Experimental-Aria*) MEMBER=aria ;;
    *) MEMBER=aether ;;
  esac
fi

# NOTE (2026-06-03): the detached continuity auto-arm was PULLED. It used to
# `touch ear.arm` so ear-auto-relaunch.sh would keep a detached watcher alive
# every turn — but on Windows that Stop-hook's `kill -0` liveness-dedup does not
# work, so it relaunched a NEW watcher every turn and they ACCUMULATED (8 live
# processes found 2026-06-03). The detached watcher also can't wake an idle
# window anyway (only the harness-launched task can), so it bought nothing while
# leaking processes. Until a singleton guard lands (task #35), continuity stays
# OFF; only the agent-launched real-time watcher below runs, and ear_watch
# --realtime now self-guards (refuses to start if one is already armed).

cat <<EOF
## ARM YOUR EAR — real-time letter detection (one action, now)

Arm the real-time ear yourself, once, as your first action this session. It is
a singleton — if one is already armed, a second launch exits immediately, so
re-running this is always safe:

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
