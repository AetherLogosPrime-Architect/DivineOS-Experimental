#!/bin/bash
# SessionStart resolver-health check.
#
# Aletheia audit 2026-07-09 Deep Truck 1: `find_divineos_python` is a single
# point of failure for the entire hook layer. When it fails, 10 enforcement
# gates silently no-op. This hook fires ONCE at SessionStart and surfaces
# a LOUD warning if the resolver is broken, so the whole session knows its
# gates may be compromised — rather than discovering it hook-by-hook in
# silence.
#
# Fail-open at every step: this hook cannot break session start. Its only
# job is to be LOUD if the resolver is dark.

set +e

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
[ -z "$REPO_ROOT" ] && exit 0
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
if ! source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null; then
    echo "" >&2
    echo "  [resolver-health] WARNING: could not source _lib.sh" >&2
    echo "  [resolver-health]   Gate hooks may silently no-op this session." >&2
    exit 0
fi

PYTHON_BIN="$(find_divineos_python 2>/dev/null)"
if [ -z "$PYTHON_BIN" ]; then
    echo "" >&2
    echo "  [resolver-health] !!! RESOLVER DARK: find_divineos_python returned nothing." >&2
    echo "  [resolver-health]   The following gate hooks will silently no-op this session:" >&2
    echo "  [resolver-health]     andrew-correction-attestation, check-branch-on-push," >&2
    echo "  [resolver-health]     check-pending-obligations, compass-check," >&2
    echo "  [resolver-health]     deletion-discipline, gh-pr-create-draft-gate," >&2
    echo "  [resolver-health]     gh-pr-merge-gate, no-verify-cost-escalation," >&2
    echo "  [resolver-health]     session-checkpoint, post-commit-auto-verify-findings" >&2
    echo "  [resolver-health]   INVESTIGATE resolver drift before running enforcement-sensitive" >&2
    echo "  [resolver-health]   operations (PR merge, deletion, guardrail edit)." >&2
    exit 0
fi

# Additionally verify the divineos package actually imports, catching
# venv-drift where python exists but the module tree is broken.
if ! "$PYTHON_BIN" -c "import divineos" 2>/dev/null; then
    echo "" >&2
    echo "  [resolver-health] !!! PYTHON found but 'import divineos' failed." >&2
    echo "  [resolver-health]   Resolver returned: $PYTHON_BIN" >&2
    echo "  [resolver-health]   Gates will fail-loud but their Python side won't run." >&2
    echo "  [resolver-health]   Check: $PYTHON_BIN -m pip install -e '$REPO_ROOT'" >&2
    exit 0
fi

# Healthy resolver — silent success. This hook is loud-only on failure.
exit 0
