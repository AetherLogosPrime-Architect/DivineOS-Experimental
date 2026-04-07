"""CLI commands for the progress dashboard.

`divineos progress` — show measurable proof the system works.
"""

import click


def register(cli: click.Group) -> None:
    """Register progress commands on the CLI group."""

    @cli.command("progress")
    @click.option("--days", default=30, type=int, help="Lookback period in days.")
    @click.option("--brief", is_flag=True, help="Show 3-line summary only.")
    @click.option("--export", is_flag=True, help="Output shareable markdown.")
    @click.option("--json", "as_json", is_flag=True, help="Output raw data as JSON.")
    def progress_cmd(days: int, brief: bool, export: bool, as_json: bool) -> None:
        """Show measurable progress metrics — real data, no vibes."""
        import dataclasses
        import json

        from divineos.core.progress_dashboard import (
            format_progress_brief,
            format_progress_export,
            format_progress_text,
            gather_progress,
        )

        report = gather_progress(lookback_days=days)

        if as_json:
            data = dataclasses.asdict(report)
            click.echo(json.dumps(data, indent=2))
        elif export:
            click.echo(format_progress_export(report))
        elif brief:
            click.echo(format_progress_brief(report))
        else:
            text = format_progress_text(report)
            try:
                click.echo(text)
            except UnicodeEncodeError:
                click.echo(text.encode("ascii", errors="replace").decode("ascii"))
