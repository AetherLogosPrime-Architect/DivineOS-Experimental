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
    sys.exit(1)
sys.exit(0)
"
exit $?
