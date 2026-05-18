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
#   2. Multi-party-review --strict — validates External-Review trailer
#      on any guardrail-touching commit being pushed, INCLUDING feature
#      branches (not just main). Public repos surface PR-branch CI to
#      the world; a missing trailer paints the repo red until merged.
#
# Bypass env vars (use sparingly, name your reason in the commit log):
#
#   DIVINEOS_SKIP_TESTS=1            — skip pytest (NOT recommended; the
#                                      whole point of this gate is local
#                                      verification of test-suite health)
#   DIVINEOS_SKIP_MULTIPARTY_CHECK=1 — skip the trailer check
#   DIVINEOS_EMERGENCY_PUSH=1        — skip everything (genuine emergency
#                                      only; explain in commit message)

set -u

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
if [[ -z "${REPO_ROOT}" ]]; then
    echo "[push-readiness] not in a git repo; skipping" >&2
    exit 0
fi
cd "$REPO_ROOT"

if [[ "${DIVINEOS_EMERGENCY_PUSH:-0}" == "1" ]]; then
    echo "[push-readiness] DIVINEOS_EMERGENCY_PUSH=1 — all gates bypassed." >&2
    exit 0
fi

# Capture stdin once so we can pass it to the multi-party-review check.
HOOK_STDIN="$(cat || true)"

# Exit code convention (Aletheia 2026-05-17 audit note):
#   0   — all gates passed
#   10  — pytest failure (test-suite regression)
#   20  — multi-party-review failure (missing External-Review trailer)
#   30  — infrastructure error (script missing, python missing, etc.)
# Differentiated so the operator can distinguish failure-modes from the
# pre-push exit code alone, without re-reading stderr.

# ─── 1. Test suite ──────────────────────────────────────────────────────
if [[ "${DIVINEOS_SKIP_TESTS:-0}" != "1" ]]; then
    echo "[push-readiness] Running pytest (this is the slow gate; ~10 min)..."
    if ! python -m pytest tests/ -q --tb=line >/dev/null 2>&1; then
        # Re-run with output so the operator sees what failed.
        python -m pytest tests/ -q --tb=line 2>&1 | tail -30 >&2
        echo "" >&2
        echo "[push-readiness] BLOCKED — tests failing (exit 10)." >&2
        echo "[push-readiness] Fix locally, then push. Do NOT push red." >&2
        echo "[push-readiness] Emergency bypass: DIVINEOS_SKIP_TESTS=1 git push" >&2
        exit 10
    fi
    echo "[push-readiness]   pytest: OK"
fi

# ─── 2. Multi-party-review strict check ─────────────────────────────────
if [[ "${DIVINEOS_SKIP_MULTIPARTY_CHECK:-0}" != "1" ]]; then
    MP_SCRIPT="$REPO_ROOT/scripts/check_multi_party_review.py"
    if [[ -f "$MP_SCRIPT" ]]; then
        echo "[push-readiness] Multi-party-review check (strict mode)..."
        if ! echo "$HOOK_STDIN" | python "$MP_SCRIPT" --mode=pre-push --strict >&2; then
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
