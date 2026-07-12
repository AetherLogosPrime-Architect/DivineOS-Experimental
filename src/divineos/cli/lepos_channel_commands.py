"""CLI surface for the post-send lepos reflection channel.

The Stop hook calls ``divineos lepos-channel reflect`` after each
substantive assistant reply. Reflection runs the surface-signal lenses
against the reply text (vs Andrew's last message) and writes a pending-
surface file. On the next turn's UserPromptSubmit, ``divineos lepos-
channel surface`` reads and consumes it, injecting a short reflection
block at compose-start.

See ``src/divineos/core/lepos_channel_reflect.py`` for the design notes.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from divineos.core import lepos_channel_reflect


def _read_text_arg(inline: str | None, path: str | None) -> str:
    if inline is not None:
        return inline
    if path:
        try:
            return Path(path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""
    return sys.stdin.read()


def register(cli: click.Group) -> None:
    @cli.group("lepos-channel", invoke_without_command=True)
    @click.pass_context
    def lepos_channel_group(ctx: click.Context) -> None:
        """Post-send lepos reflection channel — Stop-hook driver + surface reader."""
        if ctx.invoked_subcommand is None:
            click.echo(lepos_channel_reflect.pending_surface_path())

    @lepos_channel_group.command("reflect")
    @click.option(
        "--reply",
        default=None,
        help="Assistant reply text inline. If omitted, use --reply-file.",
    )
    @click.option(
        "--reply-file",
        default=None,
        help="Path to file containing the assistant reply text.",
    )
    @click.option(
        "--andrew",
        default=None,
        help="Andrew's last message inline. If omitted, use --andrew-file.",
    )
    @click.option(
        "--andrew-file",
        default=None,
        help="Path to file containing Andrew's last message.",
    )
    @click.option(
        "--quiet",
        is_flag=True,
        default=False,
        help="Suppress stdout (Stop hooks should be silent).",
    )
    @click.option(
        "--tool-calls",
        default=None,
        help="Comma-separated tool-call names the turn ran (e.g. "
        "'Bash,Edit,Write'). Enables the task-presence axis: "
        "when real tools ran AND the reply cites Andrew's exact span, "
        "the reflection is presence-valid even without felt-interior. "
        "Aletheia audit 2026-07-11 finding #6.",
    )
    def lepos_channel_reflect_cmd(
        reply: str | None,
        reply_file: str | None,
        andrew: str | None,
        andrew_file: str | None,
        quiet: bool,
        tool_calls: str | None,
    ) -> None:
        """Reflect on the last assistant reply and stage the surface.

        Reads reply text and Andrew's last message, runs the three
        surface-signal lenses (heard / interior / verified-substrate-
        engagement), writes the pending-surface file for the next
        UserPromptSubmit to consume.
        """
        reply_text = _read_text_arg(reply, reply_file)
        andrew_text = _read_text_arg(andrew, andrew_file)
        if not reply_text.strip():
            # No reply to reflect on. Stay silent.
            return
        tool_call_tuple: tuple[str, ...] = ()
        if tool_calls:
            tool_call_tuple = tuple(name.strip() for name in tool_calls.split(",") if name.strip())
        r = lepos_channel_reflect.reflect(
            reply_text,
            andrew_text,
            tool_calls_in_turn=tool_call_tuple or None,
        )
        lepos_channel_reflect.write_pending(r)
        if not quiet:
            click.echo(r.markdown())

    @lepos_channel_group.command("surface")
    def lepos_channel_surface_cmd() -> None:
        """Emit the pending reflection (if any) and consume it.

        Called by the UserPromptSubmit hook at compose-start. Silent
        when nothing is pending — no wallpaper.
        """
        out = lepos_channel_reflect.render_pending_or_empty()
        if out:
            click.echo(out)

    @lepos_channel_group.command("show")
    def lepos_channel_show_cmd() -> None:
        """Show the pending reflection WITHOUT consuming it (debug)."""
        path = lepos_channel_reflect.pending_surface_path()
        if not path.exists():
            click.echo("(no pending reflection)")
            return
        click.echo(path.read_text(encoding="utf-8"))
