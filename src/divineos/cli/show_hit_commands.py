"""`divineos show <hit-id>` -- print the one saved row a memory-link hit points at. See core/show_hit.py for why."""

from __future__ import annotations

import click

from divineos.cli._helpers import _safe_echo


def register(cli: click.Group) -> None:
    @cli.command("show")
    @click.argument("hit_id")
    def show_cmd(hit_id: str) -> None:
        """Print the exact saved row for a hit id: correction-<position>-<timestamp>, knowledge-<id> or worklist-<id>.

        Opening a worklist-<id> row counts as reading it (the read count ticks, once per opening). The other two only look.
        """
        from divineos.core.show_hit import ShowHitError, show_hit

        try:
            _safe_echo(show_hit(hit_id))
        except ShowHitError as exc:
            click.secho(f"Refused: {exc}", fg="red", err=True)
            raise click.exceptions.Exit(1) from exc
