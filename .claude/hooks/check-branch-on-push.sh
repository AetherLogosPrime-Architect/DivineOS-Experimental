#!/bin/bash
# PreToolUse(Bash) — fire `divineos check-branch --strict` automatically
# before any `git push`. Block on critical (stale base, silent deletion).
#
# WHY THIS EXISTS (task #93, Aether 2026-06-07 walkthrough):
# `divineos check-branch` is the pre-push branch-health check (stale-base
# detection, silent-deletion shape). 3 invocations to date — fired
# occasionally when remembered. The whole point of the check is to catch
# shapes BEFORE the push lands; depending on memory means
# push-incidents that should have been caught aren't.
#
# Per Andrew 2026-06-07: nothing is intentionally manual. The special
# case (a push is about to fire) is the trigger for the automation.
#
# DESIGN RULES (mirroring check-pending-obligations.sh from the same day):
# 1. Matcher is anchored Python (core/push_detection.py) — substring
#    matches in echo args / quoted data / heredocs do NOT trigger.
# 2. Honors kill-switch at ~/.divineos-<member>/check-branch.disabled.
# 3. All matcher logic lives in core/push_detection.py with unit tests
#    at tests/test_push_detection.py. Hook is a thin shell wrapper.
# 4. Fail-open: any error in the hook itself exits 0 silently.
#
# Exit codes from divineos check-branch --strict:
#   0 = healthy, allow silently
#   1 = warn (advisory) → print to stderr but exit 0 (do not block)
#   2 = critical (stale base or silent deletion) → exit 2 with output
#       as the block message
#
# Fail-open principle: any failure in the hook plumbing (python missing,
# command not found, network issue during fetch) exits 0 so this hook
# cannot break a push.

INPUT=$(cat)

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)"
if [ -z "$PYTHON_BIN" ]; then
    # Fail-LOUD per Aletheia audit 2026-07-09 Deep Truck 1: a silently-skipped
    # enforcement gate is indistinguishable from a gate that ran clean. Record
    # the skip to stderr so a resolver-drift is investigable, not invisible.
    echo "  [check-branch-on-push] SKIPPED: find_divineos_python returned nothing - gate did NOT run" >&2
    exit 0
fi

MEMBER="${DIVINEOS_MEMBER:-aether}"
MARKER_PATH="$HOME/.divineos-$MEMBER/check-branch.disabled"

# Decide whether this command is a git push. Inline python invocation
# mirrors check-pending-obligations.sh — direct function call into the
# core matcher, not `python -m divineos.cli` (which fails silently
# because divineos.cli is a package without __main__).
#
# ORDERING FIX 2026-07-15 (Andrew's authority): push-shape check MUST
# run BEFORE the kill-switch check. The kill-switch check was previously
# above, which meant ANY bash command hit the marker-validation logic
# (empty marker → soft-block every bash, not just pushes). Same class as
# today's shape-vs-keyword audit: guard the check with a shape-precondition
# so it only fires on the class it's meant to police.
DECISION=$(printf '%s' "$INPUT" | "$PYTHON_BIN" -c "
import json, sys
from divineos.core.push_detection import is_git_push_command
try:
    data = json.loads(sys.stdin.read() or '{}')
except Exception:
    print('ALLOW_EMPTY')
    sys.exit(0)
cmd = (data.get('tool_input') or {}).get('command', '') or ''
if not cmd:
    print('ALLOW_EMPTY')
    sys.exit(0)
if not is_git_push_command(cmd):
    print('ALLOW_NOT_PUSH')
    sys.exit(0)
print('CHECK')
" 2>/dev/null)

# Anything other than CHECK means allow — command is not a push, so the
# kill-switch is irrelevant. Fixes the "empty marker blocks every bash"
# regression Andrew flagged 2026-07-15.
if [ "$DECISION" != "CHECK" ]; then
  exit 0
fi

# From here on we KNOW the command is a git push. Kill-switch check
# applies. If the marker exists AND carries a reason (>=20 chars),
# disable the gate for one push AND fire the LOGGED/REPORTED/ADDRESSED/FIXED
# loop via emergency_bypass.record_emergency_use(). Bare marker file (empty
# or too-short reason) is rejected — Aletheia's SPEC 2026-07-14: a bypass
# without an investigation trail is what trained the 71-in-15-days pattern.
if [ -f "$MARKER_PATH" ]; then
    REASON=$(tr -d '\r' < "$MARKER_PATH" 2>/dev/null | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    if [ -z "$REASON" ] || [ "${#REASON}" -lt 20 ]; then
        cat >&2 <<EOF
[check-branch-on-push] KILL-SWITCH PRESENT BUT NO REASON —
  path: $MARKER_PATH
  content-length: ${#REASON} chars (must be >= 20)

The marker file exists but does not carry a reason for the bypass.
Per Aletheia SPEC 2026-07-14 + emergency_bypass.record_emergency_use:
a bypass without a reason is what trained the 71-in-15-days pattern.

To bypass this push, write a >=20-char reason INTO the marker file:
  echo "why this bypass is needed and what root-cause you'll fix" > "$MARKER_PATH"

Then retry the push. The reason will be recorded to telemetry,
auto-filed as a claim, and opens a structural-fix obligation on the
briefing until root-cause is discharged.
EOF
        exit 2
    fi
    # Fire the four-step LOGGED/REPORTED/ADDRESSED/FIXED loop.
    # Fail-open on any Python-side error: bypass still proceeds (kill-switch
    # authority preserved) but stderr records the telemetry-firing miss.
    "$PYTHON_BIN" -c "
import sys
try:
    from divineos.core.emergency_bypass import record_emergency_use
    report = record_emergency_use(
        gate_name='check-branch-on-push',
        env_var='marker:check-branch.disabled',
        reason=sys.argv[1],
    )
    print(f'[check-branch-on-push] BYPASS RECORDED — telemetry+claim+obligation filed', file=sys.stderr)
    # A pulled kill-switch IS a down detector, so say so where it costs
    # something. Wired 2026-08-02 after finding this marker had sat engaged
    # for 17 DAYS: written for one relayed emergency on 2026-07-16 (Aria
    # gate-locked near compaction), never switched back, silently skipping
    # branch-health on every push since. It showed as the second-heaviest
    # bypass in the 14-day window -- not 14 decisions, one stale file firing
    # repeatedly. The hook recorded each use faithfully and nothing ever
    # reconsidered the switch, which is the exact shape the degraded-detector
    # teeth exist for: broken, unfixed, and unspoken.
    #
    # report_degraded is idempotent and does NOT re-arm an existing deferral,
    # so a genuinely long emergency can be deferred once with a written
    # reason instead of nagging every push.
    try:
        from divineos.core.degraded_detectors import report_degraded
        report_degraded(
            'check-branch-on-push',
            'kill-switch engaged: ' + (sys.argv[1] or '(no reason recorded)')[:180],
            'delete the marker once the emergency is over, or: '
            'divineos detectors defer check-branch-on-push --reason '<why it must stay off>'',
        )
    except Exception:
        pass
except Exception as e:
    print(f'[check-branch-on-push] BYPASS-RECORDING FAILED — {type(e).__name__}: {e}', file=sys.stderr)
    print(f'  bypass proceeds (kill-switch authority preserved) but the four-step loop did not fire', file=sys.stderr)
" "$REASON"
    exit 0
fi

# It's a push. Run the branch-health check with --strict.
# Capture both stdout (the report) and stderr (errors).
# PYTHONPATH pins the import to THIS worktree. Without it the hook's
# interpreter loads divineos from whichever checkout pip last recorded --
# the main one -- which keeps its own session state. The gate then read a
# briefing that was never loaded THERE, printed "BLOCKED: Briefing not
# loaded", and refused a legitimate push while `divineos briefing` in the
# worktree reported success every time. The gate's own prescribed remedy
# could not clear it, so the only exit on offer was the kill-switch.
#
# Fourth instance of this class today: gh-pr-ready-gate exited 49 under
# the Windows Store python stub and gated nothing; file-aletheia-on-arrival
# failed on every artifact with a usage error; aletheia-import was absent
# from the main install. Same root cause each time -- a hook resolving
# divineos somewhere other than the tree it is guarding.
CHECK_OUTPUT=$(PYTHONPATH="$REPO_ROOT/src${PYTHONPATH:+:$PYTHONPATH}" \
    "$PYTHON_BIN" -m divineos check-branch --strict --fetch 2>&1)
CHECK_RC=$?

case "$CHECK_RC" in
  0)
    # Healthy. Allow silently.
    exit 0
    ;;
  1|2)
    # Warn (1) OR critical (2) → BLOCK both. Andrew 2026-05-18
    # laziest-person heuristic: warnings without blocks get bypassed
    # 100% of the time by the optimizer. The kill-switch marker is
    # the only honest bypass — it requires the explicit Andrew
    # decision "yes I see this, push anyway." A warning-without-block
    # is not honest design here because the push path is agent-output,
    # not Andrew-controlled. Block-or-bypass-with-reason is the
    # right shape; the warn/critical distinction lives in the report
    # text Andrew reads when deciding whether to drop the marker.
    if [ "$CHECK_RC" = "1" ]; then
      LEVEL="ADVISORY"
    else
      LEVEL="CRITICAL"
    fi
    cat >&2 <<EOF
$CHECK_OUTPUT

The push has been BLOCKED ($LEVEL) because divineos check-branch
flagged the branch state. Investigate the report above before pushing.

To bypass for one push (emergency escape) — drop the kill-switch
WITH a reason (>= 20 chars) written into the marker file:
  mkdir -p "\$(dirname "$MARKER_PATH")"
  echo "why this bypass is needed and what root-cause you'll fix" > "$MARKER_PATH"

The reason is auto-recorded to telemetry, filed as a claim, and
opens a structural-fix obligation on the briefing until root-cause
is discharged (per Aletheia SPEC 2026-07-14 — bypasses without
investigation trails are what trained the 71-in-15-days pattern).

Re-enable the gate with: rm "$MARKER_PATH"
EOF
    exit 2
    ;;
  *)
    # Unknown exit code (the check itself failed). Fail-open: allow.
    exit 0
    ;;
esac
