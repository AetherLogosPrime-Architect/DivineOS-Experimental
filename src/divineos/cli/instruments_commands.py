"""CLI for the instruments index — what I can measure about myself."""

import click


def register(cli: click.Group) -> None:
    """Register the instruments command."""

    @cli.command("instruments")
    @click.option(
        "--quiet-only",
        is_flag=True,
        help="Show only instruments that are not answering.",
    )
    def instruments_cmd(quiet_only: bool) -> None:
        """Survey my diagnostic surfaces -- which answer, which have gone silent.

        Every call OPENS each surface rather than describing it, so a log that
        vanished reports MISSING instead of sitting stale in a doc. An
        instrument recording nothing reports EMPTY or SILENT, never healthy:
        in this house the never-firing check has twice been the broken one.
        """
        from divineos.core.instruments import format_survey, survey

        readings = survey()

        if quiet_only:
            readings = [r for r in readings if r.status in ("EMPTY", "SILENT")]
            if not readings:
                click.secho("All instruments answering.", fg="green")
                return

        click.echo(format_survey(readings))
