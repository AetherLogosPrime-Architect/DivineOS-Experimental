"""`divineos gate-fire` — let a bash hook record its own firing.

The Python emitter in ``hooks/gate_event_ledger.py`` is reachable from Python.
Fifteen of the gates that actually block are `.sh` files, and a Python function
is not reachable from a shell script. This command is the shell-side end of the
same path — without it, "the emitter exists" is true and useless, which is the
condition it was built to end.

Andrew 2026-08-04: *"if you hit six gates thats 6 proper channels that need
made.lol"* — a fire marks where automation is missing. Aria measured the
instrument: 92 GATE_FIRE events, one distinct gate_name. The metric is real and
almost none of it is collected.

Usage from a hook, one line, never blocking:

    divineos gate-fire briefing-not-loaded \\
        --missing "briefing content in context" --derivable derivable || true

Always exits 0. A gate must never fail because its telemetry failed — that
would make measurement more dangerous than not measuring, which is how
instruments get removed.
"""

from __future__ import annotations

import click

from divineos.hooks.gate_event_ledger import (
    DERIVABILITY_UNKNOWN,
    DERIVABLE,
    NOT_DERIVABLE,
    record_simple_gate_fire,
)


def register(cli: click.Group) -> None:
    @cli.command("gate-fire")
    @click.argument("gate_name")
    @click.option(
        "--missing",
        default="",
        help="What the gate demanded and did not find. Free text, the reader's evidence.",
    )
    @click.option(
        "--derivable",
        type=click.Choice([DERIVABLE, NOT_DERIVABLE, DERIVABILITY_UNKNOWN]),
        default=DERIVABILITY_UNKNOWN,
        help=(
            "Was the missing thing derivable at fire time? "
            "derivable = a doorman could have supplied it, so this fire is a "
            "mini-failure. not_derivable = judgment was required, so this fire "
            "is a genuine save. unknown = not determined, which is a real "
            "answer and not a synonym for either."
        ),
    )
    @click.option("--actor", default="gate", help="Which layer emitted this.")
    @click.option("--quiet", is_flag=True, help="Emit nothing on stdout.")
    def gate_fire_cmd(
        gate_name: str, missing: str, derivable: str, actor: str, quiet: bool
    ) -> None:
        """Record that a gate fired, so the fire can be counted later.

        Andrew's metric needs a denominator. Aria's derivable column is the
        taxonomy: derivable fires are missing doormen, not-derivable fires are
        walls doing their job. Without this record neither is measurable, and
        prioritising which gates to automate away becomes picking from memory.
        """
        event_id = record_simple_gate_fire(
            gate_name=gate_name,
            what_was_missing=missing,
            derivable=derivable,
            actor=actor,
        )
        if not quiet:
            if event_id:
                click.echo(f"[gate-fire] recorded {gate_name} ({derivable}) {event_id[:12]}")
            else:
                # Say so rather than printing nothing. A silent telemetry
                # failure is the exact shape being measured against.
                click.echo(f"[gate-fire] NOT RECORDED — ledger write failed for {gate_name}")
