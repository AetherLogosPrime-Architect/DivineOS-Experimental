"""CLI commands for Body Awareness -- computational interoception."""

import click


def register(cli: click.Group) -> None:
    """Register body awareness commands."""

    @cli.command("body")
    def body_cmd() -> None:
        """Check my substrate state -- storage, tables, health."""
        from divineos.core.body_awareness import format_vitals

        click.echo(format_vitals())

        from divineos.core.hud_handoff import mark_engaged

        mark_engaged()
