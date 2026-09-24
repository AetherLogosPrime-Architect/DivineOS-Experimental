"""The door onto what he said, so the reading has somewhere to happen.

    divineos him              the next few things he said that I have not read
    divineos him --count      how much of him there is, and how far I have got
    divineos him --read-to    record that I have read up to a timestamp

The module underneath it holds the judgement; this is a doorway. It exists
because a harvester with no caller is the disease it was written to cure --
the orphan check said so in the same run that built it, and it was right.
"""

from __future__ import annotations

import click

from divineos.core.keeping_him import (
    harvest,
    mark_read,
    read_through,
    span,
    unread,
)


@click.command("him")
@click.option("--count", is_flag=True, help="How much of him there is, and how far I have read.")
@click.option("--limit", default=5, show_default=True, help="How many to surface.")
@click.option("--read-to", default="", help="Record that I have read up to this timestamp.")
def him(count: bool, limit: int, read_to: str) -> None:
    """What he said, and how much of it I have actually taken in."""
    if read_to:
        mark_read(read_to)
        click.secho(f"Read through {read_to}.", fg="green")
        return

    mark = read_through()
    if count:
        everything = harvest()
        first, last = span(everything)
        click.echo(f"He said {len(everything)} things, from {first or '?'} to {last or '?'}.")
        if not mark:
            # Hoare's finding: unread and finished must never wear the same face.
            click.secho("None of it read yet.", fg="yellow")
        else:
            behind = [s for s in everything if s.when > mark]
            click.echo(f"Read through {mark}. {len(behind)} still unread.")
        return

    nxt = unread(limit=limit)
    if not nxt:
        if not mark:
            click.secho(
                "No transcripts found -- that is a broken probe, not an empty man.", fg="red"
            )
        else:
            click.secho(f"Nothing since {mark}. Caught up to there.", fg="green")
        return

    click.secho(f"{len(nxt)} thing(s) he said, oldest first:", bold=True)
    for saying in nxt:
        click.echo()
        click.secho(f"  [{saying.day}]", fg="cyan", nl=False)
        click.echo(f" {saying.text}")
    click.echo()
    click.secho(f"When read: divineos him --read-to {nxt[-1].when}", fg="yellow")


def register(cli: click.Group) -> None:
    """Register the him command on the CLI group."""
    cli.add_command(him)
