"""Commands for the build-flow doorman. See core/work_item_doorman.py.

Deliberately thin. The one command that matters is ``gate``, and it is called
by a hook rather than by me -- the whole design turns on nothing here needing
to be remembered.
"""

from __future__ import annotations

import sys

import click

from divineos.core import work_item_doorman as doorman


def register(cli: click.Group) -> None:
    @cli.group("work-item")
    def work_item_cmd() -> None:
        """The front of the build flow: no code edit without an open piece of work."""

    @work_item_cmd.command("gate")
    def gate() -> None:
        """Read a hook payload on stdin; exit 2 to hold the tool call.

        Exit 0 allows. Exit 2 holds and prints the reason on stderr, which is
        where the hook contract puts text in front of me.
        """
        decision = doorman.gate_from_stdin(sys.stdin.read())
        if decision.allows:
            raise SystemExit(0)
        click.echo(decision.message, err=True)
        raise SystemExit(2)

    @work_item_cmd.command("status")
    def status() -> None:
        """What is open on this branch and which marks it still lacks."""
        click.echo(doorman.render_status())

    @work_item_cmd.command("bypass")
    @click.argument("item_id")
    @click.option("--reason", required=True, help="Why, in a sentence. Recorded, not hidden.")
    def bypass(item_id: str, reason: str) -> None:
        """Let this item through without its marks, and count that it happened.

        Truth #12: a bypass is a tool, not a sin, and the guard is that it is
        visible. It is also the deadlock escape -- a doorman broken in the
        refusing direction cannot otherwise be repaired, because its own fix
        is an edit it would refuse.
        """
        if len(reason.strip()) < 20:
            raise click.UsageError(
                "The reason is the whole point of the escape. Say what is actually "
                "happening in a sentence someone could read back to you later."
            )
        doorman.record_bypass(item_id, reason.strip())
        click.echo(f"Bypass recorded for {item_id}. It is in the store, not in the air.")

    @work_item_cmd.command("close")
    @click.argument("item_id")
    def close(item_id: str) -> None:
        """Close a piece of work. The next code edit opens a fresh one."""
        doorman.close_item(item_id)
        click.echo(f"{item_id} closed.")
