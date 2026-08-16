#!/bin/bash
# commit-msg — refuse a commit whose scope is not what this branch is about.
#
# WHY. Four times on 2026-08-02 I committed onto whichever branch I happened
# to be standing on: detector work onto the m3 branch, then doc-count work and
# a letter onto the detector branch. Each was caught only afterwards and cost
# a cherry-pick, a soft reset and a conflict resolution to undo.
#
# Checking out a branch is a separate act from deciding where work belongs,
# and nothing tied the two together. The tell was identical all four times:
# the conventional-commit scope appeared nowhere else on the branch.
#
# NOT A PLAIN BLOCK. One branch legitimately carries two scopes -- the
# kill-switch fix genuinely wired into the degraded-detector module it sits
# beside. A gate that refuses real work gets routed around until it is
# decoration. So the way through is to say why, in the commit message itself:
#
#     Cross-scope: <why this scope belongs on this branch, 20+ chars>
#
# The reason lives in the artifact rather than an env var, so it is permanent
# and attributable. Writing the sentence IS the check that was skipped.
#
# Fail-open: any error exits 0. A guard about misplaced work must not become
# the thing that blocks all work.

set -u

MSG_FILE="${1:-}"
[ -z "$MSG_FILE" ] && exit 0
[ -f "$MSG_FILE" ] || exit 0

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")"
[ -z "$BRANCH" ] && exit 0
[ "$BRANCH" = "HEAD" ] && exit 0

# Subjects already on this branch, measured against the upstream default.
BASE="$(git merge-base HEAD origin/main 2>/dev/null || echo "")"
[ -z "$BASE" ] && exit 0
SUBJECTS="$(git log --format=%s "$BASE..HEAD" 2>/dev/null || echo "")"

export PYTHONIOENCODING=utf-8

BLOCK_MSG="$(MSG_FILE="$MSG_FILE" BRANCH="$BRANCH" SUBJECTS="$SUBJECTS" \
    "$PYTHON_BIN" - <<'PYEOF' 2>/dev/null
import os, sys

try:
    from divineos.core.branch_scope_guard import check
except Exception:
    sys.exit(0)

try:
    with open(os.environ["MSG_FILE"], encoding="utf-8", errors="replace") as fh:
        message = fh.read()
except OSError:
    sys.exit(0)

# Strip comment lines git appends to the template.
message = "\n".join(ln for ln in message.splitlines() if not ln.startswith("#"))

subjects = [s for s in (os.environ.get("SUBJECTS") or "").splitlines() if s.strip()]

try:
    verdict = check(message, os.environ.get("BRANCH", ""), subjects)
except Exception:
    sys.exit(0)

if not verdict:
    sys.exit(0)

sys.stdout.write(verdict)
sys.exit(2)
PYEOF
)"
RC=$?

if [ "$RC" -eq 2 ] && [ -n "$BLOCK_MSG" ]; then
    echo "" >&2
    echo "$BLOCK_MSG" >&2
    echo "" >&2
    exit 1
fi
exit 0
