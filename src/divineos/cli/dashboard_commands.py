"""CLI for the check-engine dashboard."""

from __future__ import annotations

import click


def register(cli: click.Group) -> None:
    """Register dashboard commands on the CLI group."""

    @cli.command("dashboard")
    @click.option("--problems", is_flag=True, help="Only the lights that are not green.")
    def dashboard_cmd(problems: bool) -> None:
        """Check-engine lights — every registered system reports its own state."""
        from divineos.core.dashboard import PROBLEM, UNKNOWN, DashboardReading, read_all, render
        from divineos.core.dashboard_checks import install

        install()
        reading = read_all()
        if problems:
            reading = DashboardReading(
                results=[r for r in reading.results if r.state in (PROBLEM, UNKNOWN)]
            )
        click.echo(render(reading))
