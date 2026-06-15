#!/bin/bash
# PreToolUse hook — block `gh pr create` on guardrail-touching branches
# unless the PR is opened as a draft.
#
# Root cause (Andrew 2026-06-13): PRs #190, #191, #192 modified guardrail
# files and were opened as ready-for-review, so the multi-party-review
# CI fired immediately and marked them red on the public activity feed
# before Aletheia had a chance to audit. The integrity-audit workflow
# already has the right design — it skips draft PRs — but I was not
# opening these as drafts. The OS lets me open ready when I should be
# opening draft.
#
# This gate enforces: if the branch contains any commit that modifies
# a guardrail file, `gh pr create` must include --draft. Aletheia can
# still see and audit the draft from origin (drafts are visible); after
# audit and trailer-amend, `gh pr ready <n>` promotes it and fires CI
# once with the trailer already present.
#
# Fail-open: any error exits 0.

INPUT=$(cat)

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

DIVINEOS_HOOK_INPUT="$INPUT" "$PYTHON_BIN" - <<'PYEOF'
import json
import os
import re
import subprocess
import sys


def _read_input():
    try:
        return json.loads(os.environ.get("DIVINEOS_HOOK_INPUT", "{}") or "{}")
    except Exception:
        return {}


def _is_gh_pr_create(cmd: str) -> bool:
    # Match `gh pr create` anywhere in a pipeline / chained command,
    # but only as a discrete subcommand sequence (not e.g. `gh pr create-comment`).
    return bool(re.search(r"\bgh\s+pr\s+create\b", cmd))


def _has_draft_flag(cmd: str) -> bool:
    # --draft / -d as a standalone flag (not embedded in another word).
    return bool(re.search(r"(^|\s)(--draft|-d)(\s|$)", cmd))


def _branch_files_changed() -> list[str]:
    """Return files touched by commits on current branch ahead of main.

    Falls back to empty list on any error — fail-open: we'd rather let
    a legitimate PR through than block on git errors.
    """
    try:
        proc = subprocess.run(
            ["git", "diff", "--name-only", "origin/main...HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except Exception:
        return []
    if proc.returncode != 0:
        return []
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def _load_guardrail_set() -> set[str]:
    path = "scripts/guardrail_files.txt"
    try:
        with open(path, encoding="utf-8") as f:
            return {
                line.strip()
                for line in f
                if line.strip() and not line.strip().startswith("#")
            }
    except OSError:
        return set()


def main() -> int:
    data = _read_input()
    if (data.get("tool_name") or "") != "Bash":
        return 0
    cmd = ((data.get("tool_input") or {}).get("command") or "").strip()
    if not cmd or not _is_gh_pr_create(cmd):
        return 0
    if _has_draft_flag(cmd):
        return 0

    changed = _branch_files_changed()
    if not changed:
        return 0
    guardrail = _load_guardrail_set()
    if not guardrail:
        return 0
    touched = sorted(set(changed) & guardrail)
    if not touched:
        return 0

    # Block — guardrail-touching branch opening a non-draft PR.
    msg = (
        "BLOCKED: this branch modifies guardrail file(s) and would open a "
        "ready-for-review PR. The integrity-audit workflow skips drafts but "
        "fires on ready PRs — opening ready means a red multi-party-review "
        "badge on the public activity feed before audit.\n"
        f"  Guardrail files touched: {', '.join(touched[:5])}"
        f"{' ...' if len(touched) > 5 else ''}\n\n"
        "Fix: open as draft, let Aletheia audit from origin, amend the "
        "External-Review trailer after the round files, then promote with "
        "`gh pr ready <n>`. The CI fires once with the trailer present.\n\n"
        "Add --draft to the gh pr create command and retry."
    )
    print(msg, file=sys.stderr)
    return 1


sys.exit(main())
PYEOF
RC=$?
exit $RC
