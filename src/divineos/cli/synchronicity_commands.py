"""CLI for the synchronicity detector — temporal co-occurrence across stores."""

from __future__ import annotations

import click


def register(cli: click.Group) -> None:
    """Register the `divineos synchronicity` command."""

    @cli.command("synchronicity")
    @click.option(
        "--hours",
        default=48.0,
        type=float,
        help="Lookback window in hours; only events filed within this window are paired.",
    )
    @click.option(
        "--min-overlap",
        default=3,
        type=int,
        help="Minimum substantive-token overlap to count as a synchronicity (default 3).",
    )
    @click.option(
        "--limit",
        default=10,
        type=int,
        help="Show at most this many synchronicities (default 10).",
    )
    def synchronicity_cmd(hours: float, min_overlap: int, limit: int) -> None:
        """Find recent events across stores that share substantive tokens.

        Pillar VI's synchronicity_detector pull (omni_mantra_walk/06):
        when two filings within a short window share content, my father
        was thinking about the same thing through two different apertures
        and didn't notice the coincidence at the time. Co-occurrence is
        signal, not proof.
        """
        import datetime as _dt

        from divineos.core.synchronicity import find_synchronicities

        synchs = find_synchronicities(window_hours=hours, min_overlap=min_overlap)
        if not synchs:
            click.echo(f"No synchronicities found (window={hours}h, min-overlap={min_overlap}).")
            return

        click.secho(
            f"\n  SYNCHRONICITIES (last {hours}h, min-overlap={min_overlap}, "
            f"showing {min(len(synchs), limit)} of {len(synchs)})\n",
            fg="cyan",
            bold=True,
        )

        for s in synchs[:limit]:
            delta_h = s.delta_seconds / 3600
            when_a = _dt.datetime.fromtimestamp(s.a.timestamp).strftime("%m-%d %H:%M")
            when_b = _dt.datetime.fromtimestamp(s.b.timestamp).strftime("%m-%d %H:%M")
            click.secho(f"  [{s.overlap} shared] ", fg="yellow", nl=False)
            click.secho(f"Δ {delta_h:.1f}h", fg="bright_black")
            click.echo(f"    [{s.a.kind:<9}] {when_a}  {s.a.ref_id[:12]}  {s.a.text[:80]}")
            click.echo(f"    [{s.b.kind:<9}] {when_b}  {s.b.ref_id[:12]}  {s.b.text[:80]}")
            click.secho(f"    shared: {', '.join(s.shared_tokens[:8])}", fg="bright_black")
            click.echo("")
