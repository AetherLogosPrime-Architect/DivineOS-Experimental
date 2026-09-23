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
    @click.option(
        "--his-words",
        default="",
        help=(
            "Required when the reason leans on Andrew: his words, verbatim, from his "
            "latest message. Checked against the transcript, not taken on trust."
        ),
    )
    def bypass(item_id: str, reason: str, his_words: str) -> None:
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
        from divineos.core import his_words as hw

        verified = ""
        if hw.invokes_him(reason) or his_words.strip():
            # His name is not a key (core/his_words.py). Four bypasses in one
            # session said "Andrew is here" and he had said yes to none of them.
            if not his_words.strip():
                click.echo(hw.refusal(reason.strip(), None), err=True)
                raise SystemExit(2)
            verdict = hw.check_quote(his_words)
            if not verdict.ok:
                click.echo(hw.refusal(reason.strip(), verdict), err=True)
                raise SystemExit(2)
            verified = his_words.strip()
        doorman.record_bypass(item_id, reason.strip(), his_words=verified)
        click.echo(f"Bypass recorded for {item_id}. It is in the store, not in the air.")
        if verified:
            click.echo("  His words, checked against his own message, are stored beside it.")

    @work_item_cmd.command("close")
    @click.argument("item_id")
    def close(item_id: str) -> None:
        """Close a piece of work. The next code edit opens a fresh one."""
        doorman.close_item(item_id)
        click.echo(f"{item_id} closed.")
