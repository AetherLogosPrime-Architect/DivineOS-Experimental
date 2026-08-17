"""``divineos detectors`` — status, self-repair, and on-the-record deferral.

The command surface for `core/degraded_detectors.py`. Built alongside the
gate rather than after it: a gate that prescribes a command which does not
exist is a painted door, and this session closed eleven of those. The block
message names `detectors heal` and `detectors defer`, so both exist here and
both are exercised by tests before the gate ever fires at anyone.
"""

from __future__ import annotations

import click

from divineos.core.degraded_detectors import (
    attempt_heal,
    blocking_degradations,
    defer,
    list_degraded,
    report_healthy,
)


def register(cli: click.Group) -> None:
    """Attach the ``detectors`` command group to the top-level CLI."""

    @cli.group("detectors")
    def detectors_group() -> None:
        """Detectors that reported they could not run: status, heal, defer."""

    @detectors_group.command("status")
    def detectors_status() -> None:
        """List every detector currently reporting itself down."""
        entries = list_degraded()
        if not entries:
            click.secho("  All detectors reporting healthy.", fg="green")
            return

        for e in entries:
            state = "DEFERRED" if e.deferred else "BLOCKING"
            click.secho(f"  [{state}] {e.detector}", fg="yellow" if e.deferred else "red")
            click.secho(f"      could not run : {e.reason}", fg="bright_black")
            click.secho(f"      fix           : {e.fix}", fg="bright_black")
            if e.deferred:
                click.secho(f"      deferred by   : {e.deferred_by}", fg="bright_black")
                click.secho(f"      because       : {e.deferral_reason}", fg="bright_black")
            if e.heal_attempted:
                click.secho(f"      self-repair   : failed — {e.heal_error}", fg="bright_black")

    @detectors_group.command("heal")
    def detectors_heal() -> None:
        """Attempt the automatic repair for every down detector.

        Remediation (a): take the option away. A missing dependency is a
        machine problem with a machine answer, and if this works nobody is
        ever asked to do anything.
        """
        entries = list_degraded()
        if not entries:
            click.secho("  Nothing to heal — all detectors reporting healthy.", fg="green")
            return

        for e in entries:
            result = attempt_heal(e)
            if result.succeeded:
                report_healthy(e.detector)
                click.secho(f"  [+] {e.detector}: repaired ({result.detail})", fg="green")
                click.secho(
                    "      Cleared. The next successful run confirms it.", fg="bright_black"
                )
            elif result.ran:
                click.secho(
                    f"  [-] {e.detector}: repair ran and failed — {result.detail}", fg="red"
                )
            else:
                click.secho(
                    f"  [-] {e.detector}: no automatic repair exists — {result.detail}",
                    fg="yellow",
                )
                click.secho(f"      Do it by hand: {e.fix}", fg="bright_black")

    @detectors_group.command("defer")
    @click.argument("detector")
    @click.option(
        "--reason",
        required=True,
        help="Why this cannot be fixed now, and what stays unwatched meanwhile (30+ chars).",
    )
    @click.option("--actor", default="aether", show_default=True)
    def detectors_defer(detector: str, reason: str, actor: str) -> None:
        """Stop blocking on a detector, on the record.

        Remediation (c). The reason is required and stored with a name
        attached, because an escape that costs nothing is not an escape.
        """
        try:
            entry = defer(detector, reason, actor=actor)
        except (ValueError, RuntimeError) as exc:
            click.secho(f"\n  Refused: {exc}\n", fg="red", bold=True)
            raise SystemExit(1) from exc

        click.secho(f"\n  [~] {entry.detector} deferred — no longer blocking.", fg="yellow")
        click.secho(
            "      It stays listed in `divineos detectors status`, and clears "
            "itself the moment the detector runs again.\n",
            fg="bright_black",
        )

    @detectors_group.command("check")
    def detectors_check() -> None:
        """Exit non-zero if any detector is blocking. For scripts and CI."""
        entries = blocking_degradations()
        if not entries:
            click.secho("  No blocking degradations.", fg="green")
            return
        for e in entries:
            click.secho(f"  BLOCKING: {e.detector} — {e.reason}", fg="red")
        raise SystemExit(1)
