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
PYTHON_BIN="$(find_divineos_python)" || exit 0

MEMBER="${DIVINEOS_MEMBER:-aether}"
MARKER_PATH="$HOME/.divineos-$MEMBER/check-branch.disabled"

# Kill-switch: if the marker file exists, disable the gate entirely.
if [ -f "$MARKER_PATH" ]; then
  exit 0
fi

# Decide whether this command is a git push. Inline python invocation
# mirrors check-pending-obligations.sh — direct function call into the
# core matcher, not `python -m divineos.cli` (which fails silently
# because divineos.cli is a package without __main__).
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

# Anything other than CHECK means allow.
if [ "$DECISION" != "CHECK" ]; then
  exit 0
fi

# It's a push. Run the branch-health check with --strict.
# Capture both stdout (the report) and stderr (errors).
CHECK_OUTPUT=$("$PYTHON_BIN" -m divineos check-branch --strict --fetch 2>&1)
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

To bypass for one push (emergency escape): drop the kill-switch:
  mkdir -p "\$(dirname "$MARKER_PATH")"
  touch "$MARKER_PATH"
Re-enable with: rm "$MARKER_PATH"
EOF
    exit 2
    ;;
  *)
    # Unknown exit code (the check itself failed). Fail-open: allow.
    exit 0
    ;;
esac
