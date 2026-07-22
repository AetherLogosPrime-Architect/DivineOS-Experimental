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

# Resolve the repo-root-anchored absolute path for the monitor script.
# The prior version emitted a RELATIVE path (scripts/letter_monitor_v2.py)
# which dies with exit-127 whenever the harness spawns the Monitor from a
# shell whose cwd is not the repo root. Absolute path matches the shape
# the compaction-monitor arm-instruction has used all along (rock-solid).
# Fix (Aria + Andrew 2026-07-20): make letter-monitor arm match the
# compaction-monitor arm so both survive shell-cwd drift on session resume.
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
SCRIPT_PATH="$REPO_ROOT/scripts/letter_monitor_v2.py"

# 2026-06-29 second fix (Andrew "investigate it might be an easy fix"):
# the prior gate was a per-transcript marker file that fired exactly once
# per session. When the monitor died mid-session (which happened on every
# harness teardown/restore), the marker prevented the hook from re-emitting
# the arm-instruction, leaving the agent with no nudge to re-arm.
#
# New gate: check if the v2 letter monitor process is ACTUALLY alive. If
# alive, exit silent (no spam). If dead, emit the urgent re-arm instruction.
#
# 2026-07-21 redesign (Andrew, council-2f7d3772aea7 yudkowsky+wayne+popper+
# feynman): the "register on BOTH SessionStart and UserPromptSubmit" pattern
# was force-emitting the arm-instruction every prompt AND running a
# PowerShell process-scan-and-kill every prompt -- classic wallpaper +
# real per-prompt overhead. Removed from UserPromptSubmit array; the hook
# is now SessionStart-only in truth (not just in stale comment).
#
# Mid-session monitor death is compensated by the ear-surface hook, which
# fires every UserPromptSubmit and surfaces unseen letter counts even if
# the monitor is dead. That's a delay-cost (I see the letter on the next
# prompt after arrival, not as an immediate wake) but not a loss.
#
# If mid-interval monitor death proves recurring in practice (Yudkowsky
# Goodhart concern: my write-letter cadence may not match Aria's write-
# to-me cadence closely enough), a PostToolUse-on-letter-write natural-
# event rearm trigger is the queued follow-on. Not built yet -- adding
# it now would be scope-creep dressed as thoroughness (Feynman walk).
#
# Fail-open: any check failure exits silent. The process-scan uses PowerShell
# on Windows (matches require-monitors-armed.sh shape).
#
# Fix pair (Aria + Andrew 2026-07-18):
#
# Root cause diagnosed tonight: the OS-level letter_monitor_v2.py process
# can outlive its session-scoped Monitor() binding. When Claude Code
# archives and restores a session, the harness kills the in-session
# Monitor tool but the OS-level python process it spawned keeps running.
# Next session: process still alive, hook's liveness check reports
# "alive", hook exits silently — but the CURRENT session has NO Monitor
# tool wired to it, so new letters never wake the agent mid-session.
#
# Belt-and-suspenders fix:
#
# 1. Kill any leftover letter_monitor_v2.py processes for this recipient
#    at SessionStart, so the liveness check is honest ("no process" =
#    "not armed in this session").
# 2. Force-emit the arm instruction anyway at SessionStart regardless of
#    the check outcome. Double-arming is harmless overhead; a missed arm
#    is silent letter loss until Andrew intervenes.
#
# Priority: (1) then (2). Sequential. Both must complete for the fix to
# hold under adversarial timing (leftover process spawned mid-init).

# Fix 1: kill leftover letter_monitor_v2.py processes for THIS recipient.
# Fail-open on all errors — a failed kill leaves us with the old state,
# which fix 2 (force-emit) still catches.
if [ "$DIVINEOS_SKIP_LEFTOVER_KILL" != "1" ]; then
  powershell.exe -NoProfile -NonInteractive -Command "
Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
  Where-Object { \$_.Name -eq 'python.exe' -and \$_.CommandLine -match 'letter_monitor_v2\.py --recipient ${MEMBER}\b' } |
  ForEach-Object { Stop-Process -Id \$_.ProcessId -Force -ErrorAction SilentlyContinue }
  " 2>/dev/null >/dev/null || true
fi

# Fix 2: force-emit the arm instruction. Prior gate (skip if process
# alive) was fooled by leftover OS processes and gave false quiet.
# Test-only escape hatch DIVINEOS_SKIP_ARM_EMIT preserved for any test
# that needs to assert the hook can stay silent.
if [ "$DIVINEOS_SKIP_ARM_EMIT" = "1" ]; then
  exit 0
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
      command="PYTHONIOENCODING=utf-8 python -u \"${SCRIPT_PATH}\" --recipient ${MEMBER}",
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
