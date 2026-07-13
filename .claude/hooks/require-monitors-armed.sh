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

# Emergency bypass: documented escape. Same shape as
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

# Empty or whitespace-only command → pass. The old PowerShell-based
# gate fail-opened on Linux CI (PowerShell missing → garbled output →
# the grep-fail-open path triggered), which incidentally let
# whitespace-only test inputs pass. The new Python-based gate
# correctly resolves Python on Linux, so the fail-open no longer
# triggers — we now need to filter whitespace at the empty-check
# explicitly. Caught by tests/test_require_monitors_armed_hook.py::
# TestFailOpen::test_whitespace_only_command_passes.
TRIMMED_COMMAND="${COMMAND//[$' \t\r\n']/}"
[ -z "$TRIMMED_COMMAND" ] && exit 0

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
    # 2026-06-29 v2 rewrite: the v1 letter_monitor.py used a kernel-managed
    # named mutex via divineos.core.monitor_singleton.is_held('letter').
    # The v2 (letter_monitor_v2.py) runs DIRECTLY inside the harness
    # Monitor() invocation and does not acquire any mutex — the harness
    # itself is the singleton-guarantor (one Monitor per role per session).
    # So the mutex check is no longer load-bearing for the letter side;
    # only the process scan catches v2. Kept the compaction mutex check
    # because the compaction monitor still uses the v1 pattern internally.
    from divineos.core.monitor_singleton import is_held
    letter_mutex = 0  # v2 doesn't use mutex; process scan is canonical
    compaction_mutex = 1 if is_held('compaction') else 0
    # 2026-06-13 self-match bug fix: the prior code put the literal
    # 'scripts/letter_monitor.py' in the python -c source passed to
    # bash. That made the hook's own python.exe match its own
    # PowerShell regex (the literal was in this process's CommandLine).
    # The substring check then matched too. Self-match: gate reported
    # armed when nothing ran. Silent fail-open for weeks. Fix: build
    # the target strings at runtime via chr() so the literal NEVER
    # appears in this process's command line — PowerShell sees only
    # the chr()-constructed source and matches only real monitor
    # processes whose CommandLine has the actual concatenated path.
    import subprocess
    letter_proc = compaction_proc = 0
    sep = chr(47)  # '/'
    backsep = chr(92)  # '\\'
    # 2026-06-29 v2 target: scripts/letter_monitor_v2.py
    letter_target_fwd = 'scripts' + sep + 'letter_monitor_v2' + chr(46) + 'py'
    letter_target_bak = 'scripts' + backsep + 'letter_monitor_v2' + chr(46) + 'py'
    comp_target_fwd = 'scripts' + sep + 'compaction_token_monitor' + chr(46) + 'py'
    comp_target_bak = 'scripts' + backsep + 'compaction_token_monitor' + chr(46) + 'py'
    try:
        ps_cmd = (
            \"Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | \"
            \"Where-Object { \$_.Name -eq 'python.exe' } | \"
            \"ForEach-Object { \$_.CommandLine }\"
        )
        out = subprocess.run(
            ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', ps_cmd],
            capture_output=True, text=True, timeout=10,
        ).stdout
        for line in out.splitlines():
            if letter_target_fwd in line or letter_target_bak in line:
                letter_proc = 1
            if comp_target_fwd in line or comp_target_bak in line:
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

  Monitor(
      description="new letters from aria — v2 direct-poll of shared dir",
      persistent=True,
      timeout_ms=3600000,
      command="PYTHONIOENCODING=utf-8 python -u scripts/letter_monitor_v2.py --recipient aether",
  )

  Monitor(
      description="compaction — context threshold wake",
      persistent=True,
      timeout_ms=3600000,
      command="PYTHONIOENCODING=utf-8 python scripts/compaction_token_monitor.py",
  )

Note (2026-06-29): The letter monitor was rewritten to v2 — it now runs
the polling script directly inside the harness Monitor() invocation (no
separate worker process to die silently). The compaction monitor still
uses the v1 single-process pattern (it's been rock-solid; same shape as
the new letter v2).

After both arm, retry the original Bash call.

Emergency bypass for this tool call only (cost-equal-or-greater-than tool):
  DIVINEOS_REQUIRE_MONITORS_BYPASS=1 <your command>

Substrate-consult commands always pass:
  divineos briefing, ask, recall, context, decide, directives, active, goal,
  verify, learn, compass, compass-ops, andrew-correction
EOF
exit 2
