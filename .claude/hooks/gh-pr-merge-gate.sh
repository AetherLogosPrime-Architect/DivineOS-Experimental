#!/bin/bash
# PreToolUse hook — block `gh pr merge` on guardrail-touching PRs without
# an External-Review trailer in the merge body.
#
# Root cause (Andrew 2026-05-28): PR #50 modified moral_compass.py (a
# guardrail file) and merged without a trailer, producing a permanent
# red Integrity Audit badge on main. The pre-merge CI check fired red
# but GitHub didn't refuse the merge button.
#
# This gate moves the discipline into the OS itself so a fresh DivineOS
# install inherits guardrail protection at clone-time without any
# Andrew-side GitHub branch-protection configuration. Same shape as
# deletion-discipline.sh: thin doorman; logic in core.pr_merge_gate.
#
# Fail-open: any error exits 0 (this hook must not break workflows when
# gh is unavailable, the network is down, or the OS module is unreachable).

INPUT=$(cat)

# CHEAP RELEVANCE BAIL -- before sourcing anything, before python.
# This hook is wired to Bash but its real trigger is a COMMAND, so it
# fires on `ls` and `cat` too and pays ~664ms to find that out. The
# words below are ones the precise matcher downstream cannot fire
# without, so skipping when they are absent cannot produce a false
# negative -- it only skips work already guaranteed to be wasted.
# The bail RECORDS ITSELF; see _bail.sh for why that is not optional.
# ${0%/*} not $(dirname "$0"): dirname is a subprocess, and a subprocess
# here costs more than the whole bail saves on a hook that bails.
# shellcheck source=.claude/hooks/_bail.sh
# shellcheck disable=SC1091
source "${0%/*}/_bail.sh" 2>/dev/null || true  # fail-soft: a missing bail helper must leave this hook exactly as it was rather than break it; the guarded call below is skipped and the precise matcher still runs, so the only loss is speed
if command -v hook_bail_unless_mentions >/dev/null 2>&1; then
    hook_bail_unless_mentions "gh-pr-merge-gate.sh" "$INPUT" "gh"
fi

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
    echo "  [gh-pr-merge-gate] SKIPPED: find_divineos_python returned nothing - gate did NOT run" >&2
    exit 0
fi

echo "$INPUT" | "$PYTHON_BIN" -c "
import json, sys

try:
    data = json.loads(sys.stdin.read() or '{}')
except Exception:
    sys.exit(0)

if (data.get('tool_name') or '') != 'Bash':
    sys.exit(0)
cmd = (data.get('tool_input') or {}).get('command') or ''
if not cmd.strip():
    sys.exit(0)

try:
    from divineos.core.pr_merge_gate import block_reason
except Exception:
    sys.exit(0)  # fail-open if OS module unavailable

try:
    reason = block_reason(cmd)
except Exception:
    sys.exit(0)

if not reason:
    sys.exit(0)

print(json.dumps({
    'hookSpecificOutput': {
        'hookEventName': 'PreToolUse',
        'permissionDecision': 'deny',
        'permissionDecisionReason': reason,
    }
}))
" 2>/dev/null

exit 0
