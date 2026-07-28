"""`divineos push-ready` — automate the guardrail-trailer + audit-round ceremony.

Detects guardrail-touching commits on the current branch missing an
``External-Review`` trailer, opens an audit round, amends the commits
with the trailer, files an aether self-CONFIRMS finding, and
force-pushes with ``--force-with-lease``.
"""

from __future__ import annotations

from pathlib import Path

import click


def register(cli: click.Group) -> None:
    @cli.command("push-ready")
    @click.option(
        "--branch",
        default=None,
        help="Branch to prepare (defaults to current).",
    )
    @click.option(
        "--dry-run",
        is_flag=True,
        default=False,
        help="Print the plan without modifying commit history or pushing.",
    )
    def push_ready_cmd(branch: str | None, dry_run: bool) -> None:
        """Automate the External-Review trailer + audit-round ceremony."""
        from divineos.core.push_ready import PushReadyError, run_push_ready

        repo = Path.cwd()
        try:
            result = run_push_ready(repo, branch=branch, dry_run=dry_run)
        except PushReadyError as exc:
            click.secho(f"[!] push-ready failed: {exc}", fg="red", err=True)
            raise click.exceptions.Exit(1) from exc

        click.secho(f"Branch: {result.branch}", fg="cyan")
        click.echo(f"Commits inspected: {len(result.commits)}")
        touching = [c for c in result.commits if c.touches_guardrail]
        click.echo(f"Guardrail-touching: {len(touching)}")
        click.echo(f"Needing trailer:    {len(result.needing_trailer)}")

        for c in result.needing_trailer:
            click.echo(f"  - {c.short_sha} {c.subject}")
            for f in c.guardrail_files:
                click.echo(f"      {f}")

        if not result.needing_trailer:
            click.secho(result.message, fg="green")
            return

        if result.dry_run:
            click.secho(result.message, fg="yellow")
            return

        if result.round_id:
            click.secho(f"Audit round: {result.round_id}", fg="cyan")
        if result.amended_shas:
            click.echo(f"Amended {len(result.amended_shas)} commit(s).")
        if result.confirms_finding_id:
            click.secho(
                f"Self-CONFIRMS finding: {result.confirms_finding_id}",
                fg="cyan",
            )
        else:
            click.secho(
                "[!] Self-CONFIRMS finding was not filed (non-fatal).",
                fg="yellow",
            )

        if result.pushed:
            click.secho(result.message, fg="green")
            click.echo("")
            click.secho("Still required for merge:", fg="cyan")
            click.echo("  - Aletheia CONFIRMS on the round")
            click.echo("  - Andrew APPROVE")
        else:
            click.secho(result.message, fg="red", err=True)
            raise click.exceptions.Exit(1)
