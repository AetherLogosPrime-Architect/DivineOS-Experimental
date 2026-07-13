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
def check_branch(
    base: str,
    fetch: bool,
    strict: bool,
    stale_threshold: int,
    deletion_threshold: int,
) -> None:
    """Check branch health before push: stale-base and silent-deletion shapes."""
    findings = check_all(
        base=base,
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
