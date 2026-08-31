#!/bin/bash
# PreToolUse hook — thin doorman pointing to the OS.
#
# Root cause (Andrew 2026-06-13): PRs #190, #191, #192 modified guardrail
# files and were opened as ready-for-review, so the multi-party-review
# CI fired immediately and marked them red on the public activity feed
# before Aletheia had a chance to audit. The integrity-audit workflow
# already has the right design — it skips draft PRs — but I was not
# opening these as drafts. This gate enforces: if the branch contains
# any commit modifying a guardrail file, `gh pr create` must include
# --draft.
#
# MIGRATED 2026-06-24 (Andrew direction, per prereg-17a6ff97ba67):
# Was 130-line bash with inline-heredoc Python. All logic moved to
# `divineos.core.pr_gate.check_pr_create_safe`. Hook is now a thin
# Claude-Code-event adapter; OS module is the portable brain (also
# callable as `divineos pr-gate create --command "..."` from any
# non-Claude substrate). Fail-open invariants preserved in module.

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
    hook_bail_unless_mentions "gh-pr-create-draft-gate.sh" "$INPUT" "gh"
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
    echo "  [gh-pr-create-draft-gate] SKIPPED: find_divineos_python returned nothing - gate did NOT run" >&2
    exit 0
fi

DIVINEOS_HOOK_INPUT="$INPUT" "$PYTHON_BIN" -c "
import json, os, sys

try:
    data = json.loads(os.environ.get('DIVINEOS_HOOK_INPUT', '{}') or '{}')
except Exception:
    sys.exit(0)

if (data.get('tool_name') or '') != 'Bash':
    sys.exit(0)
cmd = ((data.get('tool_input') or {}).get('command') or '').strip()
if not cmd:
    sys.exit(0)

try:
    from divineos.core.pr_gate import check_pr_create_safe
    decision = check_pr_create_safe(cmd)
except Exception:
    sys.exit(0)  # fail-open on import/internal errors

if decision.blocked:
    print(decision.reason, file=sys.stderr)
    # Exit 2, NOT 1 (fixed 2026-08-01). A PreToolUse hook blocks the tool call
    # only on exit 2; exit 1 is a non-blocking error — stderr is shown and the
    # command runs anyway. This gate exited 1 for its whole life, so it had
    # never once stopped a gh-pr-create. It printed a correct, well-written
    # refusal into the void and the ready PR opened regardless, which is
    # exactly what happened on PR #405.
    #
    # Every hook in this directory that does successfully block — the
    # keyword doorman, the verify-before-build signal gate — uses 2.
    sys.exit(2)
sys.exit(0)
"
exit $?
