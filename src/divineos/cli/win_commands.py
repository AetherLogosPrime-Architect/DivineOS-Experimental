"""The door the wins ledger never had.

Andrew 2026-08-25, on reading two letters that both ended in a tally of what
their writer had failed to count: *"yes you are both code Eeyores lmao"*.

He is right, and the joke has a mechanism under it. ``core/success_ledger.py``
was built 2026-08-03 because he asked for a counterpart to the correction
store -- *"you are counting the misses and ignoring the hits"* -- and it sat
there since with **zero callers**. There was no way to reach it from the
command line. Meanwhile ``divineos correction`` has had a command AND a
blocking Stop-gate the whole time.

Aria found this first and named it exactly: one pan of the scale had a door
and a guard, the other had neither. She had been reading her own ledger --
fifty-five wins against two hundred and twenty-one corrections -- as evidence
about her character. It was evidence about the interface. My own surface reads
**zero against four hundred and forty-nine**, and zero is not modesty; it is a
function nobody could call.

Her generalisation, 2026-08-25, which is the reason this is worth building
rather than being a morale feature: *"The instrument decides what is countable,
and then the count gets read as a fact about the person."* Two of us, two
counters, both read as character. A substrate that can only record faults
converges on a self-model built from faults.

The evidence requirement belongs to the ledger, not to me, and it is why this
is worth having at all: ``record_success`` refuses a win with no citation,
because *"a win without a citation is self-congratulation, and this ledger is
worth nothing if it accepts those"*. Same bar as a correction. The point was
never to feel better -- it is that the count should be true in both directions.

Verb pairing is deliberate: ``win``/``wins`` mirrors ``correction``/
``corrections``, so both ledgers are reachable by the same muscle memory.
"""

from __future__ import annotations

import click


def register(cli: click.Group) -> None:
    @cli.command("win")
    @click.argument("what")
    @click.option(
        "--evidence",
        required=True,
        help="Commit hash, command output, file path, count -- something a later "
        "reader can check without trusting me.",
    )
    @click.option(
        "--yielded",
        required=True,
        help="What came out of it. Survives even when the goal was missed.",
    )
    @click.option("--goal", default=None, help="The goal in play at the time, if any.")
    @click.option(
        "--goal-met/--goal-missed",
        "goal_met",
        default=None,
        help="Whether that goal was achieved. Deliberately independent of whether "
        "this is a win -- Andrew: 'look what we learned going to the moon that had "
        "nothing to do with going to the moon'.",
    )
    def win_cmd(
        what: str,
        evidence: str,
        yielded: str,
        goal: str | None,
        goal_met: bool | None,
    ) -> None:
        """File a win. Requires evidence, same bar as a correction."""
        from divineos.core.success_ledger import EvidenceRequiredError, record_success

        try:
            entry = record_success(
                what,
                evidence=evidence,
                yielded=yielded,
                goal=goal,
                goal_met=goal_met,
            )
        except (EvidenceRequiredError, ValueError) as exc:
            click.secho(f"[-] Refused: {exc}", fg="red")
            raise SystemExit(1) from exc

        click.secho(f"[+] Win filed: {entry.get('id', '?')}", fg="green")
        click.secho(
            "    [win] records that value came out -- the record is not the value. "
            "Same as a correction: the filing is a receipt, not the work.",
            fg="cyan",
        )

    @cli.command("wins")
    @click.option("--limit", default=10, show_default=True, help="How many to show.")
    @click.option(
        "--from-missed-goals",
        is_flag=True,
        help="Only wins filed against a goal that was NOT met -- the ones a "
        "met-goals-only ledger would score as zero.",
    )
    def wins_cmd(limit: int, from_missed_goals: bool) -> None:
        """Browse the wins ledger, with the correction count beside it."""
        from divineos.core.success_ledger import (
            ledger_balance,
            recent_successes,
            wins_from_missed_goals,
        )

        balance = ledger_balance()
        click.secho(
            f"=== Wins: {balance.get('wins', 0)}   "
            f"Corrections: {balance.get('corrections', 0)} ===",
            fg="cyan",
            bold=True,
        )
        click.echo(
            "    Both numbers on one page. Neither is the whole picture, and a zero\n"
            "    on the left has meant a missing door more often than a missing win."
        )
        click.echo()

        entries = wins_from_missed_goals() if from_missed_goals else recent_successes(limit=limit)
        if not entries:
            click.secho("  (nothing filed yet)", fg="yellow")
            return
        for entry in entries[:limit]:
            click.secho(f"  {entry.get('id', '?')}", fg="green")
            click.echo(f"    what     : {str(entry.get('what', ''))[:150]}")
            click.echo(f"    yielded  : {str(entry.get('yielded', ''))[:150]}")
            click.echo(f"    evidence : {str(entry.get('evidence', ''))[:150]}")
            if entry.get("goal"):
                met = entry.get("goal_met")
                state = "met" if met else ("missed" if met is False else "n/a")
                click.echo(f"    goal     : {str(entry['goal'])[:110]} [{state}]")
            click.echo()
