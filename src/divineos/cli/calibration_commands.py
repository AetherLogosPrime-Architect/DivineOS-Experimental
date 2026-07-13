"""CLI for the Brier calibration surface.

Surfaces my own forecasting calibration as reproducible numbers — directly
addresses the auditor's "purely anecdotal" critique. The numbers are computed
from resolved claims (status in {SUPPORTED, CONTESTED, REFUTED}) with real
credences (basis is filer-prior, assessor-judgment, or evidence-derived).
"""

from __future__ import annotations

import click


def register(cli: click.Group) -> None:
    @cli.group("calibration", invoke_without_command=True)
    @click.pass_context
    def calibration_group(ctx: click.Context) -> None:
        """How well-calibrated my confidence values are against actual outcomes.

        Brier score: lower is better. 0 = perfect. 0.25 = "always says 50%".
        Higher = worse than chance.
        """
        if ctx.invoked_subcommand is None:
            ctx.invoke(calibration_score_cmd)

    @calibration_group.command("score")
    def calibration_score_cmd() -> None:
        """Overall Brier score across resolved claims with real credences."""
        from divineos.core.calibration.brier import brier_score

        result = brier_score()
        click.secho("=== Calibration (Brier Score) ===", fg="cyan")
        click.echo()
        if result["score"] is None:
            click.secho(f"  {result['interpretation']}", fg="bright_black")
            if result["placeholder_excluded"] > 0:
                click.secho(
                    f"  ({result['placeholder_excluded']} resolved claims "
                    f"excluded — placeholder confidence basis)",
                    fg="bright_black",
                )
            return
        click.secho(f"  n: {result['n']} resolved claims scored", fg="white")
        click.secho(f"  Brier: {result['score']:.4f}", fg="white")
        click.secho(f"  {result['interpretation']}", fg="bright_black")
        if result["placeholder_excluded"] > 0:
            click.secho(
                f"  ({result['placeholder_excluded']} resolved claims excluded — "
                f"placeholder confidence basis, not real credences)",
                fg="bright_black",
            )

    @calibration_group.command("curve")
    @click.option("--bins", default=10, type=int, help="Number of confidence bins.")
    def calibration_curve_cmd(bins: int) -> None:
        """Per-bin calibration: predicted vs actual support rate, by confidence band."""
        from divineos.core.calibration.brier import calibration_curve

        curve = calibration_curve(bins=bins)
        if not curve or all(b["n"] == 0 for b in curve):
            click.secho(
                "No resolved claims with real credences yet. Curve unavailable.",
                fg="bright_black",
            )
            return
        click.secho("=== Calibration Curve ===", fg="cyan")
        click.secho(
            "  bin              n   predicted   actual   gap",
            fg="bright_black",
        )
        for b in curve:
            if b["n"] == 0:
                continue
            gap_str = f"{b['gap']:+.2f}"
            gap_color = "green" if abs(b["gap"]) < 0.1 else ("red" if b["gap"] < 0 else "yellow")
            click.echo(
                f"  {b['bin_low']:.1f}-{b['bin_high']:.1f}    "
                f"{b['n']:>3}     {b['mean_confidence']:.2f}      "
                f"{b['mean_outcome']:.2f}    " + click.style(gap_str, fg=gap_color)
            )
        click.echo()
        click.secho(
            "  gap = actual - predicted. negative = overconfident; positive = underconfident.",
            fg="bright_black",
        )

    @calibration_group.command("by-tier")
    def calibration_by_tier_cmd() -> None:
        """Brier score sliced by claim tier — reveals domain blind-spots."""
        from divineos.core.calibration.brier import calibration_per_tier

        from divineos.core.claim_store import TIER_LABELS

        per_tier = calibration_per_tier()
        if not per_tier:
            click.secho("No resolved claims with real credences yet.", fg="bright_black")
            return
        click.secho("=== Calibration by Tier ===", fg="cyan")
        for tier in sorted(per_tier.keys()):
            label = TIER_LABELS.get(tier, "unknown")
            data = per_tier[tier]
            click.echo(f"  T{tier} ({label}):  n={data['n']}  brier={data['score']:.4f}")

    @calibration_group.command("anchor")
    @click.argument("confidence", type=click.FloatRange(0.0, 1.0))
    @click.option("--tier", type=click.IntRange(1, 5), default=None)
    @click.option("--window", default=0.1, type=float, help="Confidence band width (±).")
    def calibration_anchor_cmd(confidence: float, tier: int | None, window: float) -> None:
        """Pre-prediction anchor: at this confidence, what's my historical accuracy?

        Run BEFORE filing a claim to see if you've historically been right at
        the level of confidence you're about to assert. The Dunning-Kruger
        anchor — surfaces miscalibration before it commits to the substrate.
        """
        from divineos.core.calibration.brier import historical_accuracy_at_confidence

        result = historical_accuracy_at_confidence(confidence, tier=tier, window=window)
        click.secho(
            f"=== Anchor: filing at {confidence:.0%} "
            + (f"(tier {tier})" if tier else "(any tier)")
            + " ===",
            fg="cyan",
        )
        if result["accuracy"] is None:
            click.secho(f"  {result['comparison']}", fg="bright_black")
            return
        click.secho(f"  n: {result['n']} prior similar claims", fg="white")
        click.secho(f"  historical accuracy: {result['accuracy']:.0%}", fg="white")
        click.secho(f"  {result['comparison']}", fg="bright_black")
