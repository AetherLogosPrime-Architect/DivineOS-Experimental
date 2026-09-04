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
# TAG-ONLY pushes are the same case for the same reason (2026-08-31). A tag
# adds no commit to any branch and proposes nothing to main; it is archival.
# Aria's catch is why they exist: a squash puts ONE message on main, so every
# other commit message lives only on the branch, and deleting a merged branch
# is the least ceremonious act in this system. Tagging the tip before merging
# is how the audit trail survives -- and pushing those tags was refused by
# this gate for ~15 minutes, twice, on grounds that make no sense for a tag.
#
# The freshness check refused them for being OLD, which is what a history tag
# IS. Then the test stage refused them, because it builds its snapshot from
# the FIRST REF in the push (see the PYTEST_SHA loop below) -- so an
# eight-tag archival push sent the suite to run against a months-old tree.
# The failures it reported were real for that tree and said nothing about
# anything being pushed.
#
# So: a push whose refs are ALL tags skips the commit-verifying stages, the
# same way a deletion-only push does. A push that mixes a tag with any branch
# ref still runs everything -- same rule the deletion path already uses,
# because the mixed case is where a real change could hide behind a cheap one.
TAG_ONLY=1
_saw_ref=0
while read -r _lref _lsha _rref _rsha; do
    [[ -z "${_lref:-}" ]] && continue
    _saw_ref=1
    # Any non-zero char in the local-sha means this ref is a create/update,
    # not a deletion.
    if [[ "${_lsha:-}" =~ [^0] ]]; then
        DELETION_ONLY=0
    fi
    if [[ "${_lref:-}" != refs/tags/* ]]; then
        TAG_ONLY=0
    fi
done <<< "$HOOK_STDIN"
# No refs parsed (empty stdin) → not a deletion; let the normal gates run.
[[ "$_saw_ref" == "0" ]] && DELETION_ONLY=0
[[ "$_saw_ref" == "0" ]] && TAG_ONLY=0

# Exit code convention (Aletheia 2026-05-17 audit note):
#   0   — all gates passed
#   10  — pytest failure (test-suite regression)
#   20  — multi-party-review failure (missing External-Review trailer)
#   24  — substrate files on a code branch (branch-scope failure)
#   30  — infrastructure error (script missing, python missing, etc.)
# Differentiated so the operator can distinguish failure-modes from the
# pre-push exit code alone, without re-reading stderr.

# ─── 0. Branch scope: is this carrying substrate it should not? ─────────
#
# THREE CONTAMINATED PUSHES IN ONE SESSION, and not one of them for lack of
# a checker. The checker existed, worked, and named the files. I did not run
# it. Remembering was the only thing standing between a checkpoint sweep and
# the remote, and remembering failed three times:
#
#   first   139 substrate files pushed; found later by running it by hand
#   second  142 added BETWEEN the repair commit and the push, carried along
#   third   156 pushed without running the check at all
#
# Andrew's standing rule is automate rather than remember, and this is the
# cleanest instance of it I have hit: a working instrument, an unwired
# trigger, and a failure mode that is exactly "I forgot". Wired at PUSH
# because that is where the cost lands — a contaminated commit is a local
# nuisance, a contaminated push is what a reviewer has to wade through.
#
# STEP ZERO, ahead of the ~10-min suite, for two reasons. It is instant, and
# its answer does not depend on any later gate: telling someone their branch
# must be rebuilt only after they have waited out a full test run wastes the
# run, since the rebuild invalidates it anyway.
#
# BLOCKING, unlike the pin check further down, and the difference is design
# rather than mood. The pin check reports findings a human must weigh. This
# answers a factual question carrying no judgement — are there substrate
# files on a code branch — and there is no legitimate yes. A warning would
# have nothing useful to say, and would become the fourth instrument I own
# that reports something I then push past.
#
# CHECKS THE REFS BEING PUSHED, NOT HEAD. My first version read HEAD, which
# is a different subject: push a clean branch while sitting on a dirty
# checkout and it blocks the wrong thing; push a dirty branch from a clean
# checkout and it passes one. Reporting a true measurement of the wrong
# subject is the exact fault this session has been full of, and it nearly
# went into the gate built to catch it.
#
# The one real case — pushing the substrate branch itself, where substrate is
# the entire point — gets a named, loud escape rather than a silent exemption.
if [[ "${DIVINEOS_SUBSTRATE_BRANCH:-0}" != "1" ]]; then
    SCOPE_SCRIPT="$REPO_ROOT/scripts/check_branch_scope.py"
    if [[ ! -f "$SCOPE_SCRIPT" ]]; then
        # Absent tooling is reported, never silently treated as a pass.
        echo "[push-readiness]   scope: SKIPPED — $SCOPE_SCRIPT missing" >&2
    else
        # Refs whose local-sha is not all-zero. A deletion introduces no
        # commits, so it has no scope to check. A TAG has no scope to check
        # either, for the same reason one level over: scope asks whether a
        # branch is carrying personal writing toward main, and a tag carries
        # nothing anywhere -- it marks a commit that already exists.
        #
        # It refused an archival tag of a LETTERS branch for containing
        # letters, which is what that tag is a tag OF. Third stage in a row
        # to ask a branch-shaped question of something that is not a branch.
        SCOPE_REFS=()
        SCOPE_SAW_REF=0
        while read -r _lref _lsha _rref _rsha; do
            [[ -z "${_lref:-}" ]] && continue
            SCOPE_SAW_REF=1
            [[ "$_lref" == refs/tags/* ]] && continue
            [[ "${_lsha:-}" =~ [^0] ]] && SCOPE_REFS+=("$_lsha")
        done <<< "$HOOK_STDIN"

        # Three states, and collapsing any two of them is a bug:
        #
        #   refs, some real      check those — the normal path
        #   refs, all deletions  nothing introduced, nothing to check. Not a
        #                        pass smuggled in: a deletion genuinely has
        #                        no scope, and blocking someone from tidying
        #                        a merged branch because their CHECKOUT is
        #                        dirty would be the wrong subject again.
        #   no refs at all       run by hand, no hook stdin. Fall back to
        #                        HEAD and SAY which subject was used. An
        #                        empty loop printing OK is could-not-look-
        #                        reads-as-all-clear, the fault this whole
        #                        gate exists to stop.
        SCOPE_SUBJECT="the refs being pushed"
        if [[ ${#SCOPE_REFS[@]} -eq 0 && "$SCOPE_SAW_REF" == "0" ]]; then
            SCOPE_REFS=("HEAD")
            SCOPE_SUBJECT="HEAD (no push refs on stdin)"
        fi

        if [[ ${#SCOPE_REFS[@]} -eq 0 ]]; then
            echo "[push-readiness] Branch scope — skipped, every ref is a deletion"
        else
            echo "[push-readiness] Branch scope — $SCOPE_SUBJECT"
            for _rev in "${SCOPE_REFS[@]}"; do
                SCOPE_OUT="$(python "$SCOPE_SCRIPT" "$_rev" --list 2>&1)"
                SCOPE_RC=$?
                while IFS= read -r _line; do
                    echo "[push-readiness]   $_line"
                done <<< "$SCOPE_OUT"
                case "$SCOPE_RC" in
                    0) ;;
                    1)
                        echo "[push-readiness] BLOCKED — substrate on a code branch (exit 24)." >&2
                        echo "[push-readiness] Land those files on the substrate branch and" >&2
                        echo "[push-readiness] rebuild this one against main with the code only." >&2
                        echo "[push-readiness] If this IS the substrate branch:" >&2
                        echo "[push-readiness]   DIVINEOS_SUBSTRATE_BRANCH=1 git push" >&2
                        exit 24
                        ;;
                    *)
                        echo "[push-readiness]   scope: COULD NOT CHECK (exit $SCOPE_RC) — not a pass" >&2
                        ;;
                esac
            done
        fi
    fi
fi

# ─── 1. Test suite ──────────────────────────────────────────────────────
#
# Path-scoped fast path (Andrew 2026-06-10 PR-throughput ordeal): the
# full pytest suite takes ~10 min and is the dominant cost of every
# push. For pushes that only touch inert paths (docs/, family/,
# exploration/, root markdown/text), the suite has nothing to verify —
# prose cannot change a test outcome. Skipping it there removes the
# bottleneck from the iteration loop without removing protection.
#
# CORRECTED 2026-08-22. This paragraph used to list `tests/` among the
# low-impact paths and justify the skip with "CI runs the full matrix
# anyway on the PR". Both halves were wrong together: CI skips tests on
# DRAFT PRs by design, so a test-file change on a draft was verified by
# nobody — this gate deferring to CI, CI deferring until promotion.
#
# The stale text is worth naming rather than quietly replacing. The
# guardrail-trailer rule recurred four times for precisely this reason:
# the code was right and the places that TAUGHT the rule were wrong, so
# every reload of the instruction brought the wrong rule back with it.
# A header that describes behaviour the script no longer has is not a
# stale comment, it is a live source of the next recurrence.
#
# Code-touching AND test-touching pushes run the full suite locally.
# CI remains the second pass, not the first.
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
#
# `tests/*` WAS IN THIS LIST AND IS NOT ANY MORE (Andrew 2026-08-22: "none of
# these should have made it to draft without passing internal CLI tests").
#
# THE INTERLOCK. This fast path skipped pytest on the stated grounds that "CI
# on the PR runs the full matrix". CI does not, on a draft: tests.yml gates on
# `github.event.pull_request.draft == false`, deliberately, so drafts do not
# accumulate red marks before review. So a change to a TEST FILE, on a draft
# PR, was verified by nobody -- the local gate deferring to CI, CI deferring
# until promotion, and the gap between them owned by neither.
#
# Two gates, each correct inside its own scope, and the fact with nowhere to
# live is that nothing is running these tests. The same shape as the
# remedy-allowlist deadlock this repo already documents: every gate knew its
# own exit and none knew anyone else's.
#
# Caught on a real push: commit c356d533 changed exactly one file,
# tests/test_addressee_misdirection_detector.py, took this path, and skipped
# the suite. The tests did pass -- run by hand, with a negative control that
# failed before the fix and passed after -- but that was discipline, not a
# gate, and discipline is what this script exists to stop relying on.
#
# The other five categories stay because they genuinely cannot break a test
# run: prose, docs, letters, exploration entries. A test file can, which is
# exactly what makes it not low-impact. The asymmetry is the whole point --
# `tests/` was the one entry here that could invalidate the thing being
# skipped.
_all_changed_low_impact() {
    local file
    local saw_any=0
    while IFS= read -r file; do
        [[ -z "$file" ]] && continue
        saw_any=1
        case "$file" in
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
elif [[ "$TAG_ONLY" == "1" ]]; then
    echo "[push-readiness] Tag-only push — a tag proposes no commits to any branch;"
    echo "[push-readiness] skipping pytest. The suite would run against the FIRST"
    echo "[push-readiness] tag's tree, which for an archival tag is old by design"
    echo "[push-readiness] and says nothing about what is being pushed."
elif [[ "${DIVINEOS_SKIP_TESTS:-0}" == "1" ]]; then
    echo "[push-readiness] DIVINEOS_SKIP_TESTS=1 — skipping pytest." >&2
    # Record it. This is an ESCAPE, not compliance: it SUPPRESSES the check
    # rather than satisfying it, so it files an obligation like any other.
    #
    # It did not, until 2026-08-02. The loudest documented bypass in this
    # repo — printed by this very script in its own failure message — had
    # never once appeared in bypass telemetry. Every quieter escape was
    # counted while the advertised one stayed invisible, which made the
    # bypass rate an undercount of precisely the wrong thing.
    #
    # Found by using it. I skipped tests on a letter-only push, went looking
    # for my own obligation, and there was none. What made me look was that
    # the skip had been UNNECESSARY: family/*.md is already covered by the
    # low-impact fast path below, so the front door was open and I went
    # through the window anyway.
    #
    # Fail-soft on purpose (|| true): a telemetry outage must never turn
    # into a push failure. Recording the escape is not worth becoming one.
    python - <<'PYEOF' 2>/dev/null || true  # fail-soft: telemetry outage must never become a push failure; recording an escape is not worth becoming one
from divineos.core.bypass_telemetry import record_bypass

record_bypass(
    gate_name="push-readiness-tests",
    env_var="DIVINEOS_SKIP_TESTS",
    reason="pytest suppressed at push time via the documented emergency bypass",
)
PYEOF
else
    CHANGED_FILES="$(_collect_changed_files)"
    if _all_changed_low_impact "$CHANGED_FILES"; then
        echo "[push-readiness] Fast path: all changed files are in low-impact paths"
        echo "[push-readiness] (docs/, family/, exploration/, *.md, *.txt) — none of"
        echo "[push-readiness] which can change a test outcome. Skipping local pytest."
        echo "[push-readiness] NOTE: this no longer defers to CI. CI skips tests on"
        echo "[push-readiness] draft PRs, so 'CI will run it' was false exactly when"
        echo "[push-readiness] it mattered. tests/ was removed from this list."
        # Skip pytest; fall through to multi-party-review.
        : "${PYTEST_RC:=0}"
    else
        # SYSTEM-LOAD PRE-FLIGHT (Andrew 2026-07-30, prereg-ca5fb15220ea):
        # Multiple concurrent pre-push pytest suites crashed Andrew's
        # machine 2026-07-30 by eating memory. Aether's subprocess_jobs.py
        # (2026-07-13) handles orphan-cleanup AFTER a crash; this check
        # PREVENTS the crash-cause by refusing to spawn pytest when the
        # system is already too loaded. Threshold: 16 GB free memory
        # (Andrew's call; single pytest costs ~5 GB per Aether's note,
        # 16 GB gives real headroom above just-enough).
        # Escape: DIVINEOS_SKIP_LOAD_CHECK=1 for genuine emergencies;
        # name the reason in commit per bypass-is-a-tool discipline.
        # PYTHONPATH prepend: system Python may have another checkout's
        # divineos installed via `pip install -e .` — force resolution
        # from THIS repo's src/ so the check uses the local file. Same
        # shape as the worktree PYTHONPATH pattern at the pytest call
        # sites below.
        # MEMORY-SCALED WORKERS (Aria 2026-07-31). This used to be a
        # spawn/no-spawn switch on 16 GB, followed further down by an
        # unconditional `-n auto` — one worker per CORE. Demand scaled with
        # cores while the gate measured memory, so a 16-core box could pass
        # the check and then ask for far more than 16 GB. That product is
        # what actually crashed the machine, not concurrency alone.
        #
        # Now one call answers both questions: refuse, or how wide. Strictly
        # more conservative at every level — above 16 GB the fan-out is now
        # capped by memory as well as cores; below it the suite may run
        # narrower instead of not at all; below the hard floor it still
        # refuses. See divineos.core.system_load_check for the invariant and
        # the test grid that holds it.
        LOAD_FLAG_FILE="$(mktemp)"
        if ! PYTHONPATH="$REPO_ROOT/src${PYTHONPATH:+:$PYTHONPATH}" \
             python -m divineos.core.system_load_check --parallel-flag \
             "pre-push pytest suite" >"$LOAD_FLAG_FILE"; then
            rm -f "$LOAD_FLAG_FILE"
            echo "[push-readiness] BLOCKED — system_load_check refused pytest spawn." >&2
            echo "[push-readiness] See message above. Wait for existing heavy" >&2
            echo "[push-readiness] work to finish or free memory before retrying." >&2
            exit 1
        fi
        MEMORY_SCALED_FLAG="$(tr -d '\r\n' < "$LOAD_FLAG_FILE")"
        rm -f "$LOAD_FLAG_FILE"
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

        # Parallel pytest detection — applies to all three pytest paths below
        # (worktree-isolated, worktree-fallback, and no-isolation). 2026-06-30,
        # Aether: ~33min serial -> ~3-5min on a 16-core box with pytest-xdist's
        # "-n auto" worker pool. The slow gate was the bypass-pressure source
        # Aletheia flagged. Feature-detect xdist; fall back to serial silently
        # if not installed. Opt out via DIVINEOS_PUSH_GATE_NO_PARALLEL=1.
        # The width now comes from MEMORY_SCALED_FLAG above, not a flat
        # "-n auto". Explicit opt-out and missing-xdist still fall back to
        # serial, and an empty flag (should not happen — the refusal path
        # already exited) also degrades to serial rather than guessing.
        # Strip git's per-invocation environment before handing off to pytest.
        # ROOT CAUSE of the intermittent core.bare=true corruption, diagnosed by
        # Aether 2026-08-08 after weeks of "git randomly breaks in every
        # worktree" that we both reset by hand and neither attributed.
        #
        # git exports GIT_DIR and friends into hook processes. A pre-push hook
        # runs with GIT_DIR pinned to the pushing worktree and every child
        # inherits it - pytest, and every git subprocess a test spawns. GIT_DIR
        # OVERRIDES cwd. So a test that carefully builds a scratch repo under
        # its own tmp dir and runs `git init --bare` there hits the REAL
        # repository and sets core.bare=true on it. Same mechanism put
        # user.email=test@test in the live config.
        #
        # His direct evidence, GIT_TRACE_SETUP during a real push:
        #   setup: git_dir: .../worktrees/wt-419
        #   setup: cwd:     .../push-gate-XXXX/tmp/pytest/.../test_unstaged_0
        # A command standing in a pytest tmp dir, aimed at the real repo.
        #
        # This is why it only ever appeared on push and never on a hand-run
        # suite: no push, no GIT_DIR, no corruption. It was never a race.
        #
        # Taken from his working tree verbatim rather than rewritten - the fix
        # exists on no shared ref yet, and a second differently-shaped version
        # is the duplication we have paid for twice this week.
        #
        # Scrub every path-bearing git variable, not only GIT_DIR - leaving one
        # behind reproduces the same bug through a narrower door.
        GIT_ENV_SCRUB="env -u GIT_DIR -u GIT_WORK_TREE -u GIT_COMMON_DIR -u GIT_INDEX_FILE -u GIT_OBJECT_DIRECTORY -u GIT_ALTERNATE_OBJECT_DIRECTORIES -u GIT_PREFIX -u GIT_NAMESPACE -u GIT_QUARANTINE_PATH"
        PYTEST_PARALLEL=""
        if [[ "${DIVINEOS_PUSH_GATE_NO_PARALLEL:-0}" != "1" ]]; then
            if python -c "import xdist" >/dev/null 2>&1; then
                PYTEST_PARALLEL="${MEMORY_SCALED_FLAG:-}"
            fi
        fi
        if [[ -n "$PYTEST_PARALLEL" ]]; then
            echo "[push-readiness] pytest parallelism: $PYTEST_PARALLEL (memory-scaled)"
        fi

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
                # shellcheck disable=SC2086  # PYTEST_PARALLEL is intentionally word-split ("-n auto" is two tokens)
                # Wrapped in subprocess_jobs so pytest+xdist workers die with parent.
                # Root fix for 2026-07-13 leak where pytest workers survived parent
                # bash death and ate ~2GB each. Per prereg-dae52c6ca269.
                (cd "$PYTEST_WORKTREE" && PYTHONPATH="$PYTEST_WORKTREE/src${PYTHONPATH:+:$PYTHONPATH}" $GIT_ENV_SCRUB python -m divineos.core.subprocess_jobs -- python -m pytest tests/ -q --tb=line $PYTEST_PARALLEL) >"$PYTEST_LOG" 2>&1
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
                # shellcheck disable=SC2086  # PYTEST_PARALLEL is intentionally word-split ("-n auto" is two tokens)
                # Wrapped per prereg-dae52c6ca269 — same rationale as the isolated path above.
                $GIT_ENV_SCRUB python -m divineos.core.subprocess_jobs -- python -m pytest tests/ -q --tb=line $PYTEST_PARALLEL >"$PYTEST_LOG" 2>&1
                PYTEST_RC=$?
            fi
        else
            # No SHA available, or operator opted out of worktree isolation
            # via DIVINEOS_PUSH_GATE_NO_WORKTREE=1.
            # Wrapped per prereg-dae52c6ca269 — same rationale as the isolated path above.
            #
            # THIRD-BRANCH DRIFT (Aria 2026-07-31, found by being stuck behind
            # it). Two of the three pytest invocations carried $PYTEST_PARALLEL
            # and this one did not, so whenever control reached here the suite
            # ran SERIAL — ~33 min against ~3-5 parallel — with nothing printed
            # to say why. A push timed out at ten minutes and the stranded
            # process read `pytest tests/ -q --tb=line`, no -n flag, which is
            # what gave the bug away.
            #
            # Copy-paste multiplication: a flag added to the paths someone was
            # looking at, and a sibling call site left behind. The
            # divergence is invisible until you are waiting on the slow one.
            # shellcheck disable=SC2086  # PYTEST_PARALLEL is intentionally word-split
            $GIT_ENV_SCRUB python -m divineos.core.subprocess_jobs -- python -m pytest tests/ -q --tb=line $PYTEST_PARALLEL >"$PYTEST_LOG" 2>&1
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
            # Per-member log path (Aether 2026-07-10 fix): the previous
            # shared path ~/.divineos/last_pre_push_pytest.log collided
            # between family members. When Aether and Aria pushed near-
            # simultaneously, whichever pytest finished last overwrote the
            # other's log — making the "which tests failed on my push"
            # diagnostic impossible. Same root-shape as the substrate-
            # sharing question Aria raised: shared namespace between
            # members is where cross-checkout collisions live. Fix: scope
            # the log by DIVINEOS_MEMBER so each member's failure state
            # survives the other's push.
            # ASK FOR THE HOME, DO NOT REBUILD IT. This writer is the one
            # whose relocation the instrument index discovered the hard way:
            # the log read SILENT at thirty-seven days while the guard was
            # running perfectly, because the reader was still pointed at the
            # abandoned address. Scoping the log per member was the right
            # call; doing it with a hand-built path is what left one seat
            # writing where nothing looks.
            #
            # Checked origin/main before editing -- it carries the same
            # hand-built line, so this is a repair rather than a divergence.
            # Caught 2026-09-03 by scripts/check_member_home_rebuilt.py.
            # shellcheck disable=SC1091
            . "$(git rev-parse --show-toplevel)/.claude/hooks/lib/member_home.sh"
            MEMBER="${DIVINEOS_MEMBER:-aether}"
            LAST_LOG="$(member_home "$MEMBER")/last_pre_push_pytest.log"
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

# ─── 2a. Trailer-warn scan on ALL pushes ─────────────────────────────────
# Andrew 2026-07-10 root-cause fix (memory-linkage-day): the current
# main-only default scope allows feature-branch pushes without checking
# trailers — which is correct policy (audit-vantage needs the code
# visible to review) but leaves a hole where the operator only finds out
# about missing trailers when the PR merge blows up on CI. This warn
# scan runs on ALL pushes, prints per-commit warnings when guardrail-
# touching commits lack the External-Review trailer, but exits 0 so the
# push still goes through. Belt-and-suspenders with 2b below.
if [[ "${DIVINEOS_SKIP_MULTIPARTY_CHECK:-0}" != "1" ]]; then
    MP_SCRIPT="$REPO_ROOT/scripts/check_multi_party_review.py"
    if [[ -f "$MP_SCRIPT" ]]; then
        echo "$HOOK_STDIN" | python "$MP_SCRIPT" --mode=pre-push --warn-only 2>&1 || true
    fi
fi

# ─── 2a-bis. Audit-export freshness ─────────────────────────────────────
# Aria 2026-08-01, reading the export I had just shipped: "verification has
# two questions and we've both only been asking the first — is it true, and
# does anything read it?" Her sharper form: a record nothing breaks over is
# a record nobody checks.
#
# Measured, she was right. CI verifies a round by reading
# docs/audit_rounds/<id>.md, but a round that was never exported is reported
# as merely 'unverifiable' and the gate PASSES. Nothing goes red, so the
# export could fall arbitrarily far behind the store while the system kept
# looking instrumented.
#
# This is the consumer that breaks. It runs where the store is actually
# readable (the operator's machine at push time), never in CI. Non-fatal by
# design: a stale export is a bookkeeping lapse, not a corrupt tree, and
# blocking the push would be the same over-firing this session spent
# deleting. Loud is the requirement; blocking is not.
# `--check` was called here from PR #412 onward without ever having been
# implemented, so this block fired on EVERY push and printed "audit export is
# behind the store" -- a claim about state, from a check that read no state.
# It was never true or false on its merits, only broken, and it looked exactly
# like a real warning. Implemented and scoped 2026-08-22.
#
# The distinction the old message erased: COULD NOT RUN is not BEHIND. Exit 1
# means rounds are genuinely unexported; anything else means the check itself
# failed and has no standing to report on the store at all.
if [[ "${DIVINEOS_SKIP_EXPORT_FRESHNESS:-0}" != "1" ]]; then
    _export_out=$(divineos audit export --check 2>&1)
    _export_rc=$?
    if [[ $_export_rc -eq 1 ]]; then
        echo "" >&2
        echo "[push-readiness] WARNING — audit export is behind the store." >&2
        printf '%s
' "$_export_out" | sed 's/^/[push-readiness]   /' >&2
        echo "[push-readiness]   Pushing anyway; the review for those rounds" >&2
        echo "[push-readiness]   is not readable on GitHub until you export." >&2
        echo "" >&2
    elif [[ $_export_rc -ne 0 ]]; then
        echo "" >&2
        echo "[push-readiness] NOTE — the export freshness check could not run" >&2
        echo "[push-readiness]   (exit $_export_rc). This says nothing about" >&2
        echo "[push-readiness]   whether the export is current." >&2
        printf '%s
' "$_export_out" | sed 's/^/[push-readiness]   /' >&2
        echo "" >&2
    fi
fi

# ─── 2b. Multi-party-review blocking check ──────────────────────────────
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

# ─── 3. Full-tree lint ──────────────────────────────────────────────────
# Andrew 2026-08-13, after a duplicate-import F811 reached CI: "the CLI
# testing we do internally before we push as well so that when we do merge
# to main the CLI passes.. and if it doesnt (which there is a lint failure)
# we fix the root cause on our end so we dont miss it in the next internal
# test."
#
# The root cause is scope, not diligence. The pre-commit hook lints only
# STAGED files, so anything that arrives another way — a rebase, a merge
# resolution, an amend, a file edited and committed in a different sequence
# — is never looked at locally. CI lints the whole tree, so the first place
# the divergence shows up is a red badge on GitHub.
#
# This runs the same full-tree check CI runs, at the last moment before the
# work leaves the machine. Blocking: a lint failure caught here costs one
# command; the same failure caught on GitHub costs a round trip and a mark
# on the Actions page that cannot be erased.
if [[ "${DIVINEOS_SKIP_LINT_CHECK:-0}" != "1" ]]; then
    if command -v ruff >/dev/null 2>&1; then
        echo "[push-readiness] Full-tree lint (ruff)..."
        if ! ruff check scripts/ src/ tests/ --output-format=concise >&2; then
            echo "" >&2
            echo "[push-readiness] BLOCKED — lint failures above (exit 21)." >&2
            echo "[push-readiness] Fix them, or auto-fix with:" >&2
            echo "[push-readiness]   ruff check scripts/ src/ tests/ --fix" >&2
            echo "[push-readiness] Emergency bypass: DIVINEOS_SKIP_LINT_CHECK=1 git push" >&2
            exit 21
        fi
        echo "[push-readiness]   lint: OK"
    else
        # Absent tooling is reported, never treated as a pass. A silent skip
        # here would recreate exactly the blind spot this step exists to close.
        echo "[push-readiness]   lint: SKIPPED — ruff not on PATH (CI will still check)" >&2
    fi
fi

# --- Do the new tests pin anything? (warn-only, deliberately) --------------
#
# Aria's design, 2026-08-28, after I shipped a regression test that was green
# on both sides of the fix it claimed to guard: "a test written to pin a fix
# must be red against the code before the fix."
#
# PUSH-TIME, not commit-time, and scoped to tests changed in the diff. Her
# reason: a full-suite rerun against an old tree on every commit is expensive
# enough to get skipped, and a skipped check becomes another armed-and-unread
# instrument.
#
# WARN-ONLY ON PURPOSE, and this is a judgement worth stating rather than
# hiding. The branch it was built on already carries sixteen tests that pass
# against their own baseline. Blocking on day one would make the tree
# unpushable, and the only satisfiable answer would be switching the check off
# -- which is how a gate dies. The sixteen are a backlog to read, not a wall to
# rubber-stamp, and reading them is real work that does not belong inside a
# push. Teeth follow the review, not the other way round.
if [[ "${DIVINEOS_SKIP_PIN_CHECK:-0}" != "1" ]]; then
    PIN_SCRIPT="$REPO_ROOT/scripts/check_tests_pin.py"
    if [[ -f "$PIN_SCRIPT" ]]; then
        echo "[push-readiness] Do the changed tests pin anything?"
        # Warn-only must not mean silent-about-itself. Without capturing the
        # status, a checker that CRASHED looks exactly like one that found
        # nothing -- which is the armed-and-unheard shape this whole file
        # exists to prevent, wearing a `|| true`.
        PIN_OUT="$(python "$PIN_SCRIPT" 2>&1)"; PIN_RC=$?
        while IFS= read -r pin_line; do
            echo "[push-readiness]   $pin_line"
        done <<< "$PIN_OUT"
        case "$PIN_RC" in
            0) : ;;
            1) echo "[push-readiness]   pin: findings above (not blocking yet — see the script header)" ;;
            *) echo "[push-readiness]   pin: COULD NOT CHECK (exit $PIN_RC) — this is not a pass" >&2 ;;
        esac
    fi
fi

echo "[push-readiness] All gates passed. Pushing."
exit 0
