"""CLI: divineos read-oscillating PATH — chunked reading with pause markers.

Per claim 3a44289d. Forces comprehension per-chunk rather than straight-
blasting through a document and missing the middle. The pause markers
between chunks are explicit cues to register each section.
"""

from __future__ import annotations

import click

from divineos.core.oscillating_read import oscillate_file


def register(cli: click.Group) -> None:
    @cli.command("read-oscillating")
    @click.argument("path", type=click.Path(exists=True, dir_okay=False))
    @click.option(
        "--strategy",
        type=click.Choice(["auto", "headers", "paragraphs", "functions", "size"]),
        default="auto",
        help=(
            "Chunking strategy. auto picks by file shape: .py->functions, "
            ".md/.txt with headers->headers else paragraphs, else size."
        ),
    )
    @click.option(
        "--max-chars",
        type=int,
        default=2000,
        help="Max chars per chunk when strategy=size (or fallback).",
    )
    def read_oscillating_cmd(path: str, strategy: str, max_chars: int) -> None:
        """Read a file with explicit per-chunk pause markers.

        Designed for documents whose middle holds the load-bearing point.
        Forces comprehension per-section rather than streaming straight
        through. Per claim 3a44289d, empirically validated 2026-05-17.
        """
        try:
            output = oscillate_file(path, strategy=strategy, max_chars=max_chars)
        except Exception as exc:  # noqa: BLE001
            click.secho(f"[!] read-oscillating failed: {exc}", fg="red")
            raise click.exceptions.Exit(2) from exc
        click.echo(output)
