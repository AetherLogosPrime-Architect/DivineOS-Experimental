"""`divineos prs` — surface local branches without remote PRs.

Andrew 2026-06-09: tonight had 4 branches pushed but no PR opened
because I forgot to run ``gh pr create`` after each push. The gap was
invisible until Andrew pointed at the open-PR count and asked why my
recent branches weren't showing.

This command compares local branches against ``gh pr list`` and names
the branches that need a PR. Read-only by default; ``--open-missing``
runs ``gh pr create --fill`` for each gap.
"""

from __future__ import annotations

import json
import subprocess

import click


def _run(args: list[str], timeout: float = 10.0) -> tuple[int, str, str]:
    """Run a command, return (rc, stdout, stderr). No raise on failure."""
    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
        return proc.returncode, proc.stdout, proc.stderr
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, "", str(e)


def _local_branches_with_remote() -> list[str]:
    """Return local branches that have a corresponding origin/<branch>
    on the remote. A branch with no remote can't have a PR open against
    it from this side, so we filter early."""
    rc, out, _ = _run(["git", "for-each-ref", "--format=%(refname:short)", "refs/heads/"])
    if rc != 0:
        return []
    local = [line.strip() for line in out.splitlines() if line.strip()]
    rc, remote_out, _ = _run(
        ["git", "for-each-ref", "--format=%(refname:short)", "refs/remotes/origin/"]
    )
    if rc != 0:
        return local
    remote_set = {
        line.strip().removeprefix("origin/") for line in remote_out.splitlines() if line.strip()
    }
    return [b for b in local if b in remote_set and b != "main"]


def _open_pr_head_refs() -> set[str]:
    """Return the set of headRefName values for open PRs on the
    current repo. Empty set if gh is unavailable or returns nothing."""
    rc, out, _ = _run(
        ["gh", "pr", "list", "--state", "open", "--json", "headRefName", "--limit", "100"]
    )
    if rc != 0 or not out.strip():
        return set()
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return set()
    return {p.get("headRefName", "") for p in data if isinstance(p, dict)}


def find_branches_without_prs() -> list[str]:
    """Pure logic split out for testability: local branches with a
    remote counterpart that don't have an open PR."""
    branches = _local_branches_with_remote()
    if not branches:
        return []
    open_heads = _open_pr_head_refs()
    return sorted(b for b in branches if b not in open_heads)


def register(cli: click.Group) -> None:
    """Register the prs command."""

    @cli.command("prs")
    @click.option(
        "--open-missing",
        is_flag=True,
        help="Run `gh pr create --fill` for each branch missing a PR.",
    )
    def prs_cmd(open_missing: bool) -> None:
        """Find local branches without an open PR; optionally open them."""
        missing = find_branches_without_prs()
        if not missing:
            click.secho("[+] All local branches with a remote have an open PR.", fg="green")
            return

        click.secho(f"\n=== {len(missing)} branch(es) need a PR ===\n", fg="cyan", bold=True)
        for b in missing:
            click.secho(f"  {b}", fg="yellow")

        if not open_missing:
            click.secho(
                "\nRe-run with --open-missing to open them via "
                "`gh pr create --fill`, or open manually.",
                fg="bright_black",
            )
            return

        click.secho("\nOpening PRs via gh pr create --fill ...", fg="cyan")
        opened: list[tuple[str, str]] = []
        failed: list[tuple[str, str]] = []
        for branch in missing:
            rc, out, err = _run(
                ["gh", "pr", "create", "--fill", "--head", branch, "--base", "main"],
                timeout=30,
            )
            if rc == 0:
                opened.append((branch, out.strip()))
                click.secho(f"  [+] {branch} -> {out.strip()}", fg="green")
            else:
                failed.append((branch, (err or out).strip()))
                click.secho(f"  [!] {branch} failed: {(err or out).strip()[:120]}", fg="red")

        click.secho(
            f"\nDone: {len(opened)} opened, {len(failed)} failed.",
            fg="cyan",
            bold=True,
        )
