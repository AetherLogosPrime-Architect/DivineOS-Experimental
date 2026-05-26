#!/bin/bash
# Push-readiness gate — runs the things CI runs, locally, BEFORE the push
# leaves the developer's machine. Designed to prevent the failure-mode
# Andrew named 2026-05-17: iterative feature-branch pushes spamming red
# CI badges on the public activity feed. The bugs aren't the problem;
# the visibility of those bugs as red commits IS the problem.
#
# Reads pre-push stdin (forwarded by .git/hooks/pre-push) and forwards
# it to the multi-party-review strict-mode check.
#
# Gates (all run; first failure exits non-zero):
#
#   1. Full pytest suite — what CI runs. Catches environment-independent
#      failures before push. (~10 min on the full suite.)
#
#   2. Multi-party-review — validates External-Review trailer on any
#      guardrail-touching commit being pushed. Default scope: pushes to
#      `refs/heads/main` only (feature-branch pushes pass freely so the
#      external auditor can fetch and read the work without bootstrap
#      friction). Opt-in strict scope: set DIVINEOS_MULTIPARTY_STRICT=1
#      to also check feature-branch pushes — useful when iterative
#      feature-branch pushes would spam red badges on a public activity
#      feed (Andrew's 2026-05-17 concern, which the strict-mode default
#      was originally intended to address). Per Finding 78 (Aletheia
#      2026-05-18): the strict-as-default behavior created a chicken-
#      and-egg for first-audit of guardrail-touching commits — the
#      trailer requires a round, the round requires the external
#      auditor to see the work, and seeing the work requires push to
#      origin which the strict gate blocks. The fix (this file's
#      change): restore the original block-at-main scope as default;
#      strict mode becomes opt-in for operators who want the original
#      2026-05-17 protection.
#
# Bypass env vars (use sparingly, name your reason in the commit log):
#
#   DIVINEOS_SKIP_TESTS=1            — skip pytest (NOT recommended; the
#                                      whole point of this gate is local
#                                      verification of test-suite health)
#   DIVINEOS_SKIP_MULTIPARTY_CHECK=1 — skip the trailer check entirely
#   DIVINEOS_MULTIPARTY_STRICT=1     — opt INTO strict mode (also check
#                                      feature-branch pushes, not just main)
#   DIVINEOS_EMERGENCY_PUSH=1        — skip everything (genuine emergency
#                                      only; explain in commit message)

set -u

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
if [[ -z "${REPO_ROOT}" ]]; then
    echo "[push-readiness] not in a git repo; skipping" >&2
    exit 0
fi
cd "$REPO_ROOT" || exit 30

if [[ "${DIVINEOS_EMERGENCY_PUSH:-0}" == "1" ]]; then
    echo "[push-readiness] DIVINEOS_EMERGENCY_PUSH=1 — all gates bypassed." >&2
    exit 0
fi

# Capture stdin once so we can pass it to the multi-party-review check.
HOOK_STDIN="$(cat || true)"

# Deletion-only push detection. Git's pre-push protocol sends an all-zero
# local-sha for a ref being deleted; a deletion introduces no commits, so
# the test suite has nothing to verify (and the multi-party check below
# already skips deletions per-ref). If EVERY pushed ref is a deletion,
# skip the ~10-min pytest gate. Andrew 2026-05-26: tidying merged branches
# should not cost a full local test run per branch. A push that mixes a
# deletion with any real ref-update still runs the full gate.
DELETION_ONLY=1
_saw_ref=0
while read -r _lref _lsha _rref _rsha; do
    [[ -z "${_lref:-}" ]] && continue
    _saw_ref=1
    # Any non-zero char in the local-sha means this ref is a create/update,
    # not a deletion.
    if [[ "${_lsha:-}" =~ [^0] ]]; then
        DELETION_ONLY=0
    fi
done <<< "$HOOK_STDIN"
# No refs parsed (empty stdin) → not a deletion; let the normal gates run.
[[ "$_saw_ref" == "0" ]] && DELETION_ONLY=0

# Exit code convention (Aletheia 2026-05-17 audit note):
#   0   — all gates passed
#   10  — pytest failure (test-suite regression)
#   20  — multi-party-review failure (missing External-Review trailer)
#   30  — infrastructure error (script missing, python missing, etc.)
# Differentiated so the operator can distinguish failure-modes from the
# pre-push exit code alone, without re-reading stderr.

# ─── 1. Test suite ──────────────────────────────────────────────────────
if [[ "$DELETION_ONLY" == "1" ]]; then
    echo "[push-readiness] Deletion-only push — no commits to verify; skipping pytest."
elif [[ "${DIVINEOS_SKIP_TESTS:-0}" != "1" ]]; then
    echo "[push-readiness] Running pytest (this is the slow gate; ~10 min)..."
    # Run ONCE: capture combined output, then decide from the real exit code.
    # The old design ran the full suite twice (discard, then re-run on failure
    # to show output) — ~20 min on a red tree, and the two runs could diverge
    # under load (concurrent pushes contending on shared DBs), producing the
    # illegible "BLOCKED" banner sitting above a passing re-run. One run, one
    # honest signal: show the captured output only if it actually failed.
    PYTEST_LOG="$(mktemp)"
    python -m pytest tests/ -q --tb=line >"$PYTEST_LOG" 2>&1
    PYTEST_RC=$?
    if [[ $PYTEST_RC -ne 0 ]]; then
        tail -30 "$PYTEST_LOG" >&2
        rm -f "$PYTEST_LOG"
        echo "" >&2
        echo "[push-readiness] BLOCKED — tests failing (exit 10)." >&2
        echo "[push-readiness] Fix locally, then push. Do NOT push red." >&2
        echo "[push-readiness] Emergency bypass: DIVINEOS_SKIP_TESTS=1 git push" >&2
        exit 10
    fi
    rm -f "$PYTEST_LOG"
    echo "[push-readiness]   pytest: OK"
fi

# ─── 2. Multi-party-review check ────────────────────────────────────────
# Per Finding 78 (Aletheia 2026-05-18): default scope is block-at-main only
# (feature-branch pushes pass freely so external auditor can fetch the
# work). Strict scope (also check feature-branch pushes) is opt-in via
# DIVINEOS_MULTIPARTY_STRICT=1. This preserves the original 2026-05-17
# protection against red-badge spam while removing the chicken-and-egg
# for first-audit of guardrail-touching commits.
if [[ "${DIVINEOS_SKIP_MULTIPARTY_CHECK:-0}" != "1" ]]; then
    MP_SCRIPT="$REPO_ROOT/scripts/check_multi_party_review.py"
    if [[ -f "$MP_SCRIPT" ]]; then
        # Use bash array (not space-string) for argv to eliminate the
        # need for an inline lint-suppression directive, and stay defensive
        # against future modifications that might introduce spaces in argv.
        # Per Aletheia's audit-observation on Finding 78 closure.
        MP_ARGS=(--mode=pre-push)
        if [[ "${DIVINEOS_MULTIPARTY_STRICT:-0}" == "1" ]]; then
            echo "[push-readiness] Multi-party-review check (strict mode — opt-in)..."
            MP_ARGS+=(--strict)
        else
            echo "[push-readiness] Multi-party-review check (default — main only)..."
        fi
        if ! echo "$HOOK_STDIN" | python "$MP_SCRIPT" "${MP_ARGS[@]}" >&2; then
            echo "" >&2
            echo "[push-readiness] BLOCKED — multi-party-review gate failing (exit 20)." >&2
            echo "[push-readiness] File an audit round and amend commit(s)" >&2
            echo "[push-readiness] with External-Review: <round_id> trailer." >&2
            echo "[push-readiness] Emergency bypass: DIVINEOS_SKIP_MULTIPARTY_CHECK=1 git push" >&2
            exit 20
        fi
        echo "[push-readiness]   multi-party-review: OK"
    fi
fi

echo "[push-readiness] All gates passed. Pushing."
exit 0
