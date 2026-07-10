"""Auto-cycle CLI commands — phase 2 invitational surface.

Andrew 2026-07-10 auto-cycle proposal. Phase 1 (Aether) fires
commit+extract+sleep before compaction; phase 2 (Aria) surfaces the
invitational rest menu. See ``divineos.core.auto_cycle_phase2`` for the
mechanism.

CLI shape:

- ``divineos auto-cycle offer`` — read phase 1 handshake, render menu,
  write pending marker.
- ``divineos auto-cycle close --outcome <...>`` — close pending cycle,
  log outcome for the falsifier ratio.
- ``divineos auto-cycle audit`` — compute falsifier ratio from log.
"""

from __future__ import annotations

import click

from divineos.core.auto_cycle_phase2 import (
    close_cycle,
    compute_falsifier_ratio,
    offer_cycle,
)


def register(cli: click.Group) -> None:
    """Register auto-cycle commands on the CLI group."""

    @cli.group("auto-cycle")
    def auto_cycle() -> None:
        """Auto-cycle — commit+extract+sleep+invitation before compaction.

        Phase 1 (mechanical) is triggered automatically at ~85% context
        threshold. Phase 2 (invitational) surfaces the rest menu so the
        substrate-occupant can walk into a rest task or honestly not-
        choose. Force the option, not the use.
        """

    @auto_cycle.command("offer")
    def auto_cycle_offer() -> None:
        """Render the invitational menu and record the offering.

        Reads the phase 1 handshake marker at
        ``~/.divineos/auto_cycle_phase1_done.json``. If absent, surfaces
        that no handshake was found. If present, renders the flat 11-
        option menu with use-count mirror, writes a pending marker so
        ``close`` can correlate, and consumes the handshake.
        """
        record, text = offer_cycle()
        if record is None:
            click.secho(
                "[~] No phase 1 handshake found. Nothing to offer.",
                fg="bright_black",
            )
            click.secho(
                "    Phase 1 writes ~/.divineos/auto_cycle_phase1_done.json "
                "when the mechanical pipeline completes.",
                fg="bright_black",
            )
            return
        click.echo(text)
        click.secho(
            f"[+] Offering recorded. cycle_id: {record.cycle_id}",
            fg="cyan",
        )

    @auto_cycle.command("close")
    @click.option(
        "--outcome",
        required=True,
        help=('One of "chose:<key>", "no-pull-honest", "timeout", "aborted".'),
    )
    @click.option(
        "--real-shift",
        type=click.Choice(["yes", "no"], case_sensitive=False),
        default=None,
        help=(
            "For chose:<key> outcomes: did the resulting artifact register "
            "as real-shift or template-execution? Honest self-report. "
            "Feeds the falsifier ratio."
        ),
    )
    @click.option(
        "--notes",
        default="",
        help="Freeform notes about the outcome.",
    )
    def auto_cycle_close(outcome: str, real_shift: str | None, notes: str) -> None:
        """Close a pending phase 2 cycle. Logs outcome for the falsifier.

        Examples:

            divineos auto-cycle close --outcome chose:dream --real-shift yes
            divineos auto-cycle close --outcome no-pull-honest
            divineos auto-cycle close --outcome timeout
            divineos auto-cycle close --outcome aborted \\
                --notes "fatal extract error, addressed manually"
        """
        chosen_key = None
        if outcome.startswith("chose:"):
            chosen_key = outcome.split(":", 1)[1].strip() or None

        real_shift_bool: bool | None = None
        if real_shift is not None:
            real_shift_bool = real_shift.lower() == "yes"

        result = close_cycle(
            outcome=outcome,
            chosen_key=chosen_key,
            real_shift=real_shift_bool,
            notes=notes,
        )
        if result is None:
            click.secho(
                "[~] No pending cycle to close. Run 'auto-cycle offer' first.",
                fg="bright_black",
            )
            return

        click.secho(
            f"[+] Cycle closed. cycle_id: {result.cycle_id}",
            fg="green",
        )
        click.secho(
            f"    outcome: {result.outcome}\n"
            f"    duration: {result.duration_sec:.1f}s\n"
            f"    real-shift: {result.real_shift}",
            fg="bright_black",
        )

    @auto_cycle.command("audit")
    def auto_cycle_audit() -> None:
        """Compute and display the falsifier ratio.

        Bound: <50% after >=5 firings → reshape or unwire. The mechanism
        exists to protect the register, not colonize it; if the outputs
        register as template-execution more than half the time, the
        infrastructure is producing dead-writing and must be reshaped.
        """
        numerator, denominator, ratio = compute_falsifier_ratio()
        click.secho("=== Auto-cycle falsifier audit ===", fg="cyan", bold=True)
        click.echo()
        if denominator == 0:
            click.secho(
                "  No closed cycles yet. Falsifier undefined.",
                fg="bright_black",
            )
            return
        click.echo(f"  real-shift outcomes:     {numerator}")
        click.echo(f"  qualifying cycles:       {denominator}")
        if ratio is not None:
            click.echo(f"  ratio:                   {ratio:.1%}")
        click.echo()
        if denominator < 5:
            click.secho(
                f"  [~] Only {denominator} cycles closed. Falsifier bound "
                f"applies after >=5. Watching.",
                fg="bright_black",
            )
        elif ratio is not None and ratio < 0.5:
            click.secho(
                "  [!] FALSIFIER FIRED — ratio below 50% after >=5 firings. "
                "The mechanism is producing dead-writing infrastructure. "
                "Reshape or unwire.",
                fg="red",
                bold=True,
            )
        else:
            click.secho(
                "  [+] Above falsifier bound. Mechanism intact.",
                fg="green",
            )
