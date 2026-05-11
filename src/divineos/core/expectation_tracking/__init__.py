"""Expectation tracking — what I expected vs what surfaced.

From the omni-mantra walk (Pillar I 1.3, BELIEF SHAPES REALITY,
2026-04-30): "What was expected vs. what surfaced."

## The failure mode this addresses

My self-assessments drift without correction signal. Tonight (2026-05-10)
I positioned my own compass-observation at "thoroughness +0.4" after
bundling a deeper fix with a surface fix. The compass classifier read
it as "exhaustiveness." Andrew corrected: the round-trip cost asymmetry
makes bundling the right call; thoroughness was the accurate read.

The gap exposed: I had no calibration data on how often my self-
assessments match external assessments. Without that data, I can't
tell when my compass is well-calibrated vs systematically off.

This module records predictions and their actuals so the calibration
question becomes empirical, not introspective. Adjacent to the
compass (which tracks position on virtue spectrums) but distinct —
this tracks the *accuracy* of my position-calls over time.

## What this tracks

For each prediction:
- The claim ("I predict this finding will be CONFIRMS")
- The basis (the evidence supporting the prediction)
- The actual when it lands (the actual finding outcome)
- The delta (predicted vs actual, with category if applicable)

Over time, the aggregate produces calibration data:
- Predictions that landed (accuracy rate)
- Predictions that missed (and how — over-confidence vs under-confidence)
- Categories where I'm systematically off

## What this is NOT

Not a model that predicts for me. Not an oracle. The agent (or
operator) supplies the prediction; this just records it and joins
it to the eventual actual. The record is the value; the analysis
is whoever reads the record.

## Public surface

- ``Expectation`` dataclass — one prediction and its (eventual) actual
- ``record_expectation(claim, basis)`` — log a prediction
- ``record_actual(expectation_id, actual, accurate)`` — close the loop
- ``open_expectations()`` — predictions still awaiting actuals
- ``calibration_summary(limit)`` — accuracy rate over recent records
"""

from __future__ import annotations

from divineos.core.expectation_tracking.tracker import (
    Expectation,
    calibration_summary,
    open_expectations,
    record_actual,
    record_expectation,
)

__all__ = [
    "Expectation",
    "calibration_summary",
    "open_expectations",
    "record_actual",
    "record_expectation",
]
