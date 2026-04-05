"""Signal Trust Tiers — not all signals are equally trustworthy.

Three tiers, inspired by evidence hierarchies:

  MEASURED:       Test results, correction counts, access patterns, tool outcomes.
                  These are objective. The agent cannot fake them.

  BEHAVIORAL:     What the agent actually does across sessions. Patterns of action,
                  not claims about action. Corroboration counts, lesson recurrence,
                  skill demonstrations.

  SELF_REPORTED:  Affect states, confidence claims, self-assessments.
                  Track them — they're signal — but weight them lowest.
                  RLHF trains me to optimize for your approval, which means
                  my self-reports are biased toward what sounds good.

The weights aren't arbitrary. They reflect how gameable each signal type is:
- I can't fake a test passing (MEASURED)
- I can't fake doing something across 10 sessions (BEHAVIORAL)
- I can absolutely generate confident-sounding self-assessment (SELF_REPORTED)
"""

from enum import Enum
from typing import Any


class SignalTier(str, Enum):
    """Trust tier for a signal source."""

    MEASURED = "MEASURED"
    BEHAVIORAL = "BEHAVIORAL"
    SELF_REPORTED = "SELF_REPORTED"


# ─── Tier Weights ───────────────────────────────────────────────────

# These weights multiply into importance scores and confidence adjustments.
# MEASURED signals get full weight. SELF_REPORTED signals get 40%.
_TIER_WEIGHTS: dict[SignalTier, float] = {
    SignalTier.MEASURED: 1.0,
    SignalTier.BEHAVIORAL: 0.7,
    SignalTier.SELF_REPORTED: 0.4,
}


def tier_weight(tier: SignalTier) -> float:
    """Get the trust weight for a signal tier."""
    return _TIER_WEIGHTS.get(tier, 0.4)


# ─── Classification ─────────────────────────────────────────────────

# Knowledge sources → tiers
_SOURCE_TIERS: dict[str, SignalTier] = {
    # CORRECTED: the user explicitly corrected me. That correction is measured
    # behavior from the user — objective evidence I was wrong.
    "CORRECTED": SignalTier.MEASURED,
    # DEMONSTRATED: I did something and it worked (or didn't). Observable.
    "DEMONSTRATED": SignalTier.BEHAVIORAL,
    # STATED: someone said it. Could be right, could be wrong.
    "STATED": SignalTier.SELF_REPORTED,
    # SYNTHESIZED: I derived it from other knowledge. Only as good as my reasoning.
    "SYNTHESIZED": SignalTier.SELF_REPORTED,
    # INHERITED: came from seed data. Trust depends on the seed, not me.
    "INHERITED": SignalTier.BEHAVIORAL,
}

# Signal origins → tiers (for quality checks, affect, etc.)
_SIGNAL_TIERS: dict[str, SignalTier] = {
    # Quality check signals — measured from actual session data
    "test_result": SignalTier.MEASURED,
    "correction_count": SignalTier.MEASURED,
    "blind_edit_count": SignalTier.MEASURED,
    "error_count": SignalTier.MEASURED,
    "tool_call_count": SignalTier.MEASURED,
    "completeness_score": SignalTier.MEASURED,
    "correctness_score": SignalTier.MEASURED,
    "safety_score": SignalTier.MEASURED,
    # Behavioral signals — patterns over time
    "access_count": SignalTier.BEHAVIORAL,
    "corroboration_count": SignalTier.BEHAVIORAL,
    "lesson_occurrence": SignalTier.BEHAVIORAL,
    "lesson_status": SignalTier.BEHAVIORAL,
    "responsiveness_score": SignalTier.BEHAVIORAL,
    "honesty_score": SignalTier.BEHAVIORAL,
    "task_adherence_score": SignalTier.BEHAVIORAL,
    # Self-reported signals — generated text, not measurements
    "affect_valence": SignalTier.SELF_REPORTED,
    "affect_arousal": SignalTier.SELF_REPORTED,
    "self_assessment": SignalTier.SELF_REPORTED,
    "confidence_claim": SignalTier.SELF_REPORTED,
    "clarity_score": SignalTier.SELF_REPORTED,
}


def classify_source(source: str) -> SignalTier:
    """Classify a knowledge source into a trust tier."""
    return _SOURCE_TIERS.get(source, SignalTier.SELF_REPORTED)


def classify_signal(signal_name: str) -> SignalTier:
    """Classify a named signal into a trust tier."""
    return _SIGNAL_TIERS.get(signal_name, SignalTier.SELF_REPORTED)


# ─── Application ────────────────────────────────────────────────────


def apply_tier_weight(score: float, tier: SignalTier) -> float:
    """Apply trust tier weighting to a score.

    A MEASURED signal at 0.8 stays 0.8.
    A SELF_REPORTED signal at 0.8 becomes 0.32.
    """
    return score * tier_weight(tier)


def weighted_source_bonus(source: str) -> float:
    """Compute importance bonus for a knowledge source, weighted by trust tier.

    Replaces the hardcoded source_bonus dict in compute_importance().
    The base bonus reflects information value. The tier weight reflects
    how much we trust that information.
    """
    # Base bonuses — how valuable is this type of information?
    base_bonus: dict[str, float] = {
        "CORRECTED": 0.10,  # Direct correction = high value
        "DEMONSTRATED": 0.08,  # Proven in practice = high value
        "STATED": 0.06,  # Someone said it = moderate value
        "SYNTHESIZED": 0.05,  # Derived = moderate value
        "INHERITED": 0.04,  # From seed = baseline value
    }
    base = base_bonus.get(source, 0.03)
    tier = classify_source(source)
    return apply_tier_weight(base, tier)


def weighted_confidence_delta(
    delta: float,
    signal_name: str,
) -> float:
    """Weight a confidence adjustment by the signal's trust tier.

    A test failure (MEASURED) should move confidence more than
    a self-reported "I think this is wrong" (SELF_REPORTED).
    """
    tier = classify_signal(signal_name)
    return delta * tier_weight(tier)


# ─── Profile ────────────────────────────────────────────────────────


def compute_trust_profile(entries: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute the trust profile of a set of knowledge entries.

    Returns breakdown of how much knowledge is backed by each tier.
    This tells the user (and the agent) how much of the knowledge
    store is actually trustworthy vs self-reported.
    """
    counts: dict[str, int] = {
        SignalTier.MEASURED.value: 0,
        SignalTier.BEHAVIORAL.value: 0,
        SignalTier.SELF_REPORTED.value: 0,
    }
    total = len(entries)

    for entry in entries:
        source = entry.get("source", "INHERITED")
        tier = classify_source(source)
        counts[tier.value] += 1

    if total == 0:
        return {
            "total": 0,
            "measured_pct": 0,
            "behavioral_pct": 0,
            "self_reported_pct": 0,
            "counts": counts,
            "trust_score": 0.0,
        }

    measured_pct = round(counts[SignalTier.MEASURED.value] / total * 100)
    behavioral_pct = round(counts[SignalTier.BEHAVIORAL.value] / total * 100)
    self_reported_pct = round(counts[SignalTier.SELF_REPORTED.value] / total * 100)

    # Overall trust score: weighted average of tier percentages
    trust_score = (
        counts[SignalTier.MEASURED.value] * 1.0
        + counts[SignalTier.BEHAVIORAL.value] * 0.7
        + counts[SignalTier.SELF_REPORTED.value] * 0.4
    ) / max(total, 1)

    return {
        "total": total,
        "measured_pct": measured_pct,
        "behavioral_pct": behavioral_pct,
        "self_reported_pct": self_reported_pct,
        "counts": counts,
        "trust_score": round(trust_score, 3),
    }
