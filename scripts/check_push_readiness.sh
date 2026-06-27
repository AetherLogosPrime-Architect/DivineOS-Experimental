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
#
# Path-scoped fast path (Andrew 2026-06-10 PR-throughput ordeal): the
# full pytest suite takes ~10 min and is the dominant cost of every
# push. For pushes that only touch low-impact paths (tests/, docs/,
# family/, exploration/, root markdown/text), the full suite gives
# almost no protection that CI doesn't also catch — CI runs the full
# matrix anyway on the PR. Skipping the local full-suite in those
# cases keeps the safety net (CI) intact while removing the bottleneck
# from the iteration loop. Code-touching pushes still run the full
# suite locally; CI is the second pass.
#
# Three states:
#   - No commits / deletion-only          → skip
#   - All changed paths low-impact        → skip (state in log; CI catches)
#   - Anything else                       → full suite as before
#
# Emergency bypass (DIVINEOS_SKIP_TESTS=1) still applies.

# Collect the union of changed files across every ref being pushed.
# Pre-push stdin gives `<local-ref> <local-sha> <remote-ref> <remote-sha>`
# per ref; for each, `git diff --name-only <remote-sha>..<local-sha>`
# lists the files touched by commits being pushed. New branches (all-zero
# remote-sha) fall back to diff against the default base (origin/main).
_collect_changed_files() {
    local lref lsha rref rsha base
    while read -r lref lsha rref rsha; do
        [[ -z "${lref:-}" ]] && continue
        # Deletion: no files to scan.
        [[ "${lsha:-}" =~ ^0+$ ]] && continue
        if [[ "${rsha:-}" =~ ^0+$ || -z "${rsha:-}" ]]; then
            # New branch; diff against main as the conservative base.
            base="$(git merge-base "$lsha" origin/main 2>/dev/null || echo "")"
        else
            base="$rsha"
        fi
        if [[ -n "$base" ]]; then
            git diff --name-only "$base..$lsha" 2>/dev/null
        else
            # Couldn't resolve a base; emit "" so caller falls back to full.
            echo ""
        fi
    done <<< "$HOOK_STDIN" | sort -u
}

# Returns 0 (true) if every changed file is in a low-impact path.
# Empty file list → false (conservative: can't prove low-impact, run full).
_all_changed_low_impact() {
    local file
    local saw_any=0
    while IFS= read -r file; do
        [[ -z "$file" ]] && continue
        saw_any=1
        case "$file" in
            tests/*) ;;
            docs/*) ;;
            family/*) ;;
            exploration/*) ;;
            *.md) ;;
            *.txt) ;;
            *)
                return 1
                ;;
        esac
    done <<< "$1"
    [[ "$saw_any" == "1" ]]
}

# Empty-branch detection (Andrew 2026-06-12): catch the failure mode hit
# twice during the 2026-06-11 PR-batch — after rebasing a stacked branch
# onto a main that absorbed the stack's commits, the branch can end up
# with ZERO commits ahead of main while still being force-pushed. The
# force-push "succeeds" (the ref moves) but the resulting PR is empty,
# wasting ~10min of pre-push pytest + a CI run + cycles spent figuring
# out why the merge button is greyed.
#
# Signal: for any push to a non-main feature branch where main exists
# locally, `git log origin/main..<local-sha>` returns no commits → the
# branch has nothing to add. Tell the operator to close the PR (or
# rebase to recover dropped work) instead of pushing.
#
# Bypass: DIVINEOS_ALLOW_EMPTY_PUSH=1 (e.g. when intentionally pushing
# a tag-only or note-only commit that the parser missed).
_check_empty_branch() {
    local lref lsha rref rsha
    local has_main
    has_main="$(git rev-parse --verify --quiet origin/main 2>/dev/null || echo "")"
    [[ -z "$has_main" ]] && return 0  # No origin/main; can't measure.
    while read -r lref lsha rref rsha; do
        [[ -z "${lref:-}" ]] && continue
        [[ "${lsha:-}" =~ ^0+$ ]] && continue  # deletion
        # Skip the main branch itself — by definition main is "ahead of main".
        if [[ "${rref:-}" =~ /main$ ]]; then
            continue
        fi
        # Count commits the local sha has that origin/main doesn't.
        local n
        n="$(git rev-list --count "origin/main..$lsha" 2>/dev/null || echo "?")"
        if [[ "$n" == "0" ]]; then
            echo "[push-readiness] EMPTY-BRANCH detected: $lref has 0 commits ahead of origin/main."
            echo "[push-readiness] Pushing this would produce an empty PR (nothing to merge)."
            echo "[push-readiness] Likely cause: rebase absorbed the commits because main already has them."
            echo "[push-readiness] Recommended: close the PR (gh pr close <n> --comment '...') or rebase to recover."
            echo "[push-readiness] Bypass if intentional: DIVINEOS_ALLOW_EMPTY_PUSH=1 git push"
            return 21
        fi
    done <<< "$HOOK_STDIN"
    return 0
}

if [[ "${DIVINEOS_ALLOW_EMPTY_PUSH:-0}" != "1" ]]; then
    if ! _check_empty_branch; then
        # _check_empty_branch returns 21 when it detected an empty push and
        # printed the diagnostic. Propagate that exit code so the operator
        # can distinguish empty-branch from other failure modes.
        exit 21
    fi
fi

if [[ "$DELETION_ONLY" == "1" ]]; then
    echo "[push-readiness] Deletion-only push — no commits to verify; skipping pytest."
elif [[ "${DIVINEOS_SKIP_TESTS:-0}" == "1" ]]; then
    echo "[push-readiness] DIVINEOS_SKIP_TESTS=1 — skipping pytest." >&2
else
    CHANGED_FILES="$(_collect_changed_files)"
    if _all_changed_low_impact "$CHANGED_FILES"; then
        echo "[push-readiness] Fast path: all changed files are in low-impact paths"
        echo "[push-readiness] (tests/, docs/, family/, exploration/, *.md, *.txt) —"
        echo "[push-readiness] skipping local pytest. CI on the PR runs the full matrix."
        # Skip pytest; fall through to multi-party-review.
        : "${PYTEST_RC:=0}"
    else
        echo "[push-readiness] Running pytest (this is the slow gate; ~10 min)..."
        # Run ONCE: capture combined output, then decide from the real exit code.
        # The old design ran the full suite twice (discard, then re-run on failure
        # to show output) — ~20 min on a red tree, and the two runs could diverge
        # under load (concurrent pushes contending on shared DBs), producing the
        # illegible "BLOCKED" banner sitting above a passing re-run. One run, one
        # honest signal: show the captured output only if it actually failed.
        #
        # CONCURRENCY ISOLATION (claim f111801a, 2026-06-15): when multiple
        # branches push simultaneously, each fires its own pre-push hook that
        # runs `python -m pytest tests/` against the SHARED working tree.
        # `git checkout` operations during one push corrupt the file-set
        # another push's pytest is reading, producing spurious 60+ failures
        # that pass cleanly when run serially. The fix is per-push isolation
        # via a temp worktree at the specific commit being pushed: pytest
        # runs against an immutable snapshot of THAT branch, immune to what
        # the developer's main checkout is doing. Worktree setup is
        # ~200-500ms — negligible against ~10min pytest.
        #
        # The first non-deletion local SHA from HOOK_STDIN is the commit being
        # pushed. Multi-ref pushes use the first ref's SHA — same tree as
        # the working dir was at when the operator ran `git push`, which is
        # the right snapshot for a "is this commit ready" gate.
        PYTEST_SHA=""
        while read -r _lref _lsha _rref _rsha; do
            if [[ -n "$_lsha" && "$_lsha" != "0000000000000000000000000000000000000000" ]]; then
                PYTEST_SHA="$_lsha"
                break
            fi
        done <<< "$HOOK_STDIN"

        PYTEST_LOG="$(mktemp)"
        if [[ -n "$PYTEST_SHA" ]] && command -v git >/dev/null && [[ "${DIVINEOS_PUSH_GATE_NO_WORKTREE:-0}" != "1" ]]; then
            # Isolated path: temp worktree at the pushed commit. Survives
            # concurrent pushes because each gets its own checkout.
            PYTEST_WORKTREE="$(mktemp -d -t divineos-push-gate-XXXXXX)"
            if git worktree add --detach "$PYTEST_WORKTREE" "$PYTEST_SHA" >/dev/null 2>&1; then
                # Interrupt-safe cleanup (Aletheia audit catch, 2026-06-15):
                # if pytest crashes the runner OR the hook receives SIGINT/
                # SIGTERM during the ~10-min pytest, the post-pytest
                # `git worktree remove` line never executes and we leak a
                # registered worktree (the tempdir AND a .git/worktrees/
                # entry). Not a safety hole — leaked worktrees do not corrupt
                # anything and `git worktree prune` cleans them — but they
                # accumulate under interrupted pushes. Trap closes the
                # interrupt path.
                trap '
                    git worktree remove --force "$PYTEST_WORKTREE" >/dev/null 2>&1 || true
                    rm -rf "$PYTEST_WORKTREE" 2>/dev/null || true
                ' EXIT INT TERM HUP
                # Aether 2026-06-27 fix (per Aria's train-tracks-research): bare
                # `python -m pytest` resolves `import divineos` through the
                # system-wide editable install (which points at WHICHEVER worktree
                # last ran `pip install -e .`). That means a push from worktree B
                # gets its tests run against worktree A's installed code. The temp
                # worktree's source must win — prepend it to PYTHONPATH the same
                # way `.claude/hooks/_lib.sh::find_divineos_python` does for Claude
                # hooks. Same fix-shape, applied to the pre-push gate's pytest call.
                (cd "$PYTEST_WORKTREE" && PYTHONPATH="$PYTEST_WORKTREE/src${PYTHONPATH:+:$PYTHONPATH}" python -m pytest tests/ -q --tb=line) >"$PYTEST_LOG" 2>&1
                PYTEST_RC=$?
                # Normal-path cleanup — runs after pytest exits cleanly. The
                # trap above covers the interrupt path; this call covers the
                # happy path so the worktree is gone before the rest of the
                # gate runs (the trap only fires when the script ends).
                # `--force` because pytest may leave temp DBs / cache files
                # behind in the worktree.
                git worktree remove --force "$PYTEST_WORKTREE" >/dev/null 2>&1 || true
                # Disarm the trap now that the normal path cleaned up — the
                # tempdir is already gone, no need to fire again at EXIT.
                trap - EXIT INT TERM HUP
            else
                # Worktree creation failed (rare: disk full, permissions,
                # bare-repo edge case). Fall back to non-isolated run rather
                # than blocking the push outright — preserves the gate's
                # safety-net role even when isolation is unavailable.
                echo "[push-readiness] worktree isolation unavailable, running pytest in main worktree (concurrency-fragile)" >&2
                python -m pytest tests/ -q --tb=line >"$PYTEST_LOG" 2>&1
                PYTEST_RC=$?
            fi
        else
            # No SHA available, or operator opted out of worktree isolation
            # via DIVINEOS_PUSH_GATE_NO_WORKTREE=1.
            python -m pytest tests/ -q --tb=line >"$PYTEST_LOG" 2>&1
            PYTEST_RC=$?
        fi
        if [[ $PYTEST_RC -ne 0 ]]; then
            # Persist the full log to a stable path so the failures stay
            # readable after this script exits. The mktemp file gets cleaned
            # up at OS-level eventually; the stable path is what the agent
            # reads when debugging a flake. Andrew 2026-06-10 ordeal taught
            # this: tail -30 dropped FAILED lines under suites with lots of
            # warning output, leaving the agent guessing for ~30 min before
            # I could identify a single flaky test.
            LAST_LOG="${HOME}/.divineos/last_pre_push_pytest.log"
            mkdir -p "$(dirname "$LAST_LOG")"
            cp "$PYTEST_LOG" "$LAST_LOG"
            # Surface failures explicitly — multiple patterns because pytest
            # exits non-zero for several distinct reasons, each leaving a
            # different marker shape in the log:
            #   - FAILED / ERROR: normal assertion / exception failures
            #   - Timeout / Aborted / Killed: subprocess died (e.g. fixture
            #     hit pytest-timeout; this is the shape that bit me 2026-06-12
            #     when a test_corrigibility_e2e fixture timed out at subprocess
            #     setup and the FAILED-only grep returned nothing — burned ~10
            #     min diagnosing a "silent" failure)
            #   - ImportError / ModuleNotFoundError at collection time
            #   - INTERNALERROR from pytest itself
            # The -B 2 context catches the test name that appears on the line
            # before the marker (especially for timeouts).
            echo "" >&2
            echo "[push-readiness] === Failing tests (extracted from log) ===" >&2
            grep -E "^(FAILED|ERROR)\b|\+{2,} Timeout \+{2,}|Aborted|Killed|^ImportError|^ModuleNotFoundError|^INTERNALERROR" -B 2 "$LAST_LOG" >&2 || \
                echo "  (no failure markers found; check the full log for details)" >&2
            echo "" >&2
            echo "[push-readiness] === Last 100 lines of pytest output ===" >&2
            # Bumped from 30 to 100: pytest's "short test summary info" section
            # can sit 30+ lines deep when there are many warnings, so tail -30
            # missed it on dirty trees. 100 covers the typical warning-summary
            # tail without burying signal under pure noise.
            tail -100 "$LAST_LOG" >&2
            rm -f "$PYTEST_LOG"
            echo "" >&2
            echo "[push-readiness] BLOCKED — tests failing (exit 10)." >&2
            echo "[push-readiness] Full log persisted: $LAST_LOG" >&2
            echo "[push-readiness] Fix locally, then push. Do NOT push red." >&2
            echo "[push-readiness] Emergency bypass: DIVINEOS_SKIP_TESTS=1 git push" >&2
            exit 10
        fi
        rm -f "$PYTEST_LOG"
        echo "[push-readiness]   pytest: OK"
    fi
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
