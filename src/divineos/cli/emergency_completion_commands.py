"""CLI for the emergency-completion lane.

WHY THIS FILE APPEARED LATE. ``core/emergency_completion.py`` was written
complete — arm, consume, rate-limit, debt, resolve_debt — and never given a
command. The module's own docstring told the reader to run
``divineos emergency-completion resolve --diagnosis "..."``, and no such
command existed anywhere. The dark-matter sweep on 2026-08-02 surfaced it.

That is not a cosmetic gap. ``arm()`` refuses while a prior debt is
outstanding, and ``resolve_debt()`` was the only thing that could clear one.
With no way to reach it, the FIRST emergency completion would have left a
permanent debt and the lane would never open again — the mechanism bricking
itself on first use, discoverable only during the emergency it exists for.

Same defect class as the m3 doorman rebuilt earlier today: a success
condition that cannot be reached. There it was a gate that could only ever
refuse; here it is a debt that could only ever accrue.
"""

from __future__ import annotations

import time

import click

from divineos.core.emergency_completion import (
    _outstanding_debt,
    arm,
    is_armed,
    resolve_debt,
)


def _fmt_age(ts: float) -> str:
    mins = max(0, int((time.time() - ts) // 60))
    if mins < 60:
        return f"{mins}m ago"
    return f"{mins // 60}h{mins % 60:02d}m ago"


def register(cli: click.Group) -> None:
    """Attach the ``emergency-completion`` command group to the top-level CLI."""

    @cli.group("emergency-completion")
    def ec_group() -> None:
        """Emergency-completion lane: arm it, inspect it, discharge its debt."""

    @ec_group.command("status")
    def ec_status() -> None:
        """Show whether the lane is armed and whether a debt is outstanding."""
        debt = _outstanding_debt()
        armed = is_armed()

        click.secho(
            f"  armed        : {'YES' if armed else 'no'}",
            fg="yellow" if armed else "bright_black",
        )
        if debt is None:
            click.secho("  debt         : none outstanding", fg="green")
            return

        click.secho(f"  debt         : OUTSTANDING ({_fmt_age(debt.consumed_at)})", fg="red")
        click.secho(f"    for        : {debt.for_ref}", fg="bright_black")
        click.secho(f"    consumed by: {debt.consumed_by}", fg="bright_black")
        click.secho(f"    reason     : {debt.reason}", fg="bright_black")
        click.echo()
        click.secho(
            "  A new arm is refused while this stands. Discharge it:\n"
            '    divineos emergency-completion resolve --diagnosis "..."',
            fg="yellow",
        )

    @ec_group.command("arm")
    @click.option("--reason", required=True, help="The in-flight critical repair, in full.")
    @click.option(
        "--for",
        "for_ref",
        required=True,
        help="Prior work being completed: knowledge id, claim id, or pre-reg id.",
    )
    @click.option("--risk", required=True, help="What breaks if this goes wrong.")
    def ec_arm(reason: str, for_ref: str, risk: str) -> None:
        """Arm the lane for the next gate-fire (one-shot, accrues debt)."""
        try:
            armed = arm(reason=reason, for_ref=for_ref, risk=risk)
        except (ValueError, RuntimeError) as exc:
            click.secho(f"\n  Refused: {exc}\n", fg="red", bold=True)
            raise SystemExit(1) from exc

        click.secho("\n  [+] Emergency-completion armed — one gate-fire.", fg="yellow", bold=True)
        click.secho(f"      for : {armed.for_ref}", fg="bright_black")
        click.secho(
            "      Consuming it files a debt that must be discharged with a "
            "root-cause diagnosis before the lane opens again.\n",
            fg="bright_black",
        )

    @ec_group.command("resolve")
    @click.option(
        "--diagnosis",
        required=True,
        help=(
            "Root-cause diagnosis, >=100 chars, naming (a) what class the gate "
            "should have distinguished, (b) whether the emergency-classification "
            "was right in hindsight, (c) what structural change prevents the "
            "false-positive next time."
        ),
    )
    @click.option("--actor", default="aether", show_default=True)
    def ec_resolve(diagnosis: str, actor: str) -> None:
        """Discharge the outstanding debt by filing a root-cause diagnosis.

        THE COMMAND THAT WAS MISSING. Without it an outstanding debt could
        never clear, and ``arm`` refuses while one stands — so the lane would
        have closed permanently the first time it was used.
        """
        try:
            debt = resolve_debt(diagnosis=diagnosis, actor=actor)
        except (ValueError, RuntimeError) as exc:
            click.secho(f"\n  Refused: {exc}\n", fg="red", bold=True)
            raise SystemExit(1) from exc

        click.secho("\n  [+] Emergency-completion debt discharged.", fg="green", bold=True)
        click.secho(f"      was for : {debt.for_ref}", fg="bright_black")
        click.secho("      The lane is open again.\n", fg="bright_black")
