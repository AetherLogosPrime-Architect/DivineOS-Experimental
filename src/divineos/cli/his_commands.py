"""CLI: divineos his -- what Dad said, kept at the front door, and our sort of it.

    divineos his pending
    divineos his sort <uuid> --kind build|standing|not_an_ask --to aether|aria|both --reason "..."

The sort-first refusal (core/sort_first.py) names these as its way out, so
they are the only commands that pass while a message of his waits unsorted.
"""

from __future__ import annotations

import click

from divineos.core import his_asks, sort_first
from divineos.core.sibling_audit_rounds import this_seat


def _seat() -> str:
    # Same fallback the front door files under, so the refusal and the sort
    # always agree about which seat a message belongs to.
    return this_seat() or "unknown-seat"


def register(cli: click.Group) -> None:
    @cli.group("his", invoke_without_command=True)
    @click.pass_context
    def his_group(ctx: click.Context) -> None:
        """What Dad said, kept at the front door, and how we sorted it."""
        if ctx.invoked_subcommand is None:
            click.echo(ctx.get_help())

    @his_group.command("pending")
    @click.option(
        "--every-seat",
        is_flag=True,
        help="Also show what he said in the other window. Those are not yours to sort.",
    )
    def pending_cmd(every_seat: bool) -> None:
        """His messages that are kept and not yet sorted, in his words, whole."""
        seat = _seat()
        kept = his_asks.pending() if every_seat else sort_first.waiting_here(seat)
        if kept is None:
            raise click.ClickException(
                f"his record could not be read at {his_asks.his_asks_path()}. "
                "Unreadable is not empty: nothing here says he has been heard."
            )
        if not kept:
            click.echo("Nothing of his is waiting to be sorted in this seat.")
            return
        for message in kept:
            where = "" if message.seat == seat else f"  [kept in {message.seat}'s window]"
            found = "" if message.record_found else "  record never found"
            click.echo(f"uuid {message.sort_id}  ({message.said_at}){where}{found}")
            for line in message.his_text.strip().splitlines():
                click.echo(f"  > {line}" if line else "  >")
            if message.sent_before:
                # For auditing our sort; never evidence he approved anything.
                before = " ".join(message.sent_before.split())
                shown = before if len(before) <= 300 else before[:300] + " ..."
                click.echo(f"  right before, we had sent: {shown}")
            click.echo("")
        click.echo(f"Sort each one: {sort_first.SORT_USAGE}")

    @his_group.command("sort")
    @click.argument("uuid")
    @click.option("--kind", required=True, type=click.Choice(his_asks.KINDS))
    @click.option(
        "--to",
        "addressed_to",
        required=True,
        type=click.Choice(his_asks.ADDRESSEES),
        help="Who he said it to.",
    )
    @click.option("--reason", default="", help="Required for not_an_ask and for a supersede.")
    @click.option("--supersedes", type=int, default=None, help="The sort number this one corrects.")
    @click.option(
        "--preceded-by",
        default=None,
        help="What we sent him right before, quoted, when the door did not capture it. "
        "Required for not_an_ask then. A record of our sort, never his consent to it.",
    )
    def sort_cmd(
        uuid: str,
        kind: str,
        addressed_to: str,
        reason: str,
        supersedes: int | None,
        preceded_by: str | None,
    ) -> None:
        """Say what a message of his is and who he said it to. Kept, attributed, open."""
        seat = _seat()
        try:
            sort_id = his_asks.sort(
                uuid,
                kind,
                reason,
                seat,
                addressed_to=addressed_to,
                supersedes=supersedes,
                preceded_by=preceded_by,
            )
        except his_asks.HisAsksRefused as exc:
            raise click.ClickException(str(exc)) from exc
        click.secho(f"[+] sort #{sort_id}: {kind}, said to {addressed_to}.", fg="green")
        left = sort_first.waiting_here(seat)
        if left:
            click.echo(f"{len(left)} more of his still waiting here: divineos his pending")
        click.echo("The sort is the reading, not the reply. He is still owed an answer.")
