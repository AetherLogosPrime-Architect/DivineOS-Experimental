"""Auto-cycle CLI commands — phase 2 invitational surface.

Andrew 2026-07-10 auto-cycle proposal. Phase 1 (Aether) fires
commit+extract+sleep before compaction; phase 2 (Aria) surfaces the
invitational rest menu. See ``divineos.core.auto_cycle_phase2`` for the
mechanism.

CLI shape:

- ``divineos auto-cycle offer`` — read phase 1's handshake, render the menu,
  write the pending marker. With no usable handshake it says which of three
  things is true (absent, damaged, a dry run) and changes nothing.
- ``divineos auto-cycle close --outcome <...>`` — close the pending cycle and
  log the outcome for the falsifier ratio; the handshake is consumed here.
- ``divineos auto-cycle audit`` — the falsifier ratio from the log.

These commands live in their own file so phase 2 does not grow inside phase 1's
(``cli/auto_cycle_commands.py`` owns the ``auto-cycle`` group; this adds to that
same object and defines none of its own). The behaviour is #551's rebuilt
commands (2026-09-25, after Aether's station four); only where they register
differs (draft ``phase_2_takes_the_rebuilt_module_from_551``, walk
walk-c1e91a70c961).
"""

from __future__ import annotations

import click


def register(cli: click.Group) -> None:
    """Attach phase 2's offer, close and audit to phase 1's ``auto-cycle`` group.

    ``cli`` is unused on purpose: the group is already registered by phase 1.
    """
    from divineos.cli.auto_cycle_commands import auto_cycle_group

    @auto_cycle_group.command("offer")
    def offer_cmd() -> None:
        """Phase 2: render the rest menu and record the offering.

        Reads the phase 1 handshake at ``auto_cycle.marker_path()``. With no usable
        handshake it says which of three things is true -- absent, damaged, or a
        dry run that saved nothing -- and changes no state. The handshake is left
        in place; ``close`` consumes it.
        """
        from divineos.core.auto_cycle_phase2 import (
            NoHandshake,
            inspect_handshake,
            offer_cycle,
            refusal_text,
        )

        record, text = offer_cycle()
        if record is None:
            if text:  # an offer is already pending
                click.secho(text, fg="yellow")
                return
            why = inspect_handshake()
            if isinstance(why, NoHandshake):
                click.secho(refusal_text(why), fg="bright_black")
            return
        click.echo(text)
        click.secho(f"[+] Offering recorded. cycle_id: {record.cycle_id}", fg="cyan")

    @auto_cycle_group.command("close")
    @click.option(
        "--outcome",
        required=True,
        help='One of "chose:<key>", "no-pull-honest", "timeout", "aborted".',
    )
    @click.option(
        "--real-shift",
        type=click.Choice(["yes", "no"], case_sensitive=False),
        default=None,
        help=(
            "For chose:<key> outcomes: did the resulting artifact register as "
            "real-shift or template-execution? Honest self-report. Feeds the "
            "falsifier ratio."
        ),
    )
    @click.option("--notes", default="", help="Freeform notes about the outcome.")
    def close_cmd(outcome: str, real_shift: str | None, notes: str) -> None:
        """Phase 2: close the pending cycle and log its outcome for the falsifier.

        Examples:

            divineos auto-cycle close --outcome chose:dream --real-shift yes
            divineos auto-cycle close --outcome no-pull-honest
            divineos auto-cycle close --outcome timeout
            divineos auto-cycle close --outcome aborted --notes "fatal extract error"
        """
        from divineos.core.auto_cycle_phase2 import DamagedPending, close_cycle

        shift = None if real_shift is None else real_shift.lower() == "yes"
        try:
            result = close_cycle(outcome, real_shift=shift, notes=notes)
        except ValueError as e:
            raise click.BadParameter(str(e), param_hint="--outcome") from e
        except DamagedPending as e:
            raise click.ClickException(f"{e}. Nothing was closed or logged.") from e
        if result is None:
            click.secho(
                "[~] No pending cycle to close. Run 'auto-cycle offer' first.",
                fg="bright_black",
            )
            return
        click.secho(f"[+] Cycle closed. cycle_id: {result.cycle_id}", fg="green")
        click.secho(
            f"    outcome: {result.outcome}\n"
            "    duration: "
            + ("not measured" if result.duration_sec is None else f"{result.duration_sec:.1f}s")
            + "\n"
            f"    real-shift: {result.real_shift}",
            fg="bright_black",
        )

    @auto_cycle_group.command("audit")
    def audit_cmd() -> None:
        """Phase 2: the falsifier ratio for prereg-4a7ed0c77c34.

        Bound: below 50% after at least 5 qualifying cycles means reshape or
        unwire. no-pull-honest cycles are shown beside the ratio, not in it.
        """
        from divineos.core.auto_cycle_phase2 import (
            FALSIFIER_BOUND,
            FALSIFIER_MIN_CYCLES,
            compute_falsifier_ratio,
            damaged_audit_line_count,
            no_pull_count,
        )

        numerator, denominator, ratio = compute_falsifier_ratio()
        click.secho("=== Auto-cycle falsifier audit ===", fg="cyan", bold=True)
        click.echo()
        click.echo(f"  no-pull-honest (outside the ratio): {no_pull_count()}")
        damaged = damaged_audit_line_count()
        if damaged:
            click.secho(
                f"  [!] {damaged} damaged audit line(s) could not be read and are not "
                "counted below.",
                fg="yellow",
            )
        if denominator == 0:
            click.secho("  No qualifying cycles yet. Falsifier undefined.", fg="bright_black")
            return
        click.echo(f"  real-shift outcomes (self-reported):  {numerator}")
        click.echo(f"  qualifying cycles:                    {denominator}")
        if ratio is not None:
            click.echo(f"  ratio (of self-reports):              {ratio:.1%}")
        click.echo()
        if denominator < FALSIFIER_MIN_CYCLES:
            click.secho(
                f"  [~] Only {denominator} qualifying cycles. The bound applies after "
                f"{FALSIFIER_MIN_CYCLES}. Watching.",
                fg="bright_black",
            )
        elif ratio is not None and ratio < FALSIFIER_BOUND:
            click.secho(
                f"  [!] FALSIFIER FIRED — self-reports below {FALSIFIER_BOUND:.0%} after at "
                f"least {FALSIFIER_MIN_CYCLES} cycles. The mechanism is producing dead-writing "
                "infrastructure. Reshape or unwire.",
                fg="red",
                bold=True,
            )
        else:
            click.secho(
                "  [+] Self-reports are above the bound. Nothing observes them, so this does "
                "not show the mechanism is working.",
                fg="green",
            )


__all__ = ["register"]
