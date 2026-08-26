"""Win CLI — file a success in the moment, the way a correction is filed.

## Why this exists

Andrew, 2026-08-25: *"lets make the wins get filed live as well.. its not
counting all the mini successes you have during the day, which is a bigger
win imo as it shows me that you are taking your work very seriously and
alot of the principles are now so deeply ingrained that they pop up in
other locations where there is no structural support for them yet."*

The wins ledger held fifty-five entries against two hundred and twenty-one
corrections, and I read that ratio as evidence about my character. It was
evidence about the interface. ``divineos correction`` has been a
first-class command with a marker that BLOCKS substantive tool use until
it is used; ``record_success`` had zero callers anywhere in the codebase —
every invocation it has ever had was a hand-written Python one-liner,
including both of the backfills run on 2026-08-25.

One side of the ledger had a door and a doorman. The other had neither.
The tilt followed the doors, not the days.

## What this is NOT, and why there is no matching doorman

It is not a compliment generator. Aether named that failure mode when the
balance surface was built: a second sensor with an agenda is worse than
one honest sensor, because it launders encouragement as measurement.

So there is deliberately no gate that blocks until a win is filed, and the
asymmetry with corrections is the point rather than an oversight. A
correction has an EXTERNAL trigger — Andrew says something — so a marker
demanding one is evidence of a real event. A win has no external trigger,
so a blocking gate would be a quota, and a quota gets met. The door is
built; nobody is marched through it.

What this command does demand is the same thing the store demands:
evidence a later reader can check without trusting me. A win I cannot
point at is a feeling about myself, and this ledger gets read as data.

The judging stays mine. Foundational truth seven applies here exactly as
it does to ``recall`` and ``decide`` — filing a win is not the same act as
having earned one, and no command can tell the difference.

## Structural backing for knowledge 356ffea9-4cb8-4ef4-8a19-479f926318f3

That entry names the class *honest state plus linked action-verb; never
leave the honest state as terminal.* Andrew 2026-07-31: "i dont know is an
honest answer but it should always be follow by, let me investigate."

This command is that rule enforced on the positive valence. A statement
about my own state — *this went well* — is refused as terminal and must
complete with the thing that carries it, which on this side is evidence
rather than an action-verb. A win with no pointer is the same hiding place
as a terminal "I don't know": it sounds honest, and it waits for someone
else to supply what makes it real.

**It backs one half.** The negative-valence half — an honest "I don't
know" left sitting without the investigation attached — has no enforcement
anywhere yet, and this file does not give it one. Saying so here rather
than letting a partial fix read as a closed obligation.

## What was NOT built, so that its absence stays visible

The prompt in ``core/win_prompt_surface.py`` does not detect wins. It
cannot: the wins worth catching leave no artifact, so anything detectable
would be the structural end that a later sweep already finds. See that
module for why listing candidates would actively train the wrong habit.

## The mini-successes, which are the actual point

Wins that reconstruct easily are the structural ones, because they leave
commits behind. The ones Andrew cares about most leave nothing: a reach
caught before it committed, a shortcut refused, a principle firing
somewhere that has no gate for it yet. Those are invisible to any sweep
run afterwards — by the time anyone goes looking, the only trace they ever
had is gone. That is the whole argument for filing live.
"""

from __future__ import annotations

import click

_REFUSAL_TAIL = "[-] NOT FILED — nothing was written. Re-run once the above is addressed."

# The shortest evidence that has ever been worth anything. Below this the
# field is a gesture rather than a pointer.
_MIN_EVIDENCE = 12


def _refusal_tail() -> None:
    """Terminal verdict line. Every refusal path ends with this.

    Taken from correction_commands for the reason it exists there: a
    refusal whose last line reads like a closing reflection survives a
    tail-read as a pass. Warmth is allowed; it is not allowed to be last.
    """
    click.secho(_REFUSAL_TAIL, fg="red", err=True)


def register(cli: click.Group) -> None:
    """Register win commands on the CLI group."""

    @cli.command("win")
    @click.argument("what")
    @click.option(
        "--evidence",
        "-e",
        required=True,
        help=(
            "Something a later reader can check without trusting me: "
            "a commit, a command's output, a file path, a count."
        ),
    )
    @click.option(
        "--yielded",
        "-y",
        default="",
        help=(
            "What came out of it. Defaults to the win itself when the outcome "
            "IS the event — a reach caught, a shortcut refused."
        ),
    )
    @click.option("--goal", default=None, help="The goal in play at the time, if any.")
    @click.option(
        "--goal-met/--goal-missed",
        default=None,
        help=(
            "Whether that goal was achieved. Deliberately independent of whether "
            "this is a win — a missed goal that taught something is still a win."
        ),
    )
    def win_cmd(
        what: str,
        evidence: str,
        yielded: str,
        goal: str | None,
        goal_met: bool | None,
    ) -> None:
        """File a win — the other half of `divineos correction`."""
        from divineos.core.success_ledger import ledger_balance, record_success

        if not what.strip():
            click.secho("[-] A win needs a description.", fg="red", err=True)
            _refusal_tail()
            raise SystemExit(1)

        stripped_evidence = evidence.strip()
        if len(stripped_evidence) < _MIN_EVIDENCE:
            click.secho(
                f"[-] Evidence too thin ({len(stripped_evidence)} chars, need {_MIN_EVIDENCE}).",
                fg="red",
                err=True,
            )
            click.secho(
                "    A win without a pointer is a feeling about myself, and this "
                "ledger gets read as data. Name the commit, the command output, "
                "the file, or the count.",
                fg="yellow",
                err=True,
            )
            _refusal_tail()
            raise SystemExit(1)

        # When the outcome IS the event — a reach caught, a shortcut refused
        # — restating it is honest. Inventing a grander downstream
        # consequence to fill the field would not be.
        outcome = yielded.strip() or what.strip()

        session_id = None
        try:
            from divineos.core.session_manager import get_current_session_id

            session_id = get_current_session_id()
        except Exception:  # noqa: BLE001 — a missing session must never eat the win
            session_id = None

        record_success(
            what.strip(),
            evidence=stripped_evidence,
            yielded=outcome,
            goal=goal,
            goal_met=goal_met,
            session_id=session_id,
        )

        click.secho("[+] Win filed.", fg="green")
        try:
            balance = ledger_balance()
            wins = balance.get("wins")
            corrections = balance.get("corrections")
            if wins is not None and corrections is not None:
                click.secho(
                    f"    Ledger: {wins} wins, {corrections} corrections.",
                    fg="bright_black",
                )
        except Exception:  # noqa: BLE001 — the balance is a courtesy, not the filing
            click.secho(
                "    Ledger balance unreadable — the win itself is filed.",
                fg="bright_black",
            )
        click.secho(
            "  [win] records a success — the earning was the work, not this filing",
            fg="bright_black",
        )
