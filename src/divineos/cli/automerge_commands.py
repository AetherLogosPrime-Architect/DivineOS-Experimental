"""`divineos automerge` — auto-merge status surface for open PRs.

Closes a failure mode named during the 2026-06-11 PR-batch session: I kept
conflating "I armed auto-merge on this PR" with "the merge happened." When
auto-merge is ARMED but checks haven't passed, the PR sits BLOCKED — the
button was clicked, the action was queued, but nothing has landed yet. I
need to KNOW which queued PRs are progressing vs stalled without clicking
into each one in the UI.

This command lists every open PR with its mergeability state, auto-merge
arming status, and (when blocked) the first failing/pending check. No
network writes — read-only surface that pairs with `gh pr merge --auto`
to close the verification loop.

Usage:

  divineos automerge              # show all open PRs
  divineos automerge --armed      # only PRs with auto-merge armed
  divineos automerge --ready      # only PRs that could be clicked now
  divineos automerge --blocked    # only PRs that need attention

The output uses the same 5-column shape across modes so each line is
greppable / pipeable.
"""

from __future__ import annotations

import json
import subprocess
from typing import Any, cast

import click


def _gh_pr_list_with_states() -> list[dict[str, Any]]:
    """Pull open PRs with auto-merge + mergeability + check fields.

    gh CLI is the substrate-of-truth for PR state — no caching, no local
    DB, no inference. Returns [] on any failure (fail-soft: a surface
    that can't read its source must not lie about what it sees).
    """
    cmd = [
        "gh",
        "pr",
        "list",
        "--state",
        "open",
        "--json",
        "number,title,mergeable,mergeStateStatus,autoMergeRequest,headRefName,statusCheckRollup",
        "--limit",
        "100",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return []
    if proc.returncode != 0:
        return []
    try:
        return cast(list[dict[str, Any]], json.loads(proc.stdout))
    except (json.JSONDecodeError, ValueError):
        return []


def _first_problem_check(checks: list[dict] | None) -> str:
    """Return a short label for the first FAIL or PENDING check, or empty.

    Used in BLOCKED rows to surface WHY the PR isn't landing. We name the
    first problem only — full check list is one `gh pr checks <n>` away.
    """
    if not checks:
        return ""
    # Prefer reporting failures over pendings — those need action now.
    for c in checks:
        bucket = (c.get("conclusion") or "").upper()
        if bucket in {"FAILURE", "CANCELLED", "TIMED_OUT", "ACTION_REQUIRED"}:
            name = c.get("name") or c.get("workflowName") or "?"
            return f"FAIL: {name}"
    for c in checks:
        state = (c.get("status") or "").upper()
        if state in {"IN_PROGRESS", "PENDING", "QUEUED"}:
            name = c.get("name") or c.get("workflowName") or "?"
            return f"PENDING: {name}"
    return ""


def _classify(pr: dict) -> str:
    """One-word classification for the row: ARMED / READY / BLOCKED / DIRTY / UNKNOWN.

    ARMED   — auto-merge requested AND mergeStateStatus is BLOCKED (CI not green yet)
    READY   — mergeStateStatus is CLEAN and no auto-merge needed
    BLOCKED — no auto-merge AND mergeable but checks failing
    DIRTY   — mergeable=CONFLICTING (needs rebase/manual fix)
    UNKNOWN — gh hasn't computed mergeability yet (give it a sec, retry)
    """
    mergeable = pr.get("mergeable")
    mss = pr.get("mergeStateStatus")
    has_auto = bool(pr.get("autoMergeRequest"))
    if mergeable == "CONFLICTING" or mss == "DIRTY":
        return "DIRTY"
    if mergeable == "UNKNOWN" or mss == "UNKNOWN":
        return "UNKNOWN"
    if mss == "CLEAN":
        return "READY"
    if has_auto and mss in {"BLOCKED", "BEHIND"}:
        return "ARMED"
    return "BLOCKED"


def register(cli: click.Group) -> None:
    """Register the automerge command on the CLI group."""

    @cli.command("automerge")
    @click.option(
        "--armed",
        is_flag=True,
        help="Only show PRs that have auto-merge armed (queued behind CI).",
    )
    @click.option(
        "--ready",
        is_flag=True,
        help="Only show PRs that are CLEAN and could be merged right now.",
    )
    @click.option(
        "--blocked",
        is_flag=True,
        help="Only show PRs that need attention (CI failing or conflicting).",
    )
    def automerge_cmd(armed: bool, ready: bool, blocked: bool) -> None:
        """Show auto-merge state across open PRs.

        Pairs with `gh pr merge --auto` to close the verification loop —
        clicking auto-merge is not the same as the merge happening, and
        this command surfaces which queued PRs are progressing vs stalled.
        """
        prs = _gh_pr_list_with_states()
        if not prs:
            click.secho(
                "[-] gh pr list returned no PRs (or call failed). "
                "Check `gh auth status` if this seems wrong.",
                fg="yellow",
            )
            return

        rows: list[tuple[str, dict]] = [(_classify(pr), pr) for pr in prs]

        # Apply filters. Each flag narrows independently; passing all three
        # together shows just those three classes.
        filters_set = armed or ready or blocked
        if filters_set:
            wanted: set[str] = set()
            if armed:
                wanted.add("ARMED")
            if ready:
                wanted.add("READY")
            if blocked:
                wanted.update({"BLOCKED", "DIRTY", "UNKNOWN"})
            rows = [r for r in rows if r[0] in wanted]

        if not rows:
            click.secho("[~] no open PRs match the filter.", fg="bright_black")
            return

        # Sort by class then number so the output is stable across runs.
        class_order = {"READY": 0, "ARMED": 1, "BLOCKED": 2, "DIRTY": 3, "UNKNOWN": 4}
        rows.sort(key=lambda r: (class_order.get(r[0], 99), r[1].get("number", 0)))

        # Header
        click.secho(
            f"=== Auto-merge status — {len(rows)} open PR(s) ===",
            fg="cyan",
            bold=True,
        )
        click.echo("")

        # Color per class so the eye finds READY first.
        class_color = {
            "READY": "green",
            "ARMED": "cyan",
            "BLOCKED": "yellow",
            "DIRTY": "red",
            "UNKNOWN": "bright_black",
        }
        for cls, pr in rows:
            num = pr.get("number")
            title = (pr.get("title") or "")[:55]
            mss = pr.get("mergeStateStatus") or "?"
            mergeable = pr.get("mergeable") or "?"
            has_auto = bool(pr.get("autoMergeRequest"))
            auto_str = "auto-merge: ARMED" if has_auto else "auto-merge: -"
            problem = _first_problem_check(pr.get("statusCheckRollup"))
            problem_str = f"  ({problem})" if problem else ""
            color = class_color.get(cls, "white")
            click.secho(
                f"  [{cls:<7}] #{num:<4} {mergeable}/{mss:<10} {auto_str:<22} {title}{problem_str}",
                fg=color,
            )

        click.echo("")
        click.secho(
            "Legend: READY=click-merge-now  ARMED=queued+waiting-CI  "
            "BLOCKED=needs-attention  DIRTY=conflict  UNKNOWN=gh-still-computing",
            fg="bright_black",
        )
