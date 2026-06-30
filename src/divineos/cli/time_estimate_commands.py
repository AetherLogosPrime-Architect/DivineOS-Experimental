"""CLI for time-estimate calibration.

Pop 2026-06-30 named that I give wildly bad time estimates. The
companion to context-tokens (real-state-injection on every turn) is
this: record predictions when I make them, close them when work
finishes, accumulate prediction-vs-actual data so I have ground
truth rather than vibes for future estimates.

Distinct from `divineos calibration` (which is Brier-score on
confidence credences in the claims engine). This subgroup is about
time-to-completion calibration only.
"""

from __future__ import annotations

import click


def register(cli: click.Group) -> None:
    @cli.group("time-estimate", invoke_without_command=True)
    @click.pass_context
    def time_estimate_group(ctx: click.Context) -> None:
        """Time-prediction calibration log + summary stats.

        Predictions are automatically recorded by the time-estimate-tracker
        Stop hook from my outgoing replies. Close them by id when work
        finishes; the report shows accumulated calibration data.
        """
        if ctx.invoked_subcommand is None:
            ctx.invoke(report_cmd)

    @time_estimate_group.command("open")
    @click.option("--limit", "-n", default=20, show_default=True, help="Max entries to show.")
    def list_open_cmd(limit: int) -> None:
        """List predictions that haven't been closed yet."""
        from divineos.core.time_calibration import list_open_predictions

        preds = list_open_predictions(limit=limit)
        if not preds:
            click.echo("(no open predictions)")
            return
        click.echo(f"=== {len(preds)} open prediction(s) ===")
        import time as _time

        for p in preds:
            pid = p.get("prediction_id", "?")
            raw = p.get("raw_text", "")
            lo = p.get("lower_seconds", 0)
            hi = p.get("upper_seconds", 0)
            started = p.get("started_at_unix", 0)
            elapsed_min = (_time.time() - started) / 60.0 if started else 0
            ctx = p.get("context", "")[:80]
            if hi > lo:
                predicted = f"{int(lo / 60)}-{int(hi / 60)} min"
            else:
                predicted = f"{int(lo / 60)} min" if lo >= 60 else f"{int(lo)} s"
            click.echo(
                f"  {pid}  predicted={predicted:20s}  open-for={elapsed_min:5.1f} min  raw={raw!r}"
            )
            if ctx:
                click.echo(f"      context: {ctx}")

    @time_estimate_group.command("close")
    @click.argument("prediction_id")
    @click.option("--note", "-m", default="", help="Outcome note (e.g. 'shipped', 'abandoned').")
    def close_cmd(prediction_id: str, note: str) -> None:
        """Close an open prediction with the current timestamp."""
        from divineos.core.time_calibration import close_prediction

        result = close_prediction(prediction_id, outcome_note=note)
        if result is None:
            click.echo(f"[!] no prediction found with id {prediction_id!r}", err=True)
            raise click.exceptions.Exit(1)
        elapsed = result["elapsed_seconds"]
        predicted = result["predicted_seconds_midpoint"]
        ratio = result["ratio"]
        click.echo(
            f"closed {prediction_id} — "
            f"elapsed {elapsed / 60:.1f} min, predicted {predicted / 60:.1f} min, ratio {ratio:.2f}x"
        )
        if ratio > 1.5:
            click.echo(
                f"  (underpredicted by {(ratio - 1) * 100:.0f}% — typical for me; pad next estimate)"
            )
        elif ratio < 0.7:
            click.echo("  (overpredicted — work was faster than expected)")

    @time_estimate_group.command("report")
    @click.option(
        "--limit",
        "-n",
        default=50,
        show_default=True,
        help="How many closed predictions to consider.",
    )
    def report_cmd(limit: int) -> None:
        """Calibration report: mean/median ratio + last 5 paired examples."""
        from divineos.core.time_calibration import get_calibration_report

        rep = get_calibration_report(limit=limit)
        if rep["sample_size"] == 0:
            click.echo("(no closed predictions yet — make some predictions, close them, come back)")
            return
        click.echo(f"=== calibration report (sample_size={rep['sample_size']}) ===")
        click.echo(f"  mean ratio (actual/predicted):   {rep['mean_ratio']:.2f}x")
        click.echo(f"  median ratio:                    {rep['median_ratio']:.2f}x")
        if rep["typical_underpredict_factor"]:
            click.echo(
                f"  multiply your gut estimate by ~{rep['typical_underpredict_factor']:.2f}x "
                "to get a calibrated value"
            )
        click.echo("")
        click.echo("  recent paired examples:")
        for ex in rep["examples"]:
            click.echo(
                f"    {ex['raw_text']:20s}  predicted={ex['predicted_midpoint_seconds'] / 60:5.1f}min  "
                f"actual={ex['actual_seconds'] / 60:5.1f}min  ratio={ex['ratio']:.2f}x"
            )
