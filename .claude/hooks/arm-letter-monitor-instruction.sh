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

cat 2>/dev/null >/dev/null  # drain stdin

# 2026-06-29 second fix (Andrew "investigate it might be an easy fix"):
# the prior gate was a per-transcript marker file that fired exactly once
# per session. When the monitor died mid-session (which happened on every
# harness teardown/restore), the marker prevented the hook from re-emitting
# the arm-instruction, leaving the agent with no nudge to re-arm.
#
# New gate: check if the v2 letter monitor process is ACTUALLY alive. If
# alive, exit silent (no spam). If dead, emit the urgent re-arm instruction.
# Register this hook on BOTH SessionStart and UserPromptSubmit so it catches
# both cold-start and mid-session deaths.
#
# Fail-open: any check failure exits silent. The process-scan uses PowerShell
# on Windows (matches require-monitors-armed.sh shape).
#
# Test-only force-emit escape hatch (mirrors compaction hook): tests pinning
# the hook's emission format need it to always emit regardless of liveness.
# DIVINEOS_FORCE_ARM_EMIT=1 skips the liveness check. Production never sets it.
if [ "$DIVINEOS_FORCE_ARM_EMIT" != "1" ]; then
  LETTER_ALIVE=$(powershell.exe -NoProfile -NonInteractive -Command "
\$out = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
  Where-Object { \$_.Name -eq 'python.exe' } |
  ForEach-Object { \$_.CommandLine }
if (\$out -match 'letter_monitor_v2\.py --recipient ${MEMBER}\b') { Write-Output 'alive' } else { Write-Output 'dead' }
  " 2>/dev/null | tr -d '\r' | head -1)
  if [ "$LETTER_ALIVE" = "alive" ]; then
    exit 0
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
      timeout_ms=86400000,
      command="PYTHONIOENCODING=utf-8 python -u scripts/letter_monitor_v2.py --recipient ${MEMBER}",
  )

  # timeout_ms=86400000 = 24h. Andrew 2026-07-11 caught this at the root:
  # the prior 1h timeout meant the Monitor died silently after an hour of
  # session time, and any letter landing after that missed the auto-wake.
  # Sessions rarely last past 24h; a full-day timeout closes the gap.
  # The harness restarts Monitor processes when they crash (unexpected
  # failure), but a timeout is an intentional shutdown that doesn't
  # trigger restart. So the timeout has to be longer than the session.

Behavior:
  - Each new "to-${MEMBER}" letter in the shared dir becomes a wake-event,
    even mid-idle.
  - No separate worker; no log-file intermediary. Polling lives inside the
    Monitor command itself. If the Monitor dies, the harness notices.
  - Same 5s polling cadence as the prior worker; same recipient-filter shape;
    same [LETTER] line format on stdout.

This hook is now SessionStart-only (per Andrew 2026-07-04: reminder-noise
removed from UserPromptSubmit; only fires ONCE per session when the monitor
is verifiably dead). Skimming past it is not an option — do it now or letters
from ${SPOUSE} silently miss you for the rest of the session.
EOF
exit 0
