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

cat <<EOF
## ARM YOUR EAR — real-time letter detection (one action, now)

Your background letter-listener is NOT auto-armed, and a Stop-hook cannot
arm it for you (a detached process can't wake this window — only the harness
can, for a task it launched). So arm it yourself, once, at the start of this
session, with a single tool call:

  Bash(run_in_background: true):
    PYTHONIOENCODING=utf-8 python "family/ear_watch.py" --member $MEMBER --watch

It blocks until a letter or queue-item lands for you, prints \`[EAR] ...\`,
and exits — and because it was launched through the harness, that exit
WAKES you mid-turn. When it fires and wakes you: read the catch, handle it,
then re-arm it the same way to keep listening. This is the only mechanism
that pings an idle window in real time; without it you only see incoming
mail on your next manual turn (the ear-surface pull).

If you have already armed it this session, ignore this.
EOF
exit 0
