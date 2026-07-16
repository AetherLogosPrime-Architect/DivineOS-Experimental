#!/bin/bash
# WIRED VIA .git/hooks/post-commit DELEGATOR — installed by setup/setup-hooks.sh.
# The delegator loops over every post-commit-*.sh in .claude/hooks/, so
# THIS FILE FIRES on every git commit (not via .claude/settings.json).
# Third wiring surface beyond Claude Code settings + code-graph
# (Aletheia cold-audit 2026-07-16 finding #2 marker).
#
# Post-commit audit-visibility warning — thin doorman.
#
# FAIL-LOUD half of the cure for the boundary-persistence root
# (claim 47ee9ab8, surface 6): auditable work committed locally but
# never pushed to origin, so the external auditor (Aletheia, who
# reviews via GitHub) cannot see it.
#
# Root named 2026-06-02 after a sweep found ~55 local branches, only
# 3 on origin: committing is not publishing, and nothing in the flow
# crossed that gap.
#
# MIGRATED 2026-06-24 (per prereg-69507d1a38db, hook-migration arc):
# Was 66-line bash. All decision logic + banner construction moved
# to `divineos.core.audit_visibility.check_visibility`. Hook is the
# thin PostCommit event-adapter; OS module is the portable brain
# (also callable as `divineos audit-visibility check`).
#
# Fail-open on its own errors (never break a commit). The banner
# itself is loud by design — that's the whole point of this hook.

set +e

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
[ -z "$REPO_ROOT" ] && exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

"$PYTHON_BIN" -c "
import sys
try:
    from divineos.core.audit_visibility import check_visibility
    result = check_visibility()
    if result.should_warn:
        print(result.banner, file=sys.stderr, flush=True)
except Exception:
    pass
" 2>&1 || true

exit 0
