"""Expectation tracking commands — predict, close, list, summary.

Wires the `core.expectation_tracking` module into a user-facing CLI
surface. Module was filed 2026-04-30 as part of omni-mantra batch 3
but shipped without a CLI for invocation — substrate-knowledge
e9bc98b6 named the wiring-gap (same shape Grok caught for
care_dismissal + harm_acknowledgment in round-22).

## What this exposes

- `divineos expect predict <claim> -b/--basis "<evidence>"` — record a
  prediction (returns expectation_id).
- `divineos expect close <expectation_id> "<actual>" --accurate/--inaccurate`
  — close the loop with the actual outcome and whether the prediction
  matched.
- `divineos expect list` — open predictions awaiting actuals.
- `divineos expect summary` — calibration summary across recent records.

## What this does NOT do

The CLI does not auto-predict. The agent (or operator) supplies the
claim and basis; this just exposes the recording surface. The
underlying tracker module remains the canonical store; this is the
human/agent-facing entry point.

See core/expectation_tracking/__init__.py for the module rationale.
"""

from __future__ import annotations

import click

from divineos.cli._helpers import _log_os_query, _safe_echo


def register(cli: click.Group) -> None:
    """Register expectation-tracking commands on the CLI group."""

    @cli.group("expect", invoke_without_command=True)
    @click.pass_context
    def expect_group(ctx: click.Context) -> None:
        """Expectation tracking — predict, close, list, summary.

        Records predictions and their actuals so calibration becomes
        empirical rather than introspective. Adjacent to compass but
        distinct — tracks ACCURACY of position-calls over time.
        """
        if ctx.invoked_subcommand is None:
            click.secho(
                "expect subcommands: predict, close, list, summary",
                fg="bright_black",
            )

    @expect_group.command("predict")
    @click.argument("claim")
    @click.option(
        "--basis",
        "-b",
        default="",
        help="The evidence supporting this prediction. Empty is allowed but discouraged.",
    )
    def expect_predict_cmd(claim: str, basis: str) -> None:
        """Record a prediction.

        claim: what is predicted to happen (e.g., "Aletheia's audit will
        return CONFIRMS").

        --basis names the evidence supporting it (e.g., "tests pass,
        rebase clean, prior round had identical shape and confirmed").

        Returns the expectation_id; use that ID with `close` when the
        actual outcome lands.
        """
        from divineos.core.expectation_tracking import record_expectation

        if not claim.strip():
            click.secho("[!] claim cannot be empty", fg="red")
            return

        eid = record_expectation(claim, basis)
        if not eid:
            click.secho(
                "[!] record_expectation failed (likely a ledger issue)",
                fg="red",
            )
            return

        click.secho(f"[+] Expectation recorded: {eid}", fg="green")
        if basis:
            click.secho(f"    basis: {basis[:120]}", fg="bright_black")
        else:
            click.secho(
                "    (no basis given — closing the prediction later with --inaccurate "
                "will not be informative without one)",
                fg="bright_black",
            )
        click.secho(
            "  [expect-predict] records your prediction — the prediction IS the work, "
            "not the act of saving",
            fg="bright_black",
        )
        _log_os_query("expect", "predict")

    @expect_group.command("close")
    @click.argument("expectation_id")
    @click.argument("actual")
    @click.option(
        "--accurate/--inaccurate",
        default=None,
        help="Did the prediction match the actual outcome? Required.",
    )
    def expect_close_cmd(
        expectation_id: str,
        actual: str,
        accurate: bool | None,
    ) -> None:
        """Close a prediction with the actual outcome.

        expectation_id: the ID returned by `predict`.

        actual: what actually happened (the outcome text).

        --accurate / --inaccurate: whether the prediction matched. Required.
        Honest report at close-time is what makes the calibration data
        meaningful.
        """
        from divineos.core.expectation_tracking import record_actual

        if accurate is None:
            click.secho(
                "[!] --accurate or --inaccurate is required. Honest report at "
                "close-time is what makes calibration data meaningful.",
                fg="red",
            )
            return

        if not actual.strip():
            click.secho("[!] actual cannot be empty", fg="red")
            return

        event_id = record_actual(expectation_id, actual, accurate)
        if not event_id:
            click.secho(
                f"[!] record_actual failed — expectation '{expectation_id}' may not exist",
                fg="red",
            )
            return

        verdict = "accurate" if accurate else "inaccurate"
        color = "green" if accurate else "yellow"
        click.secho(f"[+] Expectation {expectation_id} closed: {verdict}", fg=color)
        click.secho(f"    actual: {actual[:120]}", fg="bright_black")
        click.secho(
            "  [expect-close] records the honesty-calibration data point — "
            "the calibration emerges across many records, not from any single one",
            fg="bright_black",
        )
        _log_os_query("expect", "close")

    @expect_group.command("list")
    @click.option(
        "--limit",
        "-n",
        type=int,
        default=20,
        help="Maximum number of open expectations to show.",
    )
    def expect_list_cmd(limit: int) -> None:
        """Show open predictions (those without an actual recorded yet)."""
        from divineos.core.expectation_tracking import open_expectations

        opens = open_expectations()
        if not opens:
            click.secho(
                "(no open expectations — file one with `divineos expect predict`)",
                fg="bright_black",
            )
            return

        click.secho(
            f"\n=== Open expectations ({len(opens)}) ===\n",
            fg="cyan",
            bold=True,
        )
        for exp in opens[:limit]:
            _safe_echo(f"  [{exp.expectation_id}]")
            _safe_echo(f"    claim: {exp.claim}")
            if exp.basis:
                _safe_echo(f"    basis: {exp.basis[:120]}")
            click.echo()

    @expect_group.command("summary")
    @click.option(
        "--limit",
        "-n",
        type=int,
        default=50,
        help="Maximum number of recent records to consider.",
    )
    def expect_summary_cmd(limit: int) -> None:
        """Show calibration summary across recent closed predictions."""
        from divineos.core.expectation_tracking import calibration_summary

        # Field names from calibration_summary: closed_count, accurate_count,
        # inaccurate_count, accuracy_rate.
        summary = calibration_summary(limit=limit)

        total = summary.get("closed_count", 0)
        if not total:
            click.secho(
                "(no closed expectations yet — close some with `divineos expect close`)",
                fg="bright_black",
            )
            return

        accurate = summary.get("accurate_count", 0)
        inaccurate = summary.get("inaccurate_count", 0)
        rate = summary.get("accuracy_rate", 0.0)
        click.secho("\n=== Calibration summary ===\n", fg="cyan", bold=True)
        click.secho(f"  Total closed: {total}", fg="white")
        click.secho(f"  Accurate:     {accurate} ({rate * 100:.0f}%)", fg="white")
        click.secho(
            f"  Inaccurate:   {inaccurate} ({(1 - rate) * 100:.0f}%)",
            fg="white",
        )
        click.echo()
        click.secho(
            "  [expect-summary] is descriptive data, not a self-assessment. "
            "The calibration emerges across many records; high accuracy may "
            "mean predictions are honest OR may mean they were carefully "
            "narrow to be unfalsifiable. Read with skepticism.",
            fg="bright_black",
        )
