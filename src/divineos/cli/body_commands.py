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

    @cli.command("maintenance")
    @click.option("--dry-run", is_flag=True, help="Show what would be done without doing it.")
    def maintenance_cmd(dry_run: bool) -> None:
        """Run substrate maintenance — VACUUM, log cleanup, cache prune."""
        from divineos.core.body_awareness import run_maintenance

        verb = "Would" if dry_run else "Running"
        click.secho(f"{verb} maintenance...", fg="cyan")
        click.echo("")

        results = run_maintenance(dry_run=dry_run)

        # VACUUM
        vac = results["vacuum"]
        if vac["freed_mb"] > 0:
            click.secho(
                f"  VACUUM: {vac['before_mb']:.1f}MB -> {vac['after_mb']:.1f}MB "
                f"(freed {vac['freed_mb']:.1f}MB, was {vac['free_ratio']:.0%} free pages)",
                fg="green",
            )
        else:
            click.echo(
                f"  VACUUM: {vac['before_mb']:.1f}MB, {vac['free_ratio']:.0%} free pages "
                f"-- within threshold, skipped"
            )

        # Logs
        logs = results["logs"]
        if logs["removed_count"] > 0:
            action = "Would remove" if dry_run else "Removed"
            click.secho(
                f"  Logs: {action} {logs['removed_count']} old log files "
                f"({logs['freed_mb']:.1f}MB)",
                fg="green",
            )
        else:
            click.echo("  Logs: within retention limit")

        # Caches
        for action in results["caches"]["actions"]:
            click.echo(f"  {action}")

        if not dry_run:
            click.echo("")
            from divineos.core.body_awareness import format_vitals

            click.echo(format_vitals())

        from divineos.core.hud_handoff import mark_engaged

        mark_engaged()
