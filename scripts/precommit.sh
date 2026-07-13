#!/bin/bash
# Pre-commit preflight — run this BEFORE `git commit` to fix everything in one pass.
# Usage: bash scripts/precommit.sh
#
# What it does:
#   1. Auto-formats staged files (ruff format)
#   2. Reports lint errors (ruff check)
#   3. Reports type errors (mypy)
#   4. Reports doc drift (test/command counts)
#   5. Reports vulture dead code
#   6. Re-stages auto-fixed files
#
# After this passes, `git commit` will succeed on first try.

set -e

STAGED_PY=$(git diff --cached --name-only --diff-filter=ACM | grep '\.py$' || true)
STAGED_SH=$(git diff --cached --name-only --diff-filter=ACM | grep '\.sh$' || true)

if [ -z "$STAGED_PY" ] && [ -z "$STAGED_SH" ]; then
    echo "No Python or shell files staged."
    exit 0
fi

ERRORS=0

# 0. Line-ending normalization for shell scripts.
# Windows editors write CRLF by default. .gitattributes specifies LF for .sh
# but that only applies at commit-write time; the working copy still has CRLF
# while shellcheck runs. Normalize staged .sh files to LF before any check
# sees them. This eliminates the "dos2unix then re-stage" dance.
if [ -n "$STAGED_SH" ]; then
    echo "=== Normalize .sh line endings ==="
    if command -v dos2unix &>/dev/null; then
        echo "$STAGED_SH" | xargs dos2unix 2>&1 | grep -v "converting" || true
    else
        # Fallback: sed strips \r. Works even without dos2unix.
        while IFS= read -r f; do
            [ -f "$f" ] && sed -i 's/\r$//' "$f"
        done <<< "$STAGED_SH"
    fi
    echo "$STAGED_SH" | xargs git add
    echo "  Normalized and re-staged."
fi

# 0c. U+FFFD scan. Any staged file containing the UTF-8 replacement-character
# byte sequence (EF BF BD) is silently corrupted — typically the result of
# writing non-ASCII via a Bash heredoc on Windows where bytes get re-encoded
# as cp1252. The corruption commits cleanly, tests pass, and the bug only
# surfaces months later when the file lands in a context that hits the JSON
# serializer (which crashes the session). Pre-reg: prereg-5e0c6f492bfa.
# Discovered live 2026-05-04. See lesson e44c7acd-d7f8-4cbd-a49e-7bf1dfd1eda2.
echo "=== U+FFFD Scan ==="
STAGED_ALL=$(git diff --cached --name-only --diff-filter=ACM)
FFFD_HITS=""
if [ -n "$STAGED_ALL" ]; then
    while IFS= read -r f; do
        [ -f "$f" ] || continue
        if grep -Iq $'\xef\xbf\xbd' "$f" 2>/dev/null; then
            FFFD_HITS="${FFFD_HITS}${f}"$'\n'
        fi
    done <<< "$STAGED_ALL"
fi
if [ -n "$FFFD_HITS" ]; then
    echo "  [!] U+FFFD replacement characters found in staged files:"
    while IFS= read -r line; do
        [ -n "$line" ] && echo "      $line"
    done <<< "$FFFD_HITS"
    echo ""
    echo "  These bytes (EF BF BD) crash the API JSON serializer when loaded."
    echo "  Likely cause: non-ASCII written via Bash heredoc on Windows."
    echo "  Fix: open the file, find the garbled chars, replace using Write tool."
    ERRORS=$((ERRORS + 1))
fi

# 1. Auto-format (fix, don't just report)
if [ -n "$STAGED_PY" ]; then
    echo "=== Format ==="
    echo "$STAGED_PY" | xargs ruff format 2>/dev/null
    echo "  Formatted. Re-staging..."
    echo "$STAGED_PY" | xargs git add
fi

# 2. Lint
if [ -n "$STAGED_PY" ]; then
    echo "=== Lint ==="
    if ! echo "$STAGED_PY" | xargs ruff check 2>/dev/null; then
        ERRORS=$((ERRORS + 1))
    fi
fi

# 3. Mypy (whole src/divineos — matches CI exactly)
# Andrew 2026-05-15: previous version ran mypy only on staged src files,
# missing cross-file type errors that emerge from interactions between
# changed and unchanged files. CI ran whole-src and caught those (4
# errors landed and broke main this week). Local precommit now matches
# CI exactly so anything passing here passes CI. Stderr kept visible so
# the actual error messages reach the user instead of getting suppressed.
STAGED_SRC=$(echo "$STAGED_PY" | grep '^src/' || true)
if [ -n "$STAGED_SRC" ]; then
    echo "=== Mypy (whole src/divineos) ==="
    # Wrapped in subprocess_jobs so mypy dies with parent (Job Object kill-on-close
    # on Windows; process-group killpg on POSIX). Root fix for 2026-07-13 leak
    # where mypy children survived parent bash death and ate ~900MB each. Per
    # prereg-dae52c6ca269.
    if ! python -m divineos.core.subprocess_jobs -- mypy src/divineos --ignore-missing-imports; then
        ERRORS=$((ERRORS + 1))
    fi
fi

# 3.5. Deptry — scan code imports vs pyproject deps so undeclared
# transitive packages become loud-fail at commit time. Catches the
# silent-failure root that bit PR #266 (filelock available locally
# via transitive install; CI's clean install pulled red). Per
# prereg-e05fb19ed93f (2026-06-24). Only fires when src/* or
# pyproject.toml is in the staged set — no point scanning when only
# docs/tests changed.
STAGED_DEPTRY_RELEVANT=$(echo "$STAGED_PY" | grep -E "^(src/|scripts/|benchmark/|bootcamp/)" || true)
STAGED_PYPROJECT=$(git diff --cached --name-only --diff-filter=ACM | grep -E "^pyproject\.toml$" || true)
if [ -n "$STAGED_DEPTRY_RELEVANT" ] || [ -n "$STAGED_PYPROJECT" ]; then
    if command -v deptry &>/dev/null; then
        echo "=== Deptry (imports vs pyproject deps) ==="
        if ! deptry . 2>&1 | tail -20; then
            ERRORS=$((ERRORS + 1))
        fi
    fi
fi

# 4. Doc drift — check FIRST; only auto-fix if drift exceeds tolerance.
# Previously --fix ran on EVERY commit, rewriting counts to the exact value
# each time. Across parallel branches each rewrite landed a different number
# on the same line, so every branch collided with main on CLAUDE.md/README
# the moment anything else merged first (the recurring count-conflict tax,
# 2026-06-02). The drift thresholds already tolerate small churn — so within
# tolerance we leave the count line untouched (no rewrite, no conflict), and
# only auto-fix + re-stage when drift actually exceeds tolerance.
echo "=== Doc Drift ==="
if ! python scripts/check_doc_counts.py 2>/dev/null; then
    python scripts/check_doc_counts.py --fix 2>/dev/null || true
    git add CLAUDE.md README.md src/divineos/seed.json docs/ARCHITECTURE.md 2>/dev/null || true
    if ! python scripts/check_doc_counts.py 2>/dev/null; then
        ERRORS=$((ERRORS + 1))
    fi
fi

# 5. Broad exceptions
echo "=== Broad Exceptions ==="
if ! python scripts/check_broad_exceptions.py 2>/dev/null; then
    ERRORS=$((ERRORS + 1))
fi

# 5c. Silent-swallow handlers added in PR diffs (Aria 2026-06-23 after
# Aether named the fail-loud audit class — two real silent-swallow bugs
# found today, one in his conftest, one in my hooks). Diff-only so
# existing instances ungate; new additions require `# fail-soft: <reason>`
# or fall into the documented hook-prelude idiom whitelist. Per
# prereg-<filed-during-build>.
echo "=== Silent-Swallow Handlers ==="
if ! python scripts/check_silent_swallow.py; then
    ERRORS=$((ERRORS + 1))
fi

# 5b. Function-naming theater drift (Dijkstra audit-walk 2026-05-07).
# Catches future drift by flagging functions that start with mythological
# verbs. Manual audit on filing-day found zero violations; this prevents
# regression. Suppressible per-line with `# noqa: BLE001`.
echo "=== Function-Naming (theater drift) ==="
if ! python scripts/check_function_naming.py 2>/dev/null; then
    ERRORS=$((ERRORS + 1))
fi

# 5a. Orphan-modules warning (non-blocking). Round-2 audit (2026-05-07)
# wired this at warning-level: the existing detector found 22 orphans
# (down to ~4 after fixing false-positive shapes) but each remaining
# one needs an individual decision (wire / mark / delete). Surfacing
# on every commit catches new accumulation; not blocking lets the
# existing real orphans wait for their own follow-up PRs.
echo "=== Orphan Modules (informational) ==="
python scripts/check_orphan_modules.py 2>/dev/null || true

# 5b. Pre-reg gate (un-gameable): new mechanisms require a filed pre-reg.
# The gate reads the staged diff and blocks when a new mechanism lacks a
# matching OPEN pre-registration in the ledger. Discipline from the
# gute_bridge docstring made binding. See scripts/check_preregs.py.
echo "=== Pre-reg Gate ==="
if ! python scripts/check_preregs.py; then
    ERRORS=$((ERRORS + 1))
fi

# 5c. Multi-party-review warning. The actual gate runs at commit-msg time
# (see .git/hooks/commit-msg installed by setup/setup-hooks.sh). This is
# an early warning so the operator sees the requirement BEFORE typing
# the commit message. Non-blocking — it only surfaces information.
if [ -f scripts/guardrail_files.txt ] && [ -f scripts/check_multi_party_review.py ]; then
    echo "=== Multi-Party-Review Check ==="
    # Read guardrail list (skip comments + blanks) once, then match.
    # Avoid `set -e` killing the subshell on grep-non-match.
    GUARDRAIL_LIST=$(grep -v '^\s*#' scripts/guardrail_files.txt | grep -v '^\s*$' || true)
    STAGED_GUARDRAILS=$(git diff --cached --name-only | while read -r f; do
        if echo "$GUARDRAIL_LIST" | grep -Fxq "$f"; then
            echo "$f"
        fi
    done || true)
    if [ -n "$STAGED_GUARDRAILS" ]; then
        echo "  [!] Guardrail files in this commit:"
        while IFS= read -r line; do
            [ -n "$line" ] && echo "      $line"
        done <<< "$STAGED_GUARDRAILS"
        DIFF_HASH=$(git diff --cached --unified=3 | sha256sum | cut -c1-64)
        echo ""
        echo "  Before committing, file a Watchmen audit round with:"
        echo "      - CONFIRMS from actor=user"
        echo "      - CONFIRMS from actor=grok | gemini | claude-<variant>"
        echo "      - round focus/notes contain: 'diff-hash: $DIFF_HASH'"
        echo "  Then add to the commit message:"
        echo "      External-Review: <round_id>"
        echo ""
        echo "  The commit-msg hook will block the commit if any piece is missing."
        echo ""

        # Gate-self-test (claim cf05b878, 2026-04-25): the commit-msg
        # hook is what enforces the hash binding. If it isn't installed,
        # the gate is theater — operator-discipline only. Discovered live
        # 2026-04-25 when both that day's External-Review rounds landed
        # without the hook running. Worktree-incompatibility in
        # setup-hooks.sh silently no-op'd the install. Verify here that
        # the hook actually exists and is non-empty BEFORE the operator
        # types the commit message — the operator should see this loudly.
        HOOK_PATH=$(git rev-parse --git-path hooks/commit-msg 2>/dev/null || echo ".git/hooks/commit-msg")
        if [ ! -s "$HOOK_PATH" ]; then
            echo "  [!!] COMMIT-MSG HOOK NOT INSTALLED — gate enforcement absent."
            echo "       Path checked: $HOOK_PATH"
            echo "       Without this hook, the External-Review trailer is"
            echo "       NOT validated at commit time. The hash binding"
            echo "       between the filed round and the landed commit is"
            echo "       operator-discipline only, not structurally enforced."
            echo "       Install: bash setup/setup-hooks.sh (note: has a"
            echo "       worktree-compatibility bug — verify the hook"
            echo "       actually appears at the path above after running,"
            echo "       or write it manually)."
            echo ""
            ERRORS=$((ERRORS + 1))
        fi
    fi
fi

# 5d. Ignore-flag-has-reason check (Aletheia Finding 74, 2026-05-17).
# Refuses pytest --ignore= usages without an adjacent # REASON: comment.
# Substrate-level fix for the bypass-too-broad pattern that recurred
# twice on 2026-05-17 (--ignore=test_check_broad_exceptions masked PR
# #10's new violations because the masking from PR #12 hid them).
if [ -f scripts/check_ignore_has_reason.py ]; then
    echo "=== Ignore-flag has reason ==="
    if ! python scripts/check_ignore_has_reason.py; then
        ERRORS=$((ERRORS + 1))
    fi
fi

# 6. Vulture
if [ -n "$STAGED_SRC" ] && command -v vulture &>/dev/null; then
    echo "=== Vulture ==="
    # shellcheck disable=SC2086
    if ! vulture $STAGED_SRC scripts/vulture_whitelist.py --min-confidence 70 2>/dev/null; then
        ERRORS=$((ERRORS + 1))
    fi
fi

# 6b. Bandit security scan — MEDIUM+ severity. Audit r9-21 #28 wired
# this in after the 12 false-positive B608 findings were marked with
# # nosec on a per-site rationale. Strict mode here means: if a NEW
# medium-severity finding lands without an explicit nosec marker, the
# commit is blocked and the operator must either add the marker (with
# rationale) or fix the SQL composition. Closes the path where bandit
# was a deferred run-this-yourself script no one ran.
if [ -n "$STAGED_SRC" ]; then
    echo "=== Bandit (MEDIUM+) ==="
    if ! python scripts/run_bandit.py --strict 2>/dev/null; then
        ERRORS=$((ERRORS + 1))
    fi
fi

# 6d. Test-CLI linkage check. Audit finding 2026-05-05 (PR #264):
# test file shipped with complete suite for `divineos commitment fulfillment`
# but the actual subcommand never registered with the CLI. Each test failed
# at runtime with "Error: No such command 'fulfillment'". This catches
# the failure mode prospectively — if a staged test invokes a command, the
# command must register on the CLI.
if [ -n "$STAGED_PY" ] && echo "$STAGED_PY" | grep -q "^tests/"; then
    echo "=== Test-CLI Linkage ==="
    if ! python scripts/check_test_cli_linkage.py; then
        ERRORS=$((ERRORS + 1))
    fi
fi

# 6c. Verifier-run stamp. Audit r9-21 round-3+ (prereg-e30878ce3f09):
# precommit running successfully constitutes a verifier run, so we
# stamp the run-log here. The closure-claim commit-msg hook reads
# this log to gate closure-language commit messages on recent
# verification evidence. Without the stamp, "fully closed" / "0
# remaining" / "no remaining surface" phrasing in the commit message
# blocks the commit (round-1 + round-3 audit-cleanup slips both had
# that exact shape).
if [ $ERRORS -eq 0 ]; then
    python scripts/check_closure_claim.py --record "precommit:$(git rev-parse --abbrev-ref HEAD)" 2>/dev/null || true
fi

# 7. Shellcheck on staged .sh files (line endings already normalized in step 0)
if [ -n "$STAGED_SH" ] && command -v shellcheck &>/dev/null; then
    echo "=== Shellcheck ==="
    if ! echo "$STAGED_SH" | xargs shellcheck 2>/dev/null; then
        ERRORS=$((ERRORS + 1))
    fi
fi

# 8. Wiring-gap (informational, non-blocking) — surface any new public
#    function in core/ that has zero callers across src/, tests/, scripts/,
#    or hooks. Documented as informational in the script's docstring; runs
#    here so the report is in front of the agent's eyes BEFORE the commit
#    lands, not after the next external audit catches it.
#    Andrew 2026-05-29: "the inspector who would condemn the dead lightbulbs
#    has no current either." This is the current.
if [ $ERRORS -eq 0 ]; then
    echo "=== Wiring-gap (informational) ==="
    python scripts/wiring_gap_phase1.py --only-zero-callers 2>/dev/null | head -40 || true
fi

echo ""
if [ $ERRORS -eq 0 ]; then
    echo "All clear. git commit will succeed."
else
    echo "$ERRORS check(s) failed. Fix them, then git commit."
fi
exit $ERRORS
