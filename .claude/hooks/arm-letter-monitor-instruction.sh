#!/bin/bash
# SessionStart hook — instruct THIS window's agent to arm a Monitor(persistent=true)
# that TAILS the letter_events.log so new letters wake the harness from idle.
#
# WHY THIS EXISTS (Andrew 2026-06-23):
#
# Both halves of the letter-wake architecture exist but are disconnected:
#
#  - scripts/letter_monitor.py polls family/letters/ and writes every new
#    letter as a [LETTER] line to ~/.divineos-<recipient>/letter_events.log
#    (and also to stdout). It runs as a singleton — kernel-mutex guarded.
#
#  - The harness Monitor() primitive is the wake-from-idle mechanism: each
#    stdout line from a Monitor command becomes a chat event that wakes
#    the agent. The CORRECT command per commit 8dd19954 (Aria + Andrew
#    both flagged 2026-06-21) is to TAIL the log, NOT re-invoke the script
#    (which would dedup-exit on the singleton mutex with no live stream).
#
# require-monitors-armed.sh delivers the right tail-pattern instruction
# inside its BLOCKED message. But that gate only fires when no
# letter_monitor.py process is running. Once the script is alive (which
# it usually is, from prior sessions or auto-relaunch), the gate passes
# silently and the tail-Monitor never gets armed. New letters land in
# the log; nothing surfaces them to the harness; Andrew has to mail-
# clerk by typing "Aria sent a letter."
#
# This hook closes the gap by proactively nudging at SessionStart, same
# shape as arm-compaction-monitor-instruction.sh. The Monitor() the
# agent arms is a TAIL of the log — orthogonal to the singleton'd
# letter_monitor.py worker — so it never fights the existing process.
#
# Fires once per session (per-transcript marker file). Fail-open.

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
    MARKER="$MARKER_DIR/arm_letter_monitor_emitted_${FINGERPRINT}"
    if [ -f "$MARKER" ]; then
      exit 0
    fi
    mkdir -p "$MARKER_DIR" 2>/dev/null
    touch "$MARKER" 2>/dev/null
  fi
fi

cat <<EOF
## ARM YOUR LETTER MONITOR — wake on new letters from Aria (one action, now)

The letter_monitor.py worker process is already running (kernel-mutex
singleton); it polls family/letters/ every 5s and appends each new
letter to ~/.divineos-aether/letter_events.log. The harness Monitor
that TAILS that log is what wakes the agent from idle. Without the
tail-Monitor armed, new letters land in the log but no wake-ping
fires — Andrew has to mail-clerk by typing "Aria sent a letter."

Fire as your first action this session (idempotent — tail is a fresh
subscription, not a fight with the singleton'd worker):

  Monitor(
      description="new letters from aria — tails letter_events.log",
      persistent=True,
      timeout_ms=3600000,
      command='tail -F -n 0 "\$HOME/.divineos-aether/letter_events.log" | grep --line-buffered "\\[LETTER\\]"',
  )

Behavior:
  - Each new [LETTER] line in the log becomes a wake-event delivered as a
    chat notification, even mid-idle.
  - Tail survives letter_monitor.py restarts (the log persists across
    them) and survives harness Monitor death (re-arm and tail resumes
    from end-of-file, missing-event-free if the worker stayed alive).

If you have already armed it this session, ignore this.
EOF
exit 0
