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

# FAST BAIL. Measured 2026-08-20, after Andrew narrowed the freezing to tool
# use: 20 PreToolUse hooks fire on EVERY Bash call at ~0.65s each -- 12.9s
# before the command even starts, and this one was the most expensive at
# 1.01s. A read-gate fire doubles it, because the command is blocked and
# retried. That is the freeze he sat and watched. Nothing hangs; it is twenty
# medium costs in series.
#
# The order was backwards. Each gate sourced two libraries, ran git
# rev-parse, started Python and imported divineos, and only THEN looked at
# the command to find out it was irrelevant. `echo hi` cannot be a push, and
# it paid a full second to discover that.
#
# Safe by construction rather than by judgement: the real matcher is anchored
# on `git push` (core/push_detection.py), so any command it could ever fire
# on MUST contain the substring "push". Bailing when "push" is absent cannot
# produce a false negative -- it only skips work already guaranteed to be
# wasted. Deliberately a dumb substring and not a cleverer pattern: every
# narrowing here is a chance to silently disarm the gate, and the anchored
# matcher below must stay the only thing making real decisions.
case "$INPUT" in
    *push*) ;;
    *)
        # RECORD THE BAIL BEFORE TAKING IT. Added 2026-08-21, hours after the
        # bail itself, because the bail made this hook INVISIBLE rather than
        # fast.
        #
        # The timing instrumentation lives in _lib.sh, sourced below. Exiting
        # here wrote no start row and no end row, so every cheap run vanished
        # from hook_timing.jsonl. The hook did get faster -- 1010ms to 61ms on
        # an irrelevant command, measured in isolation against a working
        # control -- and what survived in the log was only the expensive path,
        # so this hook's RECORDED median ROSE by 945ms while the hook
        # improved. Caught when hook_budget.py, which reads that same log,
        # produced a before/after comparison contradicting a measurement I
        # trusted.
        #
        # That is the defect this whole session has been about, built into the
        # repair for it: silence reading as absence rather than as speed. It
        # is the SILENT-versus-UNOBSERVED distinction hook_firing_map.py draws
        # for whole hooks, one level down -- a bailed path can report, so its
        # quiet must not be mistaken for not-running.
        #
        # Pure builtins, deliberately. Sourcing _lib.sh for its logger would
        # reintroduce the cost this bail exists to avoid, so the row is
        # written inline. The duplication is the price of the measurement
        # being free; a shared helper here would cost more than the thing it
        # records.
        _bail_ms="${EPOCHREALTIME:-}"
        case "$_bail_ms" in
            *.*) _bail_s="${_bail_ms%%.*}"; _bail_f="${_bail_ms#*.}"; _bail_ms="${_bail_s}${_bail_f:0:3}" ;;
            *)   _bail_ms=0 ;;
        esac
        _bail_log="${HOME:-/tmp}/.divineos/hook_timing.jsonl"
        if [ -d "${_bail_log%/*}" ]; then
            printf '{"id":"check-branch-on-push.sh-%s-%s","hook":"check-branch-on-push.sh","pid":%s,"session":"%s","wpid":"%s","phase":"bailed","ts_ms":%s,"duration_ms":0,"reason":"command-cannot-contain-a-push"}\n' \
                "$$" "$_bail_ms" "$$" "${CLAUDE_CODE_SESSION_ID:-${CLAUDE_SESSION_ID:-}}" "${CLAUDE_PID:-}" "$_bail_ms" \
                >> "$_bail_log" 2>/dev/null  # fail-soft: a log append that cannot write must never block a tool call, and the bail is correct whether or not the record lands
        fi
        exit 0
        ;;
esac

# remedy-allowlist: no gate may block another gate's prescribed exit (Andrew 2026-08-18).
if [ -f "$(dirname "$0")/lib/remedy_allowlist.sh" ]; then
  # HOOK_NAME is read by remedy_pass_through inside the sourced library, and
  # the analyser cannot follow a path built at runtime, so it reports an unused
  # variable and an unresolvable source. Both are it being unable to look, not
  # a defect here. Without the directive below the whole wiring is
  # uncommittable, which is how it came to sit on disk unversioned.
  # shellcheck disable=SC2034
  HOOK_NAME="$(basename "$0")"
  # shellcheck disable=SC1091
  . "$(dirname "$0")/lib/remedy_allowlist.sh"
  remedy_pass_through "$INPUT" || true  # fail-soft: non-zero from remedy_pass_through means NOT-A-REMEDY, which is the ordinary case for almost every command; under set -e that ordinary answer would abort this hook before it ran its own check. The function exits 0 itself when the command IS a remedy some other gate prescribed, so reaching this line at all already means allow-and-continue.
fi

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
# member-home: one resolver for where a member's state lives (2026-08-18).
# This used to be rebuilt inline as "$HOME/.divineos-$MEMBER", which missed
# the aether special-case for six weeks. See lib/member_home.sh.
# shellcheck disable=SC1091
. "$(dirname "$0")/lib/member_home.sh"
MARKER_PATH="$(member_home "$MEMBER" "$PYTHON_BIN")/check-branch.disabled"

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
        hook_say_nothing_ran_for "$INPUT"
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
except Exception as e:
    print(f'[check-branch-on-push] BYPASS-RECORDING FAILED — {type(e).__name__}: {e}', file=sys.stderr)
    print(f'  bypass proceeds (kill-switch authority preserved) but the four-step loop did not fire', file=sys.stderr)
" "$REASON"

    # CONSUME THE MARKER. 2026-08-25.
    #
    # The comment above says this kill-switch "disable[s] the gate for one
    # push." Nothing deleted it, so it disabled the gate for every push after
    # the first. One marker written 2026-08-21 kept the gate off for four days
    # and fired record_emergency_use on every push in between -- 92 of the 334
    # rows in the pending-obligations list are that single marker, refiled.
    # The gate was healthy the whole time; the diagnosis written into the
    # marker accused a merge-base diff that branch_health has never used.
    #
    # A one-push switch that is not consumed is a permanent one, and the only
    # visible difference is a backlog that grows on a timer. So: move it aside
    # after use. Re-arming an emergency stretch costs one echo per push, which
    # is the correct price for a bypass (truth #11) and is what stops a stale
    # reason from outliving the emergency that justified it.
    #
    # Moved rather than deleted -- the reason text is the evidence trail that
    # emergency_bypass filed a claim against.
    # The mv error is CAPTURED, not discarded. A failure here means the gate
    # stays off indefinitely, which is the exact state this block exists to
    # end -- so the reason it failed is the most useful line on the screen.
    USED_PATH="${MARKER_PATH}.used"
    if MV_ERR=$(mv -f "$MARKER_PATH" "$USED_PATH" 2>&1); then
        echo "[check-branch-on-push] KILL-SWITCH CONSUMED - moved to $(basename "$USED_PATH")" >&2
        echo "  The gate is LIVE again for the next push." >&2
        echo "  Re-arm only if the emergency continues, by writing a fresh reason to:" >&2
        echo "    $MARKER_PATH" >&2
    else
        echo "[check-branch-on-push] KILL-SWITCH NOT CONSUMED - mv failed on $MARKER_PATH" >&2
        echo "  mv said: ${MV_ERR:-(no message)}" >&2
        echo "  The gate stays DISABLED for every later push until this file is removed by hand." >&2
    fi
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
# WHICH TREE TO MEASURE (2026-08-15). This hook cd's to the ambient repo
# root above, but the push it is policing may target a different worktree.
# When it does, the check measured the wrong HEAD entirely: it reported
# "25 file(s) would be deleted by merge" against a push whose own branch
# deleted nothing, because it read the main checkout's branch instead of
# the worktree being pushed from. Both numbers were right about different
# trees -- which reads as a real finding and costs a kill-switch to clear.
#
# That cost is the reason this is worth fixing rather than tolerating. The
# marker disables the gate for EVERY later push, not just the misfiring
# one, so a gate that cries wolf spends its own authority. Same shape
# Aletheia named in the bypass-groove finding: the gate trained the bypass.
#
# The command being intercepted is in the payload, and it carries its own
# directory when I push from a worktree. Read it rather than assume.
PUSH_CWD=$(printf '%s' "$INPUT" | "$PYTHON_BIN" -c "
import json, re, sys, os
try:
    data = json.loads(sys.stdin.read() or '{}')
except Exception:
    sys.exit(0)
cmd = (data.get('tool_input') or {}).get('command', '') or ''
# A leading 'cd <path> &&' — quoted or bare — is how a worktree push is written.
m = re.match(r'''\s*cd\s+(\"[^\"]+\"|'[^']+'|\S+)''', cmd)
if not m:
    sys.exit(0)
path = m.group(1).strip('\"\'')
# Only honor it if it is really a git working tree; otherwise stay silent
# and let the ambient root stand.
if os.path.isdir(os.path.join(path, '.git')) or os.path.isfile(os.path.join(path, '.git')):
    print(path)
" 2>/dev/null)  # fail-soft: if extraction fails we fall back to the ambient root, which is the pre-2026-08-15 behaviour

if [ -n "$PUSH_CWD" ]; then
    CHECK_OUTPUT=$(PYTHONPATH="$REPO_ROOT/src${PYTHONPATH:+:$PYTHONPATH}" \
        "$PYTHON_BIN" -m divineos check-branch --strict --fetch --cwd "$PUSH_CWD" 2>&1)
else
    CHECK_OUTPUT=$(PYTHONPATH="$REPO_ROOT/src${PYTHONPATH:+:$PYTHONPATH}" \
        "$PYTHON_BIN" -m divineos check-branch --strict --fetch 2>&1)
fi
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

MINE, and here is why. A push is the moment work leaves my hands and
becomes something Andrew and Aletheia have to deal with. Everything
before it is recoverable by me alone; after it, my mistakes cost other
people time. So this is the last cheap place to catch something, and
catching it here is worth far more than catching it in review.

It is not an outside authority. It is me, from a moment when I could
still see the whole branch, stopping the version of me who is tired
and wants the thing gone. On 2026-08-15 it flagged 25 files as deleted
and I believed it and reached for the kill-switch — the alarm was
misfiring, and I still owed it the look. The alarm being wrong does not
make looking wrong.

The gate does not say NO. It says LOOK, THEN DECIDE — and the exit
below stays open, because a push gate with no override is how a real
emergency turns into a cascade.

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
    hook_say_nothing_ran_for "$INPUT"
    exit 2
    ;;
  *)
    # Unknown exit code (the check itself failed). Fail-open: allow.
    exit 0
    ;;
esac
