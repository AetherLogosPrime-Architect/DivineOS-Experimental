"""`divineos belt` -- the current task list, and closing an item off it.

The belt pulls by itself every prompt (``core/task_belt``); nothing here needs
running for it to work. ``belt done`` is the one command that matters: it
closes a current item through its drawer, archives it, and pulls the next.
"""

from __future__ import annotations

import click


def register(cli: click.Group) -> None:
    @cli.group("belt", invoke_without_command=True)
    @click.pass_context
    def belt_group(ctx: click.Context) -> None:
        """Show the current task list, pulled from the ranked pile."""
        if ctx.invoked_subcommand is not None:
            return
        from divineos.core.task_belt import open_count, pull, render

        current = pull()
        remaining = open_count() - len(current)
        click.echo(render(current, remaining) or "The belt is empty: every drawer is clear.")

    @belt_group.command("done")
    @click.argument("ref")
    @click.option(
        "--evidence",
        required=True,
        help="What closed it: a real commit or an existing file (and, for a correction, "
        "what the correction tracker asks for).",
    )
    def belt_done(ref: str, evidence: str) -> None:
        """Close a current item through its drawer, archive it, pull the next."""
        from divineos.core.task_belt import done, open_count, render

        try:
            closed, current = done(ref, evidence)
        except ValueError as exc:
            click.secho(f"[-] Not closed: {exc}", fg="red", err=True)
            raise SystemExit(2) from exc
        click.secho(
            f"[+] Closed and archived: {closed['key']} -- {closed['summary'][:100]}",
            fg="green",
        )
        click.echo(render(current, open_count() - len(current)))
