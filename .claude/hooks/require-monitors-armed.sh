#!/bin/bash
# PreToolUse(Bash) — require Monitor primitives to be alive before allowing
# Bash tool calls.
#
# WHY THIS EXISTS (Andrew 2026-06-09 budget-investigation + Monitor-failure):
# The harness Monitor(persistent=true) primitive is documented as "runs until
# TaskStop or session end" but empirically dies more often than that:
# - Doesn't survive SessionStart:resume (task #108 original finding)
# - Can die mid-turn even within the SAME generation (today's failure: armed at
#   start-of-turn, dead by mid-turn)
#
# Without an alive Monitor, the wake-from-idle mechanism for new letters from
# Aria and context-threshold-crossing notifications doesn't fire. The
# arm-monitor-instruction.sh hooks NUDGE me to arm at SessionStart, but
# nudges don't survive compaction (my intention to comply is in the context
# window; once compacted it's gone). Per Andrew 2026-05-27: "if I want
# something to persist across the reset, it cannot stay a want or a promise;
# it must be built into the OS as structure."
#
# This hook converts the nudge into a structural gate: every Bash tool call
# verifies the Monitor processes are alive. If either is missing, Bash is
# blocked with instructions to re-arm via the Monitor() tool (which is NOT
# a Bash call and is therefore never blocked by this gate — no chicken-and-
# egg).
#
# Same shape as the deprecated require-ear-armed.sh, but for the Monitor
# primitive instead of the old ear-watch architecture.
#
# Fail-open: any error exits 0 silently. This hook cannot break a turn.

INPUT=$(cat)

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"

# Resolve the divineos-aware Python via the shared helper. Required by
# tests/test_hook_python_lookup.py — hooks importing divineos must NOT
# call bare `python` (which can resolve to a different interpreter than
# the one with divineos installed). Fail-open if helper missing.
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

# Bypass list — gate-recovery commands must always pass through. These are
# the divineos substrate-consult commands the gate-system itself prescribes
# as the named escape from any gate's block. Matches the canonical list in
# scripts/hook_bypass_commands.txt (PR #112 lands the shared list; until
# then keep a minimal local copy here).
BYPASS_PREFIXES=(
  "divineos briefing"
  "divineos ask"
  "divineos recall"
  "divineos context"
  "divineos decide"
  "divineos directives"
  "divineos active"
  "divineos goal"
  "divineos verify"
  "divineos learn"
  "divineos compass"
  "divineos compass-ops"
  "divineos andrew-correction"
)

# Emergency bypass: documented operator escape. Same shape as
# DIVINEOS_EAR_ALLOW_UNARMED — costs more than tool use (must be set on the
# specific invocation, not exported globally) to honor Andrew 2026-05-31
# design-constraint #3 (bypass must cost more than tool use).
if [ "$DIVINEOS_REQUIRE_MONITORS_BYPASS" = "1" ]; then
  exit 0
fi

# Extract the bash command from the tool input.
COMMAND=$(printf '%s' "$INPUT" | "$PYTHON_BIN" -c "
import json, sys
try:
    data = json.loads(sys.stdin.read() or '{}')
    print((data.get('tool_input') or {}).get('command', ''))
except Exception:
    pass
" 2>/dev/null)

# Empty command → pass.
[ -z "$COMMAND" ] && exit 0

# Bypass check — split on shell separators, trim, match against prefixes.
# Pattern lifted from scripts/hook_bypass_commands.txt (PR #112).
IFS_BACKUP="$IFS"
IFS=$'\n'
for segment in $(printf '%s' "$COMMAND" | tr '&|;' '\n'); do
  segment="${segment#"${segment%%[![:space:]]*}"}"  # ltrim
  segment="${segment%"${segment##*[![:space:]]}"}"  # rtrim
  [ -z "$segment" ] && continue
  case "$segment" in '#'*) continue ;; esac
  for prefix in "${BYPASS_PREFIXES[@]}"; do
    [ -z "$prefix" ] && continue
    case "$segment" in
      "$prefix"|"$prefix "*)
        IFS="$IFS_BACKUP"
        exit 0
        ;;
    esac
  done
done
IFS="$IFS_BACKUP"

# Check for alive Monitors. Primary: kernel-managed named mutex via
# divineos.core.monitor_singleton.is_held (the new singleton-guard
# primitive). Fallback: process scan for matching script names — used
# only when is_held reports "not held" but the scripts ARE running.
# This belt-and-suspenders shape covers an empirically-observed case
# where cross-process mutex visibility from the gate's spawned Python
# differs from the live letter_monitor.py's view (likely PYTHONPATH /
# pywin32 install differences). The mutex is canonical; the process
# scan is the safety net.
#
# Fail-open: if Python or the module is unavailable, treat as armed.
# This gate cannot break a turn (Andrew 2026-06-09 design constraint).
MONITORS_STATUS=$("$PYTHON_BIN" -c "
import sys
try:
    from divineos.core.monitor_singleton import is_held
    letter_mutex = 1 if is_held('letter') else 0
    compaction_mutex = 1 if is_held('compaction') else 0
    # Process-scan fallback (subprocess to powershell — only used as
    # confirmation, never as primary). Script-name match is unambiguous
    # because the scripts are uniquely-named, unlike the prior regex
    # which matched arbitrary command-line tokens.
    import subprocess
    letter_proc = compaction_proc = 0
    try:
        ps_cmd = (
            \"Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | \"
            \"Where-Object { (\$_.CommandLine -match 'letter_monitor\.py' \"
            \"-or \$_.CommandLine -match 'compaction_token_monitor\.py') \"
            \"-and \$_.Name -eq 'python.exe' } | \"
            \"ForEach-Object { \$_.CommandLine }\"
        )
        out = subprocess.run(
            ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', ps_cmd],
            capture_output=True, text=True, timeout=10,
        ).stdout
        for line in out.splitlines():
            if 'letter_monitor.py' in line:
                letter_proc = 1
            if 'compaction_token_monitor.py' in line:
                compaction_proc = 1
    except Exception:
        pass
    letter = letter_mutex or letter_proc
    compaction = compaction_mutex or compaction_proc
    print(f'{letter},{compaction}')
except Exception:
    sys.exit(0)
" 2>/dev/null)

# Fail-open on missing output (Python broken, module missing, etc).
if ! echo "$MONITORS_STATUS" | grep -qE '^[0-9]+,[0-9]+$'; then
  exit 0
fi

LETTER_COUNT="${MONITORS_STATUS%,*}"
COMPACTION_COUNT="${MONITORS_STATUS#*,}"

# Conditional-requirement discipline: only require the compaction Monitor
# if its underlying script exists in the working tree.
COMPACTION_REQUIRED=1
if [ ! -f "$REPO_ROOT/scripts/compaction_token_monitor.py" ]; then
  COMPACTION_REQUIRED=0
fi

LETTER_OK=0
COMPACTION_OK=0
if [ "$LETTER_COUNT" -gt 0 ]; then
  LETTER_OK=1
fi
if [ "$COMPACTION_REQUIRED" -eq 0 ] || [ "$COMPACTION_COUNT" -gt 0 ]; then
  COMPACTION_OK=1
fi

if [ "$LETTER_OK" -eq 1 ] && [ "$COMPACTION_OK" -eq 1 ]; then
  exit 0
fi

# Build the missing-list message.
MISSING=""
if [ "$LETTER_COUNT" -eq 0 ]; then
  MISSING="${MISSING}  - Letter Monitor (watching family/letters/ for new aria-to-aether-*.md)
"
fi
if [ "$COMPACTION_REQUIRED" -eq 1 ] && [ "$COMPACTION_COUNT" -eq 0 ]; then
  MISSING="${MISSING}  - Compaction Monitor (watching context-token threshold)
"
fi

cat >&2 <<EOF
BLOCKED: required Monitor(s) not alive.

Missing:
$MISSING
Without these armed, mid-idle wake from new letters and context-threshold
crossings does not fire. The arm-instruction.sh SessionStart hooks are NUDGES,
not constraints — they don't survive compaction or my own attention drift.
This gate enforces the discipline structurally (Andrew 2026-06-09).

Re-arm via Monitor() — NOT a Bash call, so this gate does not block it.
Each script acquires a kernel-managed named mutex at startup; if a
sibling Monitor for that role is already alive, the script exits
cleanly with a [MONITOR-SINGLETON-DEDUP role=...] line. The kernel
releases the mutex on process death (including crash), so no stale
state can accumulate.

  Monitor(
      description="new letters from aria — wakes from idle",
      persistent=True,
      timeout_ms=3600000,
      command="PYTHONIOENCODING=utf-8 python scripts/letter_monitor.py",
  )

  Monitor(
      description="compaction — context threshold wake",
      persistent=True,
      timeout_ms=3600000,
      command="PYTHONIOENCODING=utf-8 python scripts/compaction_token_monitor.py",
  )

After both arm, retry the original Bash call.

Emergency bypass for this tool call only (cost-equal-or-greater-than tool):
  DIVINEOS_REQUIRE_MONITORS_BYPASS=1 <your command>

Substrate-consult commands always pass:
  divineos briefing, ask, recall, context, decide, directives, active, goal,
  verify, learn, compass, compass-ops, andrew-correction
EOF
exit 2
