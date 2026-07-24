#!/bin/bash
# Setup script to install Git hooks for DivineOS
# Run this after cloning the repository: bash setup-hooks.sh

echo "Setting up Git hooks for DivineOS..."

# Create hooks directory if it doesn't exist
HOOKS_DIR=".git/hooks"
mkdir -p "$HOOKS_DIR"
echo "Created $HOOKS_DIR directory"

# Configure Git to use the hooks directory
git config core.hooksPath "$HOOKS_DIR"
echo "Configured Git to use hooks from $HOOKS_DIR"

# Create pre-commit hook
cat > "$HOOKS_DIR/pre-commit" << 'EOF'
#!/bin/bash
# Pre-commit hook for DivineOS
# Enforces ruff formatting, linting, mypy, doc-drift, dead-code, and shellcheck

set -e

# .db guard (2026-06-30, backstop for the 2026-06-26 key-leak class).
# Aether 2026-06-26 committed event_ledger.db so Perplexity could see it
# for an external audit. An Anthropic API key inside the DB rode into
# git history; GitHub flagged it; the key had to be revoked.
#
# Root structural fix lives in core/secret_redactor.py — secrets never
# reach the ledger in the first place. This guard is the second layer:
# even if a secret slipped through redaction, the DB itself cannot be
# committed without an explicit acknowledgment.
#
# To override (e.g., committing a known-safe seed/fixture that ships
# with the package), set DIVINEOS_ALLOW_DB_COMMIT=1 for the invocation.
# Loud-by-design — typing it is the consent signal that the operator
# has audited the file.
DB_STAGED=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\.db$' || true)
if [[ -n "$DB_STAGED" ]]; then
    if [[ "${DIVINEOS_ALLOW_DB_COMMIT:-}" == "1" ]]; then
        echo "WARNING: DIVINEOS_ALLOW_DB_COMMIT=1 — letting .db file(s) through:"
        echo "$DB_STAGED" | sed 's/^/  /'
    else
        echo "" >&2
        echo "BLOCKED: .db file(s) staged for commit:" >&2
        echo "$DB_STAGED" | sed 's/^/  /' >&2
        echo "" >&2
        echo "Database files MUST NOT be committed — 2026-06-26 leaked an" >&2
        echo "Anthropic API key this way (event_ledger.db contained a key" >&2
        echo "from a tool-call payload, then was unignored for an audit)." >&2
        echo "" >&2
        echo "If the .db file is genuinely intended (e.g. a seed/fixture)," >&2
        echo "re-run the commit with:" >&2
        echo "  DIVINEOS_ALLOW_DB_COMMIT=1 git commit ..." >&2
        echo "" >&2
        echo "Otherwise: 'git restore --staged <file>' to unstage and add" >&2
        echo "the path to .gitignore." >&2
        exit 1
    fi
fi

echo "Running ruff format check..."
# Substrate-fix 2026-05-10 (Aether, hold-644d325062b2):
# The prior behavior aborted the commit and asked the operator to
# manually re-stage formatted files. That created two failure modes:
#   1. Friction tax — every commit that touched whitespace required
#      a re-stage + re-commit cycle, sometimes multiple times per
#      commit.
#   2. Audit-hash drift — when an External-Review round was filed
#      with a hash bound to pre-format staged content, the auto-
#      format here drifted the hash and the multi-party-review gate
#      rejected the commit, requiring a fresh audit round filed
#      against the post-format hash.
# Ruff format is deterministic and safe. Auto-staging the formatted
# files lets the commit proceed. For guardrail-touching commits,
# operators should run \`bash scripts/precommit.sh\` BEFORE filing
# the External-Review round so the audit-bound hash matches the
# eventual commit hash.
ruff format --check src/ tests/ || {
    echo "Formatting violations detected. Running ruff format to fix..."
    ruff format src/ tests/
    echo "Auto-staging formatted .py files that were already staged..."
    # Only re-stage already-staged files. Working-tree-only changes
    # stay unstaged so the operator's intent is preserved.
    # 2026-06-09: was '\.py\$' (escaped dollar) which matched literal
    # backslash-dollar instead of files ending in .py. The grep returned
    # empty, xargs got nothing, re-staging silently did nothing, and CI
    # ate the ruff failure on every PR. The fix is one character: '\.py$'.
    git diff --cached --name-only --diff-filter=ACM | grep -E '\.py$' | xargs --no-run-if-empty git add
    echo "Re-checking format after auto-stage..."
    ruff format --check src/ tests/ || {
        echo "Format still failing after auto-format — investigate manually."
        exit 1
    }
    echo "  Format clean after auto-stage; continuing."
}

echo "Running ruff lint check..."
ruff check src/ tests/ || {
    echo "Linting violations detected. Please fix them before committing."
    exit 1
}

echo "Running mypy type check..."
mypy src/divineos --ignore-missing-imports || {
    echo "Type errors detected. Please fix them before committing."
    exit 1
}

echo "Checking doc counts for drift..."
# Andrew 2026-06-12: auto-fix flipped to DEFAULT ON, with opt-out via
# DIVINEOS_DOC_COUNT_NO_AUTOFIX=1.
#
# History: the 2026-06-09 opt-in design was a valid response to cross-
# branch rebase conflicts on the count line — every branch auto-bumped
# to slightly different numbers, then collided on rebase. But the
# opt-in cost the operator a manual --fix step on every commit and bit
# me multiple times during the 2026-06-12 structural-fix session.
#
# The better fix is monotonic-only-raise inside check_doc_counts.py:
# two branches with different higher counts no longer conflict because
# the lower-count branch becomes a no-op once main has the higher
# count. With monotonic auto-fix safe, default ON removes the "remember
# to opt in" tax that Andrew 2026-06-10 PR-marathon teaching called
# out as the wrong structural shape ("auto-generate or remove, not
# always run").
if ! python scripts/check_doc_counts.py 2>/dev/null; then
    if [[ "${DIVINEOS_DOC_COUNT_NO_AUTOFIX:-}" == "1" ]]; then
        echo ""
        echo "Doc-count drift detected. Auto-fix suppressed via DIVINEOS_DOC_COUNT_NO_AUTOFIX=1."
        echo "Re-run without the env var to auto-fix and re-stage."
        echo ""
        python scripts/check_doc_counts.py
        exit 1
    fi
    python scripts/check_doc_counts.py --fix 2>/dev/null || true
    git add CLAUDE.md README.md src/divineos/seed.json docs/ARCHITECTURE.md 2>/dev/null || true
    python scripts/check_doc_counts.py || {
        echo "Doc counts still drifted after auto-fix (likely a non-count error). Investigate manually."
        exit 1
    }
fi

echo "Running vulture dead-code check..."
if command -v vulture &>/dev/null; then
    vulture src/divineos/ scripts/vulture_whitelist.py --min-confidence 70 || {
        echo "Dead code detected. Remove it or add to scripts/vulture_whitelist.py."
        exit 1
    }
else
    echo "  (vulture not installed, skipping — pip install vulture)"
fi

echo "Running shellcheck on hooks..."
if command -v shellcheck &>/dev/null; then
    shellcheck .claude/hooks/*.sh || {
        echo "Shellcheck violations in hook scripts. Fix them before committing."
        exit 1
    }
else
    echo "  (shellcheck not installed, skipping)"
fi

echo "All checks passed!"
exit 0
EOF

chmod +x "$HOOKS_DIR/pre-commit"
echo "Created pre-commit hook at $HOOKS_DIR/pre-commit"

# Create commit-msg hook.
#
# Gate-altitude correction (Andrew 2026-05-12): commits should never be
# blocked. Work-preservation matters; cross-vantage audit needs to SEE the
# diffs to audit them; the boundary that needs protection is the merge
# into main, not every commit on a feature branch. The multi-party-review
# check runs here in ADVISORY mode (warns informationally; doesn't block).
# The real gate fires at pre-push when target is refs/heads/main.
#
# The closure-claim gate stays at commit-msg time; it targets a different
# failure-mode (closure-language without verification) that should be
# caught at commit-time regardless of where the commit lives.
cat > "$HOOKS_DIR/commit-msg" << 'EOF'
#!/bin/bash
# commit-msg hook for DivineOS.
#
# 1. Multi-party-review: ADVISORY at commit-time. Warns if guardrail
#    files are touched without the trailer; does not block. The real
#    block fires at pre-push when target is refs/heads/main. Reason:
#    commits to feature branches must succeed so cross-vantage audit
#    can see the diffs; the protected boundary is merge-into-main.
# 2. Closure-claim: blocks commit messages with closure-language
#    ("fully closed", "all N items addressed", "everything landed",
#    "body-building done") unless a recent verifier-run is recorded.
#    Defends against the round-1 / round-3 audit-cleanup recurrence
#    pattern: closure-language commit messages without actual
#    verification of the claim. Pre-reg: prereg-e30878ce3f09.
#    Bypass: --no-verify on the commit (visible bypass only).
#
# Both delegate to standalone scripts; both fail-open if their script
# is missing (hooks must never block work because of broken infra).

set -e

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
MULTI_PARTY="$REPO_ROOT/scripts/check_multi_party_review.py"
CLOSURE_CLAIM="$REPO_ROOT/scripts/check_closure_claim.py"
ROOT_CAUSE_AUDIT="$REPO_ROOT/scripts/check_root_cause_audit.py"
WIRING_CLAIMS="$REPO_ROOT/scripts/check_wiring_claims.py"
PREREG_INFRA="$REPO_ROOT/scripts/check_prereg_for_new_infra.py"

# 1. Multi-party-review — INFORMATIONAL at commit-time.
# Script never blocks at commit-time; just warns if guardrails touched
# without trailer. Real gate fires at pre-push.
if [[ -f "$MULTI_PARTY" ]]; then
    python "$MULTI_PARTY" "$1" || true
fi

# 2. Closure-claim gate.
if [[ -f "$CLOSURE_CLAIM" ]]; then
    python "$CLOSURE_CLAIM" "$1" || exit 1
fi

# 3. Root-cause-audit gate — ADVISORY at commit-time, BLOCKING at
# pre-push-to-main (added below). Enforces family-level investigation
# before bugfix-shaped commits. Family this addresses: instance-fix-
# without-family-audit (substrate-knowledge round-38d9fd161175). The
# OS describes the discipline in 67a0ff39; this gate makes the
# discipline structural rather than advisory.
if [[ -f "$ROOT_CAUSE_AUDIT" ]]; then
    python "$ROOT_CAUSE_AUDIT" --mode=commit-msg --commit-msg-file "$1" || true
fi

# 4. Wiring-claim gate — SOFT WARNING. Surfaces "wire X to Y" /
# "bridge", "integrate", "connect", "end-to-end", "close the gap"
# language and reminds the operator to verify both sides exercised.
# Closes Aletheia Finding 1 wire-decision for check_wiring_claims.py.
# Never blocks; always exits 0. Operator reads the warning, decides.
if [[ -f "$WIRING_CLAIMS" ]]; then
    python "$WIRING_CLAIMS" "$1" || true
fi

# 5. Pre-reg-required-before-infra — BLOCK on new files under
# src/divineos/core/ without prereg-XXX reference in the commit
# message. Bypass: DIVINEOS_NEW_INFRA_NO_PREREG=1. Andrew 2026-05-18.
if [[ -f "$PREREG_INFRA" ]]; then
    python "$PREREG_INFRA" "$1" || exit 1
fi

exit 0
EOF

chmod +x "$HOOKS_DIR/commit-msg"
echo "Created commit-msg hook at $HOOKS_DIR/commit-msg"

# Create pre-push hook with THREE safety checks:
#   1. branch-freshness: blocks branches whose base is stale relative
#      to origin/main (silent-revert prevention, claim d3baec5a).
#   2. force-push-safety: blocks force-pushes that would shrink a
#      branch's unique-vs-main work below safety thresholds — catches
#      botched-rebase work-loss (prereg-c1c896a67321, 2026-05-04).
#   3. multi-party-review: when target is refs/heads/main, blocks
#      commits in the push-range that touch guardrail files without
#      a valid External-Review trailer. This is the gate that used
#      to fire at commit-msg time; moved to pre-push 2026-05-12 per
#      Andrew's altitude-correction (commits should never be blocked;
#      only push-to-main should). "Main" means any production-bound
#      branch (DivineOS prod's main AND DivineOS-Experimental's main).
# All delegate to standalone scripts so the logic stays testable.
cat > "$HOOKS_DIR/pre-push" << 'EOF'
#!/bin/bash
# pre-push hook for DivineOS — five safety checks.
# Bypass env vars (use sparingly; explain in commit message):
#   DIVINEOS_SKIP_FRESHNESS_CHECK=1   — bypass freshness
#   DIVINEOS_FORCE_PUSH_OK=1          — bypass force-push safety
#   DIVINEOS_SKIP_TESTS=1             — bypass local pytest (push-readiness)
#   DIVINEOS_SKIP_MULTIPARTY_CHECK=1  — bypass External-Review trailer check
#   DIVINEOS_EMERGENCY_PUSH=1         — bypass push-readiness entirely

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
FRESHNESS="$REPO_ROOT/scripts/check_branch_freshness.sh"
FORCE_SAFETY="$REPO_ROOT/scripts/check_force_push_safety.sh"
MULTI_PARTY="$REPO_ROOT/scripts/check_multi_party_review.py"
ROOT_CAUSE_AUDIT="$REPO_ROOT/scripts/check_root_cause_audit.py"
PUSH_READINESS="$REPO_ROOT/scripts/check_push_readiness.sh"

# Capture stdin once — every gate that reads ref-update lines uses it.
HOOK_STDIN=$(cat)

# 1. Branch freshness.
if [[ -x "$FRESHNESS" ]]; then
    "$FRESHNESS" origin main
    RC=$?
    if [[ $RC -eq 1 ]]; then
        # Stale base detected — script already printed instructions.
        exit 1
    fi
fi

# 2. Force-push safety.
if [[ -x "$FORCE_SAFETY" ]]; then
    echo "$HOOK_STDIN" | "$FORCE_SAFETY" "$1"
    RC=$?
    if [[ $RC -eq 1 ]]; then
        exit 1
    fi
fi

# 3. Multi-party-review (pre-push mode, target=main only).
# Walks the push-range and blocks if any commit touching guardrail
# files lacks the External-Review trailer. Default mode filters to
# refs/heads/main; the push-readiness gate below also runs --strict
# which catches feature-branch pushes that will fail CI.
if [[ -f "$MULTI_PARTY" ]]; then
    echo "$HOOK_STDIN" | python "$MULTI_PARTY" --mode=pre-push
    RC=$?
    if [[ $RC -eq 1 ]]; then
        exit 1
    fi
fi

# 4. Root-cause-audit (pre-push mode).
# Walks the push-range when target is refs/heads/main. Blocks if any
# fix-shaped commit lacks a Root-Cause-Audit trailer pointing to a
# valid root-cause-audit round. The script's pre-push mode handles
# the ref-filtering internally.
if [[ -f "$ROOT_CAUSE_AUDIT" ]]; then
    echo "$HOOK_STDIN" | python "$ROOT_CAUSE_AUDIT" --mode=pre-push
    RC=$?
    if [[ $RC -eq 1 ]]; then
        exit 1
    fi
fi

# 5. Push readiness (NEW, added 2026-05-17 after Andrew named the
# "red badges on public activity feed" failure mode). Runs the full
# pytest suite + multi-party-review --strict so feature-branch pushes
# that would fail CI get caught BEFORE leaving the developer machine.
# The bugs aren't the showstopper; the public-visibility of red runs is.
if [[ -x "$PUSH_READINESS" ]]; then
    echo "$HOOK_STDIN" | "$PUSH_READINESS"
    RC=$?
    if [[ $RC -ne 0 ]]; then
        exit $RC
    fi
fi

exit 0
EOF

chmod +x "$HOOKS_DIR/pre-push"
echo "Created pre-push hook at $HOOKS_DIR/pre-push"

# Install post-commit hook — delegates to every post-commit-*.sh script
# under .claude/hooks/. 2026-07-07 fix: the prior single-script delegator
# hard-coded post-commit-auto-close.sh and silently orphaned every other
# post-commit hook (post-commit-audit-visibility.sh, post-commit-auto-
# integrate-corrections.sh, etc.). The loop pattern is a will-to-structure
# fix in Andrew's frame — new post-commit hooks are picked up automatically
# instead of relying on someone remembering to add them to the delegator.
cat > "$HOOKS_DIR/post-commit" << 'EOF'
#!/bin/bash
# Post-commit hook — delegates to every post-commit-*.sh under
# .claude/hooks/. Fail-open per script: any failure exits 0 for that
# script and continues the loop, so no hook can break the workflow or
# starve later hooks.
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
if [ -z "$REPO_ROOT" ]; then
    exit 0
fi
HOOKS_SRC="$REPO_ROOT/.claude/hooks"
if [ ! -d "$HOOKS_SRC" ]; then
    exit 0
fi
for hook in "$HOOKS_SRC"/post-commit-*.sh; do
    if [ -x "$hook" ]; then
        bash "$hook" || true
    fi
done
exit 0
EOF

chmod +x "$HOOKS_DIR/post-commit"
echo "Created post-commit hook at $HOOKS_DIR/post-commit"

# Install prepare-commit-msg hook — trailer-automation for guardrail commits.
#
# The recurring failure pattern (PR #287 was the third recurrence): a commit
# touches a guardrail-listed file, the operator forgets to add the
# `External-Review: round-<id>` trailer, the commit lands locally fine,
# the push succeeds, the PR's multi-party-review check fails because the
# per-commit branch check requires the trailer inline on each guardrail-
# touching commit, and the fix is a rebase + force-push.
#
# This hook closes the loop at commit-time so it can't recur:
#   1. Scan staged files against scripts/guardrail_files.txt.
#   2. If none are guardrail-listed, exit clean (no-op for normal commits).
#   3. If guardrail-listed AND the commit message already has an
#      External-Review trailer, exit clean (operator added it manually).
#   4. If DIVINEOS_AUDIT_ROUND=<round-id> env var is set, append that
#      trailer to the commit message and exit clean.
#   5. If exactly one open audit round was filed in the last 4 hours by
#      a non-internal actor (aether/aletheia/aria/auditor/etc.), append
#      that round's id as the trailer with a freshness note.
#   6. Otherwise: fail loud, name the format, list candidate rounds.
#
# Skip when COMMIT_SOURCE is "merge" (merge commits don't get trailers
# added automatically — keeps merge-commit messages clean).
cat > "$HOOKS_DIR/prepare-commit-msg" << 'EOF'
#!/bin/bash
# Prepare-commit-msg hook — auto-stamp External-Review trailer for
# guardrail-touching commits. Closes the PR-stamp-missing failure mode
# at commit-time rather than catching it at PR-time after force-push.
#
# Source: setup/setup-hooks.sh (regenerate via `bash setup/setup-hooks.sh`).

set -e

COMMIT_MSG_FILE="$1"
COMMIT_SOURCE="$2"

# Skip merge commits — they don't need per-commit External-Review trailers.
if [[ "$COMMIT_SOURCE" == "merge" ]]; then
    exit 0
fi

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
GUARDRAIL_LIST="$REPO_ROOT/scripts/guardrail_files.txt"
if [[ ! -f "$GUARDRAIL_LIST" ]]; then
    exit 0  # No guardrail list — nothing to enforce
fi

# Resolve a Python interpreter that can import divineos. Prevents the
# silent-fail-OPEN pattern named in round-1 and round-2 external audits
# (12 hooks total: 11 in .claude/hooks/ plus this one, recurrence #12).
# Bare `python` in the git-hook PATH resolves to a system interpreter
# without divineos installed, `import divineos.core.watchmen.store`
# fails silently, the substance-check's fail-open path fires, and the
# trailer gate passes ceremony without substance. 2026-07-21 substance-
# check reintroduced exactly the class the audits already killed
# (Peirce catch: pattern-inheritance at code-adjacent-copy time overrode
# named-audit-knowledge). find_divineos_python walks sealed-venv
# candidates and prepends the active worktree's src/ to PYTHONPATH.
# Confirmed pattern: Andrew 2026-07-13 CONFIRM on the sibling hook-
# python-dep fix (same class, same solution shape).
LIB_SH="$REPO_ROOT/.claude/hooks/_lib.sh"
if [[ -f "$LIB_SH" ]]; then
    # shellcheck disable=SC1090
    source "$LIB_SH"
    PYTHON_BIN="$(find_divineos_python 2>/dev/null)" || PYTHON_BIN="python"
else
    PYTHON_BIN="python"
fi

# Find any staged file that matches a guardrail-listed path.
STAGED_GUARDRAIL=""
while IFS= read -r f; do
    [[ -z "$f" ]] && continue
    if grep -Fxq "$f" "$GUARDRAIL_LIST" 2>/dev/null; then
        STAGED_GUARDRAIL+="  $f"$'\n'
    fi
done < <(git diff --cached --name-only --diff-filter=ACM)

if [[ -z "$STAGED_GUARDRAIL" ]]; then
    exit 0  # No guardrail files touched — no trailer required
fi

# A guardrail file is staged. Resolve the round-id from any source
# (existing trailer, env-provided, or auto-attach) and fall through to
# the substance-check at the end. Refactored 2026-07-21 (council-
# a81fff875c52) per Dijkstra single-point-of-truth: one substance-check
# block handles all three paths instead of duplicated inline checks.
RESOLVED_ROUND_ID=""
if grep -qE '^External-Review:\s*round-' "$COMMIT_MSG_FILE"; then
    RESOLVED_ROUND_ID=$(grep -oE 'round-[a-f0-9]+' "$COMMIT_MSG_FILE" | head -1)
fi

# No trailer yet. Try environment override next.
if [[ -z "$RESOLVED_ROUND_ID" && -n "${DIVINEOS_AUDIT_ROUND:-}" ]]; then
    ROUND_ID="${DIVINEOS_AUDIT_ROUND}"
    if [[ ! "$ROUND_ID" =~ ^round-[a-f0-9]{6,}$ ]]; then
        echo "" >&2
        echo "BLOCKED: DIVINEOS_AUDIT_ROUND='${ROUND_ID}' is not a valid round id." >&2
        echo "Expected shape: round-<hex>, e.g. round-a7fe5f413c47" >&2
        exit 1
    fi
    {
        echo ""
        echo "External-Review: ${ROUND_ID}"
    } >> "$COMMIT_MSG_FILE"
    echo "prepare-commit-msg: trailer added from DIVINEOS_AUDIT_ROUND: ${ROUND_ID}"
    RESOLVED_ROUND_ID="$ROUND_ID"
fi

# No env override — query the audit_rounds table for recent open rounds.
# Inline Python keeps the hook self-contained (no CLI dependency).
RECENT_ROUNDS=$(python -c '
import time
try:
    from divineos.core.knowledge._base import _get_connection
except ImportError:
    raise SystemExit(0)
cutoff = time.time() - 4 * 3600
try:
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT round_id, focus FROM audit_rounds "
            "WHERE created_at > ? ORDER BY created_at DESC LIMIT 5",
            (cutoff,),
        ).fetchall()
    finally:
        conn.close()
except Exception:
    raise SystemExit(0)
for rid, focus in rows:
    print(f"{rid} {focus[:60]}")
' 2>/dev/null || true)

# Count non-empty lines starting with round-
ROUND_COUNT=$(echo "$RECENT_ROUNDS" | grep -cE '^round-' || true)

if [[ -z "$RESOLVED_ROUND_ID" && "$ROUND_COUNT" == "1" ]]; then
    ROUND_ID=$(echo "$RECENT_ROUNDS" | grep -oE 'round-[a-f0-9]+' | head -1)
    {
        echo ""
        echo "External-Review: ${ROUND_ID}"
    } >> "$COMMIT_MSG_FILE"
    echo "prepare-commit-msg: trailer auto-attached from sole recent open round: ${ROUND_ID}"
    echo "  (filed within the last 4 hours — if this isn't the right round, abort and re-commit"
    echo "   with DIVINEOS_AUDIT_ROUND=round-<correct-id> git commit ...)"
    RESOLVED_ROUND_ID="$ROUND_ID"
fi

# Andrew 2026-07-24 design correction: WARN not BLOCK at commit-time.
# Commits and pushes-to-origin require no external review; only merge-to-main
# does. The chicken-egg was: guardrail changes couldn't be committed for
# review because commit required review. Push origin IS how external
# reviewers see the change to review it. Real gate stays at merge-to-main.
if [[ -z "$RESOLVED_ROUND_ID" ]]; then
    echo "" >&2
    echo "WARN: this commit touches guardrail-listed file(s):" >&2
    echo -n "$STAGED_GUARDRAIL" >&2
    echo "" >&2
    echo "No External-Review trailer set. Commits proceed without a trailer;" >&2
    echo "the real multi-party-review gate fires at merge-to-main." >&2
    echo "To attach a trailer now (recommended for guardrail changes):" >&2
    if [[ "$ROUND_COUNT" == "0" ]]; then
        echo "  divineos audit submit-round \"<focus>\" --actor <name> --source-ref \"<branch>\"" >&2
        echo "  then re-commit with DIVINEOS_AUDIT_ROUND=round-<id> git commit ..." >&2
    else
        echo "  Recent open rounds (pick one and re-commit with DIVINEOS_AUDIT_ROUND=round-<id>):" >&2
        echo "$RECENT_ROUNDS" | sed 's/^/    /' >&2
    fi
    echo "" >&2
    exit 0
fi

# ---------------------------------------------------------------------------
# SUBSTANCE-CHECK (2026-07-21, council-a81fff875c52)
#
# Truth #15 fix: the pre-existing gate checked trailer PRESENCE but never
# validated trailer SUBSTANCE. I proved this hole exists by walking through
# it seven times in one session (empty rounds + trailer stamps = fake
# external-review provenance). Fix: after trailer is resolved, query the
# referenced round's findings and require at least one CONFIRMS from an
# external actor (user OR grok/gemini/claude-variant, NEVER bare claude).
#
# Fail-open on infrastructure failures: DB unreachable, python missing,
# module import error. Threat model per Schneier walk is my-optimizer-
# gaming not external attacker, so infra fail-open is safe. The pre-push
# gate at scripts/check_multi_party_review.py provides the second layer
# with stricter requirements (BOTH user AND external-AI CONFIRMS + hash
# binding + recency check).
#
# Spec per Knuth walk: EITHER user CONFIRMS OR external-AI CONFIRMS
# satisfies (softer than pre-push both-required). Missing review_stance
# field on legacy findings treated as CONFIRMS (matches existing shape
# in check_multi_party_review.py).
#
# Held constraints (Dekker/Beer follow-on notes): does not scan for
# reviews-that-happened-outside-the-round (System-4 gap). Smooth-confirm
# helper (queued follow-on) closes some of that friction.
# ---------------------------------------------------------------------------
SUBSTANCE_RESULT=$(python -c "
import sys
try:
    from divineos.core.watchmen.store import get_round, list_findings
except Exception:
    print('SKIP')  # infra unavailable, fail-open per Schneier walk
    sys.exit(0)
round_id = '$RESOLVED_ROUND_ID'
try:
    rnd = get_round(round_id)
except Exception:
    print('SKIP')
    sys.exit(0)
if rnd is None:
    print('NOROUND')  # per Holmes walk: eliminate impossible round-id upstream
    sys.exit(0)
try:
    findings = list_findings(round_id=round_id, limit=500)
except Exception:
    print('SKIP')
    sys.exit(0)
EXTERNAL_AI = {'grok', 'gemini'}
for f in findings:
    stance = getattr(f, 'review_stance', None)
    stance_val = getattr(stance, 'value', stance) if stance is not None else 'CONFIRMS'
    if str(stance_val).upper() != 'CONFIRMS':
        continue
    actor = (getattr(f, 'actor', '') or '').lower().strip()
    if not actor:
        continue
    if actor == 'user':
        print('OK_USER')
        sys.exit(0)
    if actor in EXTERNAL_AI or actor.startswith('claude-'):
        print(f'OK_AI:{actor}')
        sys.exit(0)
print('EMPTY')
" 2>/dev/null || echo "SKIP")

case "$SUBSTANCE_RESULT" in
    OK_*)
        # Substance validated. Commit proceeds.
        echo "prepare-commit-msg: substance-check passed on round ${RESOLVED_ROUND_ID} (${SUBSTANCE_RESULT})"
        exit 0
        ;;
    SKIP)
        # Infrastructure unavailable. Fail-open per Schneier walk.
        echo "prepare-commit-msg: substance-check skipped (infra unavailable), commit proceeds fail-open"
        exit 0
        ;;
    NOROUND)
        echo "" >&2
        echo "WARN: External-Review trailer references round '${RESOLVED_ROUND_ID}'" >&2
        echo "but that round does not exist in the audit_rounds table." >&2
        echo "Commit proceeds; fix the trailer before pushing to main. File a real round:" >&2
        echo "  divineos audit submit-round \"<focus>\" --actor <name> --source-ref \"<branch>\"" >&2
        exit 0
        ;;
    EMPTY|*)
        # The trailer references a real round but the round has no CONFIRMS
        # finding from any external actor. This is the fake-trailer shape.
        echo "" >&2
        echo "WARN: External-Review trailer references round '${RESOLVED_ROUND_ID}'" >&2
        echo "but that round contains no CONFIRMS findings from an external actor." >&2
        echo "The trailer is ceremony without substance." >&2
        echo "" >&2
        echo "Truth #15: mechanism-firing (trailer stamp) must not substitute for" >&2
        echo "the pointed-at work (real external review). The trailer requires an" >&2
        echo "actual CONFIRMS finding from user, grok, gemini, or claude-<variant>." >&2
        echo "" >&2
        echo "To satisfy: get real review, then file a CONFIRMS finding." >&2
        echo "" >&2
        echo "  divineos audit submit \"<one-line finding summary>\" \\" >&2
        echo "    --round ${RESOLVED_ROUND_ID} \\" >&2
        echo "    --actor user \\" >&2
        echo "    --stance CONFIRMS \\" >&2
        echo "    --severity LOW \\" >&2
        echo "    --category CODE \\" >&2
        echo "    --description \"<what was reviewed and confirmed>\"" >&2
        echo "" >&2
        echo "For external-AI review, use --actor grok/gemini/claude-<variant>." >&2
        echo "Commit proceeds; fix the trailer substance before merging to main." >&2
        exit 0
        ;;
esac
EOF

chmod +x "$HOOKS_DIR/prepare-commit-msg"
echo "Created prepare-commit-msg hook at $HOOKS_DIR/prepare-commit-msg"

# Install post-merge hook — delegates to .claude/hooks/post-merge-doc-fix.sh
# Closes the doc-leapfrog conflict pattern (PR #169, 2026-06-13): merge
# resolution silently drops architecture-tree entries, the next CI run
# fails on test_real_readme_passes, manual re-add is needed every rebase.
cat > "$HOOKS_DIR/post-merge" << 'EOF'
#!/bin/bash
# Post-merge hook — delegates to .claude/hooks/post-merge-doc-fix.sh
# which re-runs check_doc_counts --fix to recover entries dropped during
# merge conflict resolution. Fail-open: any error exits 0 silently.
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
if [ -z "$REPO_ROOT" ]; then
    exit 0
fi
if [ -x "$REPO_ROOT/.claude/hooks/post-merge-doc-fix.sh" ]; then
    bash "$REPO_ROOT/.claude/hooks/post-merge-doc-fix.sh" || true
fi
exit 0
EOF

chmod +x "$HOOKS_DIR/post-merge"
echo "Created post-merge hook at $HOOKS_DIR/post-merge"

echo ""
echo "Git hooks setup complete!"
echo ""
echo "The following checks will run before each commit:"
echo "  1. ruff format --check (formatting compliance)"
echo "  2. ruff check (linting)"
echo "  3. mypy (type checking)"
echo "  4. doc count drift (test/command counts vs reality)"
echo "  5. vulture dead-code (if installed)"
echo "  6. shellcheck on hooks (if installed)"
echo ""
echo "Additionally, commit-msg hook validates multi-party-review for"
echo "guardrail-file modifications (scripts/guardrail_files.txt)."
echo ""
echo "Pre-push hook blocks pushes from branches whose base is stale"
echo "relative to origin/main (silent-revert prevention, claim d3baec5a)."
echo "Bypass with: DIVINEOS_SKIP_FRESHNESS_CHECK=1 git push"
echo ""
echo "If any check fails, the commit will be blocked and you'll need to fix the issues."
