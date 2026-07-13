"""Brier-score calibration — the auditor's "by what measure does this work" answer.

Resolved claims (status in {SUPPORTED, CONTESTED, REFUTED}) carry both a
confidence-at-resolution and an outcome. Brier score sums (confidence - outcome)^2
across all resolved claims; perfect calibration = 0; "always says 50%" = 0.25;
> 0.25 is worse than that. Lower is better.

Per-bin calibration: bin predictions by confidence (0.0-0.1, 0.1-0.2, ...).
For each bin, what fraction of those claims actually resolved as supported?
A well-calibrated agent has the curve hugging the diagonal — predictions of
0.7 should land at ~70% support rate.

Excludes claims whose confidence_basis is 'uncommitted' or 'legacy-default' —
those aren't real credences (per the confidence_basis fix from prereg-b35f0d36cb2b).
Scoring against placeholders would lie about the calibration.

Born 2026-06-06 after the auditor's "purely anecdotal" critique. The
confidence_basis fix shipped today is the prerequisite — Brier scoring
against stuck-at-default placeholders would have produced noise. Now that
real credences exist (filer-prior, assessor-judgment, evidence-derived),
the calibration mechanism becomes meaningful.
"""

from __future__ import annotations

from typing import Any

from divineos.core.claim_store import (
    BASIS_LEGACY_DEFAULT,
    BASIS_UNCOMMITTED,
    STATUS_CONTESTED,
    STATUS_REFUTED,
    STATUS_SUPPORTED,
    _get_connection,
    init_claim_tables,
)

# Outcome encoding: SUPPORTED → 1.0 (claim turned out true), REFUTED → 0.0
# (claim turned out false), CONTESTED → 0.5 (neither cleanly true nor false,
# treated as the maximally-uncertain outcome). Matches the Brier-score
# convention used in forecasting (Tetlock GJP) where partial-resolution
# outcomes get scored against the midpoint.
_OUTCOME_FOR_STATUS = {
    STATUS_SUPPORTED: 1.0,
    STATUS_REFUTED: 0.0,
    STATUS_CONTESTED: 0.5,
}

# Confidence-basis values to EXCLUDE from scoring — these are placeholders,
# not real credences. Scoring against placeholders would lie about calibration.
_PLACEHOLDER_BASES = (BASIS_UNCOMMITTED, BASIS_LEGACY_DEFAULT)


def _resolved_claims_with_basis() -> list[dict[str, Any]]:
    """Resolved claims (SUPPORTED/CONTESTED/REFUTED) with non-placeholder basis.

    Returns list of dicts with keys: claim_id, confidence, status, basis,
    statement, created_at, updated_at, tier.
    """
    init_claim_tables()
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT claim_id, confidence, status, confidence_basis, statement, "
            "created_at, updated_at, tier "
            "FROM claims "
            "WHERE status IN (?, ?, ?) "
            "AND confidence_basis NOT IN (?, ?)",
            (
                STATUS_SUPPORTED,
                STATUS_CONTESTED,
                STATUS_REFUTED,
                BASIS_UNCOMMITTED,
                BASIS_LEGACY_DEFAULT,
            ),
        ).fetchall()
    finally:
        conn.close()
    return [
        {
            "claim_id": r[0],
            "confidence": r[1],
            "status": r[2],
            "basis": r[3],
            "statement": r[4],
            "created_at": r[5],
            "updated_at": r[6],
            "tier": r[7],
        }
        for r in rows
    ]


def brier_score() -> dict[str, Any]:
    """Compute overall Brier score across resolved claims with real credences.

    Returns dict with:
      - n: count of resolved claims scored
      - score: mean Brier score across them (lower better; 0 perfect; 0.25 = "always 50%")
      - placeholder_excluded: count of resolved claims excluded for placeholder basis
      - interpretation: human-readable string
    """
    claims = _resolved_claims_with_basis()
    n = len(claims)
    if n == 0:
        return {
            "n": 0,
            "score": None,
            "placeholder_excluded": _count_placeholder_resolved(),
            "interpretation": (
                "No resolved claims with real credences yet. "
                "File claims with --confidence and resolve them to start "
                "accumulating calibration data."
            ),
        }

    total = 0.0
    for c in claims:
        outcome = _OUTCOME_FOR_STATUS.get(c["status"], 0.5)
        total += (c["confidence"] - outcome) ** 2
    score = total / n

    if score < 0.05:
        interp = (
            "Excellent calibration. Predictions track outcomes tightly. "
            "Lower than typical superforecaster benchmarks (~0.15)."
        )
    elif score < 0.15:
        interp = (
            "Good calibration. In the range of trained forecasters. "
            "Predictions roughly match outcomes."
        )
    elif score < 0.25:
        interp = (
            "Moderate calibration. Predictions show some signal but "
            "with meaningful error. Room to tighten."
        )
    elif score == 0.25:
        interp = (
            "Calibration equivalent to 'always say 50%'. Predictions "
            "carry no real information about outcomes."
        )
    else:
        interp = (
            "Worse than 'always say 50%' — predictions are actively misleading. "
            "Probably systematically overconfident or underconfident."
        )

    return {
        "n": n,
        "score": round(score, 4),
        "placeholder_excluded": _count_placeholder_resolved(),
        "interpretation": interp,
    }


def _count_placeholder_resolved() -> int:
    """How many resolved claims got excluded because their basis is placeholder."""
    init_claim_tables()
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM claims WHERE status IN (?, ?, ?) AND confidence_basis IN (?, ?)",
            (
                STATUS_SUPPORTED,
                STATUS_CONTESTED,
                STATUS_REFUTED,
                BASIS_UNCOMMITTED,
                BASIS_LEGACY_DEFAULT,
            ),
        ).fetchone()
    finally:
        conn.close()
    return int(row[0]) if row else 0


def calibration_curve(bins: int = 10) -> list[dict[str, Any]]:
    """Per-bin calibration: for each confidence bin, what fraction resolved as supported?

    A well-calibrated agent has predicted-confidence == actual-support-rate
    within each bin (the curve hugs the diagonal).

    Returns list of dicts (one per bin) with keys:
      - bin_low: lower edge of confidence bin
      - bin_high: upper edge of confidence bin
      - n: count of claims in this bin
      - mean_confidence: average predicted confidence in this bin
      - mean_outcome: average outcome (1.0=supported, 0.0=refuted) in this bin
      - gap: mean_outcome - mean_confidence (positive = underconfident, negative = overconfident)
    """
    claims = _resolved_claims_with_basis()
    if not claims:
        return []

    bin_width = 1.0 / bins
    buckets: list[list[dict[str, Any]]] = [[] for _ in range(bins)]
    for c in claims:
        idx = min(int(c["confidence"] / bin_width), bins - 1)
        buckets[idx].append(c)

    result = []
    for i, bucket in enumerate(buckets):
        low = i * bin_width
        high = (i + 1) * bin_width if i < bins - 1 else 1.0
        if not bucket:
            result.append(
                {
                    "bin_low": round(low, 3),
                    "bin_high": round(high, 3),
                    "n": 0,
                    "mean_confidence": None,
                    "mean_outcome": None,
                    "gap": None,
                }
            )
            continue
        mean_conf = sum(c["confidence"] for c in bucket) / len(bucket)
        mean_outcome = sum(_OUTCOME_FOR_STATUS.get(c["status"], 0.5) for c in bucket) / len(bucket)
        result.append(
            {
                "bin_low": round(low, 3),
                "bin_high": round(high, 3),
                "n": len(bucket),
                "mean_confidence": round(mean_conf, 3),
                "mean_outcome": round(mean_outcome, 3),
                "gap": round(mean_outcome - mean_conf, 3),
            }
        )
    return result


def calibration_per_tier() -> dict[int, dict[str, Any]]:
    """Brier score sliced by claim tier. Returns dict {tier: {n, score, ...}}.

    Tier-level slicing reveals where my calibration is good vs bad.
    Tier 1 (empirical) should ideally calibrate tighter than Tier 5
    (metaphysical) — if not, that's data about a domain blind-spot.
    """
    claims = _resolved_claims_with_basis()
    if not claims:
        return {}

    by_tier: dict[int, list[dict[str, Any]]] = {}
    for c in claims:
        by_tier.setdefault(c["tier"], []).append(c)

    result = {}
    for tier, tier_claims in by_tier.items():
        total = 0.0
        for c in tier_claims:
            outcome = _OUTCOME_FOR_STATUS.get(c["status"], 0.5)
            total += (c["confidence"] - outcome) ** 2
        result[tier] = {
            "n": len(tier_claims),
            "score": round(total / len(tier_claims), 4),
        }
    return result


def historical_accuracy_at_confidence(
    confidence: float, tier: int | None = None, window: float = 0.1
) -> dict[str, Any]:
    """For pre-prediction anchoring: when I previously filed at confidence ~X
    in tier ~T, what's my actual support rate?

    The Dunning-Kruger anchor — surface this BEFORE a claim commits so I can
    see the gap between what I'm about to predict and what I've historically
    been right about at that confidence level.

    Returns dict with n, accuracy, and a comparison string. Accuracy is the
    fraction of similar past claims that resolved SUPPORTED (CONTESTED counts as 0.5).
    """
    init_claim_tables()
    conn = _get_connection()
    params: list[Any] = [
        STATUS_SUPPORTED,
        STATUS_CONTESTED,
        STATUS_REFUTED,
        BASIS_UNCOMMITTED,
        BASIS_LEGACY_DEFAULT,
        confidence - window,
        confidence + window,
    ]
    where_tier = ""
    if tier is not None:
        where_tier = "AND tier = ?"
        params.append(tier)
    try:
        rows = conn.execute(
            f"SELECT confidence, status FROM claims "
            f"WHERE status IN (?, ?, ?) "
            f"AND confidence_basis NOT IN (?, ?) "
            f"AND confidence BETWEEN ? AND ? "
            f"{where_tier}",  # nosec B608 — where_tier is a constant from this function only
            tuple(params),
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        return {
            "n": 0,
            "accuracy": None,
            "comparison": (
                f"No prior claims in the {confidence:.0%}±{window:.0%} confidence band"
                + (f" at tier {tier}" if tier else "")
                + ". No anchor available yet."
            ),
        }

    outcomes = [_OUTCOME_FOR_STATUS.get(r[1], 0.5) for r in rows]
    accuracy = sum(outcomes) / len(outcomes)

    # Compare anchor to the predicted confidence
    diff = abs(accuracy - confidence)
    if diff < 0.05:
        comp = f"You've been roughly {accuracy:.0%} accurate at this confidence — well-calibrated."
    elif accuracy < confidence:
        comp = (
            f"You've been {accuracy:.0%} accurate at this confidence band — "
            f"historically OVERCONFIDENT by {diff:.0%} on similar claims. "
            f"Consider lowering."
        )
    else:
        comp = (
            f"You've been {accuracy:.0%} accurate at this confidence band — "
            f"historically UNDERCONFIDENT by {diff:.0%} on similar claims. "
            f"You could raise."
        )

    return {
        "n": len(rows),
        "accuracy": round(accuracy, 3),
        "comparison": comp,
    }
