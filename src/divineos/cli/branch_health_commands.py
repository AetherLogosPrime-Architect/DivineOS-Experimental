"""CLI commands for branch_health — pre-push sanity check.

Surfaces stale-base and silent-deletion shapes before they become PRs.
Built 2026-05-09 in response to PR #343's 127-deletion shape (caused
by stale local main).

Usage::

    divineos check-branch                    # advisory
    divineos check-branch --strict           # exit 1 on warn or critical
    divineos check-branch --fetch            # git fetch first
    divineos check-branch --base origin/dev  # different base branch

Pre-push hook integration: a small ``.git/hooks/pre-push`` script can
call ``divineos check-branch --strict`` to block the push when the
findings cross thresholds. The OS does the work; the hook is a
reminder. (See setup/hooks/pre-push for the optional wrapper.)
"""

from __future__ import annotations

import sys

import click

from divineos.core.branch_health import (
    DEFAULT_DELETION_COUNT_THRESHOLD,
    DEFAULT_STALE_COMMITS_THRESHOLD,
    check_all,
    has_critical,
    has_warnings,
)


@click.command("check-branch")
@click.option(
    "--base",
    default="origin/main",
    show_default=True,
    help="Branch to compare against (e.g. origin/main, origin/dev).",
)
@click.option(
    "--fetch/--no-fetch",
    default=False,
    show_default=True,
    help="Run 'git fetch origin' first to refresh remote refs.",
)
@click.option(
    "--strict",
    is_flag=True,
    default=False,
    help="Exit with code 1 on warn or 2 on critical (for use in pre-push hooks).",
)
@click.option(
    "--stale-threshold",
    type=int,
    default=DEFAULT_STALE_COMMITS_THRESHOLD,
    show_default=True,
    help="Commits-behind threshold above which base_freshness is critical.",
)
@click.option(
    "--deletion-threshold",
    type=int,
    default=DEFAULT_DELETION_COUNT_THRESHOLD,
    show_default=True,
    help="Deletion count threshold above which deletion_shape warns.",
)
@click.option(
    "--cwd",
    default=None,
    help="Directory to measure. Pass this when the push originates in a worktree.",
)
def check_branch(
    base: str,
    fetch: bool,
    strict: bool,
    stale_threshold: int,
    deletion_threshold: int,
    cwd: str | None,
) -> None:
    """Check branch health before push: stale-base and silent-deletion shapes.

    ``--cwd`` exists because this check is fired by a PreToolUse(Bash) hook
    that relocates to the ambient repo root, while the push it polices may
    target a different worktree entirely.

    2026-08-15: it reported "25 file(s) would be deleted by merge" against a
    push whose own branch deleted nothing. It had measured HEAD of the main
    checkout — a branch that really does delete 25 retired hooks — instead of
    the worktree being pushed from, where the same command returns 0. Both
    numbers were correct about different trees, which is the worst kind of
    wrong: it reads as a real finding, and clearing it costs a kill-switch
    that disables the gate for every later push. That is precisely the
    habituation that trained the 71-bypasses-in-15-days pattern, so a gate
    that misfires this way does not merely annoy — it spends its own
    authority.

    ``check_all`` already threaded ``cwd`` to both checks. Only the CLI had
    no way to say which tree to look at.
    """
    findings = check_all(
        base=base,
        cwd=cwd,
        fetch=fetch,
        stale_threshold=stale_threshold,
        deletion_threshold=deletion_threshold,
    )

    for f in findings:
        if f.severity == "critical":
            click.secho(f"[!!] {f.name}: {f.message}", fg="red", err=True)
        elif f.severity == "warn":
            click.secho(f"[!] {f.name}: {f.message}", fg="yellow", err=True)
        else:
            click.secho(f"[ok] {f.name}: {f.message}", fg="green")

    if strict:
        if has_critical(findings):
            sys.exit(2)
        if has_warnings(findings):
            sys.exit(1)


def register(cli: click.Group) -> None:
    """Register the check-branch command on the CLI group."""
    cli.add_command(check_branch)
