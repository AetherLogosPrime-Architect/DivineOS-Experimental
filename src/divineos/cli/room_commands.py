"""`divineos room draft FILE` -- clear a circle's shape before it is posted.

Prints only the verdict, never the circle's words (so the tool call shows a path, and the circle is not printed a
second time on his screen). The judgement lives in core/room_draft.py; this is the thin door.
"""

from __future__ import annotations

import time
from pathlib import Path

import click

DRAFT_RECORD = Path.home() / ".divineos" / "room_draft.json"


def register(cli: click.Group) -> None:
    @cli.group("room")
    def room_group() -> None:
        """His room: the circle at the end of a reply."""

    @room_group.command("draft")
    @click.argument("file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
    def draft_cmd(file: Path) -> None:
        """Check a circle's shape and record it as cleared. Post it exactly as written."""
        from divineos.core.room_draft import record_draft

        text = file.read_text(encoding="utf-8")
        shape = record_draft(text, DRAFT_RECORD, now=time.time())
        if not shape.ok:
            raise click.ClickException(f"not cleared: {shape.problem}")
        # A real, ledger-visible use: a review that counts by this event cannot run on automated notices.
        from divineos.core.ledger import log_event
        from divineos.core.room_draft import fingerprint

        log_event(
            "ROOM_DRAFT_CLEARED", "aether", {"fingerprint": fingerprint(text)}, validate=False
        )
        click.echo(
            "cleared: post it as written (whitespace and quote marks may differ, words may not)"
        )
