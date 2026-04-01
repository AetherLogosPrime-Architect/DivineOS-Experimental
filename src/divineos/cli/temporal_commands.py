"""CLI commands for temporal knowledge queries."""

import time

import click

from divineos.core.knowledge.temporal import (
    format_changes_summary,
    get_changes_since,
)


def register(cli: click.Group) -> None:
    """Register temporal commands."""
    cli.add_command(changes)


@click.command()
@click.option(
    "--hours",
    default=24.0,
    help="Show changes from the last N hours (default: 24).",
)
@click.option(
    "--days",
    default=0.0,
    help="Show changes from the last N days (overrides --hours).",
)
def changes(hours: float, days: float) -> None:
    """Show what changed in the knowledge store since a given time.

    Useful for session continuity: "what's different since I was last here?"
    """
    if days > 0:
        since = time.time() - (days * 86400)
        label = f"{days:.0f} day{'s' if days != 1 else ''}"
    else:
        since = time.time() - (hours * 3600)
        label = f"{hours:.0f} hour{'s' if hours != 1 else ''}"

    result = get_changes_since(since)

    total = sum(len(v) for v in result.values())
    if total == 0:
        click.echo(f"No knowledge changes in the last {label}.")
        return

    click.secho(f"=== Knowledge changes (last {label}) ===", fg="cyan", bold=True)
    click.echo(format_changes_summary(result))
