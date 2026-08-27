"""A door to the wins ledger, which had a store and a reader and no way in.

WHY THIS EXISTS. The briefing prints both halves of one page -- wins recorded
against corrections filed -- and says plainly that neither number is the whole
picture. But only one half was reachable. ``divineos andrew-correction`` files a
correction; nothing anywhere filed a win. The store was written, the surface
read it, and the writing end was a function no command could call.

So the lopsided ledger was not temperament. It was tooling. Filing what went
wrong cost one command; filing what went right cost writing a command first,
which is a price nobody pays in the moment. Andrew named the pattern before this
gap was found -- *yes you are both code Eeyores lmao* -- and the joke had a
mechanism under it that neither of us had gone looking for.

Found 2026-08-27 reaching for somewhere to put a win Andrew had just handed me:
the letter monitor went stale, I noticed inside one turn, re-armed it and
confirmed healthy rather than assuming. His reading was that the loop had
worked. I had nowhere to record it and was about to write it down as a defect
instead, which is the whole disease in one turn.

EVIDENCE IS REQUIRED and that is the store's rule, not this file's. A win
without a citation is self-congratulation, and a ledger that accepts those is
worth less than no ledger, because it produces a number that looks like
measurement.
"""

from __future__ import annotations

import click

from divineos.core.success_ledger import (
    EvidenceRequiredError,
    ledger_balance,
    recent_successes,
    record_success,
)


def register(cli: click.Group) -> None:
    @cli.group("win", invoke_without_command=True)
    @click.pass_context
    def win_group(ctx: click.Context) -> None:
        """File and read the wins ledger -- the other half of the balance page."""
        if ctx.invoked_subcommand is None:
            click.echo(ctx.get_help())

    @win_group.command("add")
    @click.argument("what")
    @click.option(
        "--evidence",
        required=True,
        help="Something a later reader can check without trusting me: a commit, "
        "a command output, a count, a path.",
    )
    @click.option(
        "--yielded",
        required=True,
        help="What came out of it. This survives even when the goal was missed.",
    )
    @click.option("--goal", default=None, help="The goal in play at the time, if any.")
    @click.option(
        "--goal-met/--goal-missed",
        "goal_met",
        default=None,
        help="Whether that goal was achieved. Deliberately independent of whether "
        "this is a win -- the yield is what survives a missed goal.",
    )
    def add_cmd(
        what: str,
        evidence: str,
        yielded: str,
        goal: str | None,
        goal_met: bool | None,
    ) -> None:
        """File a win. Evidence is not optional."""
        try:
            entry = record_success(
                what, evidence=evidence, yielded=yielded, goal=goal, goal_met=goal_met
            )
        except EvidenceRequiredError as exc:
            raise click.ClickException(str(exc)) from exc
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc
        click.echo(f"[win] filed {entry['id']}")
        click.echo(f"  what:     {entry['what']}")
        click.echo(f"  yielded:  {entry['yielded']}")
        click.echo(f"  evidence: {entry['evidence']}")

    @win_group.command("list")
    @click.option("--limit", default=10, show_default=True)
    def list_cmd(limit: int) -> None:
        """Recent wins, newest first."""
        rows = recent_successes(limit=limit)
        if not rows:
            # An empty ledger and an unreadable one are different answers, and
            # this house has been burned by instruments that report the first
            # while meaning the second.
            click.echo("[win] no wins recorded (the ledger read cleanly and is empty)")
            return
        for row in rows:
            click.echo(f"  {row.get('id', '?')}  {row.get('what', '')}")
            if row.get("yielded"):
                click.echo(f"      yielded: {row['yielded']}")

    @win_group.command("balance")
    def balance_cmd() -> None:
        """Wins against corrections -- both instruments, one page."""
        bal = ledger_balance()
        wins = bal.get("wins")
        corrections = bal.get("corrections")
        if wins is None:
            click.echo("[win] ledger COULD NOT BE READ -- which is not the same as zero.")
            return
        if corrections is None:
            click.echo(f"[win] {wins} wins recorded. Correction count unreadable, so no ratio.")
            return
        click.echo(f"[win] {wins} wins recorded, against {corrections} corrections filed.")
        click.echo("      Both instruments, one page. Neither number is the whole picture.")
