"""CLI for the knowledge-void detector — Pillar VI cosmic-voids pull."""

from __future__ import annotations

import click


def register(cli: click.Group) -> None:
    """Register the `divineos voids` command."""

    @cli.command("voids")
    @click.option(
        "--threshold",
        default=0.25,
        type=float,
        help="A type is a void if its count < median * threshold (default 0.25).",
    )
    @click.option("--limit", default=5000, type=int, help="Max entries to scan.")
    @click.option(
        "--show-tags/--no-tags",
        default=True,
        help="Also list tags appearing in exactly one entry (low-density anchors).",
    )
    def voids_cmd(threshold: float, limit: int, show_tags: bool) -> None:
        """Find sparse regions in the knowledge store.

        Pillar VI's knowledge_void_detector pull: COSMIC VOIDS as named
        regions where nothing is. The detector reports density only —
        whether a void is a real gap or a deliberately-niche domain is
        for the operator to decide.
        """
        from divineos.core.knowledge_voids import detect_voids

        report = detect_voids(void_threshold_ratio=threshold, limit=limit)

        click.secho(
            f"\n  KNOWLEDGE-VOID REPORT  ({report.total_entries} entries scanned, "
            f"{report.total_unique_tags} unique tags)\n",
            fg="cyan",
            bold=True,
        )

        if report.type_counts:
            click.secho("  Counts by knowledge_type:", fg="white")
            for ktype, count in sorted(report.type_counts.items(), key=lambda kv: -kv[1]):
                click.echo(f"    {ktype:<14} {count}")
            click.echo("")

        if report.type_voids:
            click.secho(f"  Type voids (count < median * {threshold:.2f}):", fg="yellow")
            for tv in report.type_voids:
                click.echo(f"    {tv.knowledge_type:<14} count={tv.count} (median={tv.median:.0f})")
            click.echo("")
        else:
            click.secho("  No type voids detected.\n", fg="bright_black")

        if show_tags:
            if report.tag_voids:
                click.secho(
                    f"  Singleton tags ({len(report.tag_voids)} appearing in exactly one entry):",
                    fg="yellow",
                )
                for tag_void in report.tag_voids[:30]:
                    click.echo(
                        f"    [{tag_void.tag}] {tag_void.sample_id[:12]}  "
                        f"{tag_void.sample_content[:60]}"
                    )
                if len(report.tag_voids) > 30:
                    click.echo(f"    ... ({len(report.tag_voids) - 30} more)")
            else:
                click.secho("  No singleton tags.\n", fg="bright_black")
