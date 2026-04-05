"""CLI commands for Body Awareness -- computational interoception."""

import click


def register(cli: click.Group) -> None:
    """Register body awareness commands."""

    @cli.command("body")
    @click.option("--prune", is_flag=True, help="Prune caches that exceed limits.")
    @click.option("--dry-run", is_flag=True, help="Show what would be pruned without deleting.")
    def body_cmd(prune: bool, dry_run: bool) -> None:
        """Check my substrate state -- storage, tables, health."""
        from divineos.core.body_awareness import format_vitals, prune_caches

        if prune or dry_run:
            actions = prune_caches(dry_run=dry_run)
            for action in actions:
                click.secho(action, fg="yellow" if dry_run else "green")
            if not dry_run:
                click.echo("")
                click.echo("Post-prune vitals:")
                click.echo(format_vitals())
        else:
            click.echo(format_vitals())

        from divineos.core.hud_handoff import mark_engaged

        mark_engaged()
