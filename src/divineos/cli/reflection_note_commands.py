"""File a reflection in my own place, so Andrew's reply stays only the plain part.

The reflection hold (core/reflection_room.py) counts a filed note the same as a
## REFLECTION appended to the reply. Andrew 2026-10-08: "this is hard to
follow son" -- the technical block was landing where he reads last.
"""

from __future__ import annotations

import click

from divineos.core import reflection_room


def register(cli: click.Group) -> None:
    @cli.command("reflection-note")
    @click.argument("text")
    def reflection_note(text: str) -> None:
        """File a reflection for the reflection hold (name each stumble, then fixed by structure: / owed:).

        [tool] This files the text; whether the thinking in it is good stays mine.
        """
        reflection_room.file_note(text)
        click.echo("[+] Reflection filed in your own place. The reply can stay plain.")
