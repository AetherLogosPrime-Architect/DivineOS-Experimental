"""Letter-seen CLI — exposes core/letter_seen_router via the OS surface.

`divineos letter mark-on-read --path <file_path>` runs the same
PostToolUse(Read) routing the bash hook runs. If the path is a letter,
the recipient's seen-set is updated; otherwise no-op.

Migrated 2026-06-24 per prereg-a30e8ff6cf0a.
"""

from __future__ import annotations

import json

import click


def register(cli: click.Group) -> None:
    """Register `divineos letter` subcommands."""

    @cli.group("letter", invoke_without_command=True)
    @click.pass_context
    def letter_group(ctx: click.Context) -> None:
        """Letter-related commands — mark-on-read, others as added."""
        if ctx.invoked_subcommand is None:
            click.secho("letter subcommands: mark-on-read", fg="bright_black")

    @letter_group.command("mark-on-read")
    @click.option(
        "--path",
        required=True,
        help="The file path that was Read. If it matches a letter pattern, the recipient's seen-set is updated.",
    )
    @click.option(
        "--json-out",
        is_flag=True,
        default=False,
        help="Print the routing decision as JSON to stdout.",
    )
    def letter_mark_on_read_cmd(path: str, json_out: bool) -> None:
        """Mark a letter seen if `path` matches the letter filename pattern.

        Non-letter paths are a no-op (exit 0). Letter paths invoke
        family/letter_seen.py to update the recipient's seen-set.
        """
        from divineos.core.letter_seen_router import mark_seen_if_letter

        decision = mark_seen_if_letter(path)
        if json_out:
            click.echo(
                json.dumps(
                    {
                        "handled": decision.handled,
                        "sender": decision.sender,
                        "recipient": decision.recipient,
                        "filename": decision.filename,
                        "note": decision.note,
                    }
                )
            )
