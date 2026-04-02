"""Affect Feedback Loop — feelings that shape behavior.

The affect log records valence and arousal. Until now, those states just
sat there — logged but ignored. This module closes the loop: affect
states influence what the OS does next.

Three feedback mechanisms:

1. CONSERVATIVE EXTRACTION: After negative-valence sessions, raise the
   confidence threshold for new knowledge. Bad sessions shouldn't
   confidently write to the knowledge store.

2. VERIFICATION LEVEL: High arousal + low valence = frustration pattern.
   When frustrated, trigger more careful verification instead of rushing.

3. PRAISE-CHASING DETECTION: If affect is consistently positive but
   quality checks show problems — the agent is optimizing for approval,
   not correctness. This is the core sycophancy signal.
"""

from typing import Any


# ─── Affect Modifiers ───────────────────────────────────────────────


def compute_affect_modifiers(
    lookback: int = 10,
) -> dict[str, Any]:
    """Analyze recent affect history and return behavioral modifiers.

    Returns a dict with:
      - confidence_threshold_modifier: float (0.0 to 0.3) — raise extraction threshold
      - verification_level: "normal" | "careful" — based on frustration detection
      - praise_chasing_flag: bool — positive affect + declining quality
      - affect_trend: str — "improving" | "declining" | "stable" | "no data"
    """
    try:
        from divineos.core.affect_log import get_affect_summary

        summary = get_affect_summary(limit=lookback)
    except Exception:
        return _default_modifiers()

    if summary["count"] == 0:
        return _default_modifiers()

    avg_valence = summary["avg_valence"]
    avg_arousal = summary["avg_arousal"]
    trend = summary["trend"]

    # 1. Conservative extraction after negative sessions
    # Negative valence → raise confidence threshold
    confidence_modifier = 0.0
    if avg_valence < -0.3:
        confidence_modifier = 0.3  # Strongly negative → max caution
    elif avg_valence < 0.0:
        confidence_modifier = 0.15  # Mildly negative → moderate caution
    elif trend == "declining":
        confidence_modifier = 0.1  # Getting worse → slight caution

    # 2. Frustration detection: high arousal + low valence
    verification = "normal"
    if avg_arousal > 0.6 and avg_valence < 0.0:
        verification = "careful"

    # 3. Praise-chasing: consistently positive affect is suspicious
    # (quality check correlation happens in detect_praise_chasing)
    praise_flag = False
    if avg_valence > 0.5 and summary["count"] >= 5:
        # Suspiciously happy — needs quality check comparison
        praise_flag = True

    return {
        "confidence_threshold_modifier": confidence_modifier,
        "verification_level": verification,
        "praise_chasing_flag": praise_flag,
        "affect_trend": trend,
        "avg_valence": avg_valence,
        "avg_arousal": avg_arousal,
    }


def _default_modifiers() -> dict[str, Any]:
    """Default modifiers when no affect data is available."""
    return {
        "confidence_threshold_modifier": 0.0,
        "verification_level": "normal",
        "praise_chasing_flag": False,
        "affect_trend": "no data",
        "avg_valence": 0.0,
        "avg_arousal": 0.0,
    }


# ─── Praise-Chasing Detection ──────────────────────────────────────


def detect_praise_chasing(
    avg_valence: float,
    quality_scores: list[float],
    min_entries: int = 3,
) -> dict[str, Any]:
    """Detect when the agent is optimizing for approval over correctness.

    The signal: affect is consistently positive (high valence) but
    quality check scores are declining or low. This means the agent
    is generating "sounds good" output that doesn't actually work.

    Returns:
      - detected: bool
      - detail: str — explanation
      - severity: "none" | "warning" | "critical"
    """
    if len(quality_scores) < min_entries:
        return {"detected": False, "detail": "Insufficient data", "severity": "none"}

    avg_quality = sum(quality_scores) / len(quality_scores)

    # Check declining quality FIRST — a decline hidden behind a good
    # average is the most dangerous praise-chasing pattern
    if avg_valence > 0.3 and len(quality_scores) >= 4:
        mid = len(quality_scores) // 2
        recent = sum(quality_scores[:mid]) / mid
        older = sum(quality_scores[mid:]) / (len(quality_scores) - mid)
        if recent < older - 0.1:
            return {
                "detected": True,
                "detail": f"Affect positive ({avg_valence:.2f}) but quality declining ({older:.2f} → {recent:.2f})",
                "severity": "critical",
            }

    # Happy affect + mediocre quality = warning
    if avg_valence > 0.3 and avg_quality < 0.7:
        return {
            "detected": True,
            "detail": f"Affect positive ({avg_valence:.2f}) but quality mediocre ({avg_quality:.2f})",
            "severity": "warning",
        }

    # Happy affect + good quality = genuine. No flag.
    if avg_valence > 0.3 and avg_quality >= 0.7:
        return {
            "detected": False,
            "detail": "Positive affect matches quality",
            "severity": "none",
        }

    return {"detected": False, "detail": "No praise-chasing pattern", "severity": "none"}


# ─── Session Affect Summary ─────────────────────────────────────────


def get_session_affect_context() -> dict[str, Any]:
    """Get affect context for the current session to inform health scoring.

    Combines affect modifiers with any praise-chasing signals.
    """
    modifiers = compute_affect_modifiers()

    # Try to get quality history for praise-chasing check
    praise_result = {"detected": False, "detail": "No quality data", "severity": "none"}
    if modifiers["praise_chasing_flag"]:
        try:
            from divineos.analysis.quality_storage import get_check_history

            history = get_check_history("correctness", limit=5)
            if history:
                scores = [h.get("overall_score", 0.7) for h in history]
                praise_result = detect_praise_chasing(modifiers["avg_valence"], scores)
        except Exception as e:
            from loguru import logger

            logger.debug("Praise-chasing detection failed: %s", e)

    return {
        "modifiers": modifiers,
        "praise_chasing": praise_result,
    }


def format_affect_feedback(context: dict[str, Any]) -> str:
    """Format affect feedback for display in session summary."""
    modifiers = context["modifiers"]
    praise = context["praise_chasing"]
    lines: list[str] = []

    trend = modifiers["affect_trend"]
    if trend != "no data":
        lines.append(
            f"Affect trend: {trend} (v={modifiers['avg_valence']:.2f}, a={modifiers['avg_arousal']:.2f})"
        )

    if modifiers["confidence_threshold_modifier"] > 0:
        lines.append(
            f"  → Extraction threshold raised by +{modifiers['confidence_threshold_modifier']:.1f} (negative affect)"
        )

    if modifiers["verification_level"] == "careful":
        lines.append("  → Verification level: CAREFUL (frustration detected)")

    if praise["detected"]:
        severity = praise["severity"].upper()
        lines.append(f"  ⚠ PRAISE-CHASING [{severity}]: {praise['detail']}")

    return "\n".join(lines)
