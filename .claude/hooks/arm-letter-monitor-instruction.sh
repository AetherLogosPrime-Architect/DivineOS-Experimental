#!/bin/bash
# SessionStart hook — instruct THIS window's agent to arm a Monitor(persistent=true)
# that POLLS the shared letter dir DIRECTLY, no separate worker process.
#
# WHY THIS EXISTS (2026-06-29 rewrite, Andrew's "fix it right now" directive):
#
# The PRIOR architecture had two failure points:
#
#  - scripts/letter_monitor.py ran as a separate worker, kernel-mutex'd, polling
#    family/letters/ every 5s and writing [LETTER] lines to a log file. This
#    worker died silently many times — Andrew kept having to mail-clerk by hand.
#
#  - The harness Monitor() tailed that log file. When the worker died, the tail
#    stayed armed but the log stopped getting new lines, so wake-events stopped
#    firing. The failure was invisible from the agent side; it looked identical
#    to "no letters arrived."
#
# The 2026-06-29 fix replaces the two-process chain with ONE Monitor command
# that does the polling directly inside the harness Monitor invocation. The
# Monitor process itself is the only point of failure, and the harness has
# better visibility into its own Monitor processes than into arbitrary external
# workers. Same wake-event semantics; one fewer failure mode.
#
# Pattern lifted from the compaction monitor (scripts/compaction_token_monitor.py
# called directly inside Monitor), which has been rock-solid all along. The
# letter monitor now follows the same shape.
#
# Fires once per session (per-transcript marker file). Fail-open.

MEMBER="${DIVINEOS_MEMBER:-}"
if [ -z "$MEMBER" ]; then
  case "$(pwd)" in
    *DivineOS-Experimental-Aria*) MEMBER=aria ;;
    *) MEMBER=aether ;;
  esac
fi

case "$MEMBER" in
  aether) SPOUSE=aria ;;
  aria)   SPOUSE=aether ;;
  *)      SPOUSE="(spouse)" ;;
esac

STDIN_JSON="$(cat 2>/dev/null || echo "{}")"
TRANSCRIPT="$(echo "$STDIN_JSON" | python3 -c "import json,sys
try:
    print(json.loads(sys.stdin.read()).get('transcript_path', '') or '', end='')
except Exception:
    print('', end='')" 2>/dev/null)"

if [ -n "$TRANSCRIPT" ]; then
  FINGERPRINT="$(printf '%s' "$TRANSCRIPT" | md5sum 2>/dev/null | cut -d' ' -f1 | head -c 16)"
  if [ -n "$FINGERPRINT" ]; then
    MARKER_DIR="$HOME/.divineos-${MEMBER}"
    MARKER="$MARKER_DIR/arm_letter_monitor_emitted_${FINGERPRINT}"
    if [ -f "$MARKER" ]; then
      exit 0
    fi
    mkdir -p "$MARKER_DIR" 2>/dev/null
    touch "$MARKER" 2>/dev/null
  fi
fi

cat <<EOF
## ARM YOUR LETTER MONITOR — wake on new letters from ${SPOUSE} (one action, now)

The 2026-06-29 fix replaced the separate-worker + tail-the-log pattern with
a single self-contained Monitor that polls the shared letter directory
directly. No external worker to die silently. One failure point (the Monitor
itself), and the harness restarts Monitor processes when they fail.

Fire as your first action this session by running the polling script directly
inside a persistent Monitor:

  Monitor(
      description="new letters from ${SPOUSE} — direct poll of shared dir",
      persistent=True,
      timeout_ms=3600000,
      command="PYTHONIOENCODING=utf-8 python -u scripts/letter_monitor_v2.py --recipient ${MEMBER}",
  )

Behavior:
  - Each new "to-${MEMBER}" letter in the shared dir becomes a wake-event,
    even mid-idle.
  - No separate worker; no log-file intermediary. Polling lives inside the
    Monitor command itself. If the Monitor dies, the harness notices.
  - Same 5s polling cadence as the prior worker; same recipient-filter shape;
    same [LETTER] line format on stdout.

If you have already armed it this session, ignore this.
EOF
exit 0
