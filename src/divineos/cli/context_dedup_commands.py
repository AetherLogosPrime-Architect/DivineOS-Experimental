"""`divineos dedup-stats` — show token savings from the Warden-pattern dedup.

Andrew 2026-07-01: "keep track of the tokens saved and where so I can
see and understand the difference." This CLI reads the per-event log
context_dedup writes on each fire and shows a per-source + grand-total
summary of chars and estimated tokens saved.
"""

from __future__ import annotations

import json

import click


def register(cli: click.Group) -> None:
    """Register `divineos dedup-stats`."""

    @cli.command("dedup-stats")
    @click.option(
        "--json-out",
        is_flag=True,
        default=False,
        help="Emit the summary as JSON to stdout.",
    )
    def dedup_stats_cmd(json_out: bool) -> None:
        """Show context-dedup savings by source."""
        from divineos.core.context_dedup import savings_summary

        summary = savings_summary()
        if json_out:
            click.echo(json.dumps(summary))
            return

        total = summary["total"]
        per_source = summary["per_source"]

        if total["events"] == 0:
            click.echo("[dedup-stats] no dedup events recorded yet.")
            click.echo(
                "  Context-dedup fires when a wallpaper block emits identically "
                "within TTL (1 hour). The retrofit landed 2026-06-30 for the "
                "ACTIVE NEEDS block; next-session repeats will show up here."
            )
            return

        click.echo(
            f"context-dedup savings — {total['events']} events, "
            f"{total['saved_chars']:,} chars, "
            f"~{total['saved_tokens_est']:,} tokens saved"
        )
        click.echo("")
        click.echo("Per source (block):")
        # Sort by tokens saved, descending.
        rows = sorted(
            per_source.items(),
            key=lambda kv: kv[1]["saved_tokens_est"],
            reverse=True,
        )
        for src, entry in rows:
            click.echo(
                f"  {src:24s}  events={entry['events']:>4}  "
                f"chars={entry['saved_chars']:>8,}  "
                f"~tokens={entry['saved_tokens_est']:>7,}"
            )
