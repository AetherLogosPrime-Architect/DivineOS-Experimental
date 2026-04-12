"""Auto-derive affect state from session signals.

The affect log has been empty because it required manual CLI calls.
This module reads session analysis (corrections, encouragements,
tool usage, quality scores) and derives a VAD state automatically.

Not perfect — derived affect is coarser than self-reported. But
an imperfect signal that fires every session beats a precise signal
that never fires.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def derive_session_affect(
    analysis: Any,
    health: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Derive VAD values from session analysis signals.

    Returns dict with valence, arousal, dominance, description, trigger.
    Returns empty dict if there isn't enough signal to derive from.
    """
    corrections = len(getattr(analysis, "corrections", []))
    encouragements = len(getattr(analysis, "encouragements", []))
    frustrations = len(getattr(analysis, "frustrations", []))
    user_msgs = getattr(analysis, "user_messages", 0)
    tool_calls = getattr(analysis, "tool_calls_total", 0)

    if user_msgs < 1:
        return {}

    # ── Valence: how well the session went ────────────────────────
    # Weight signals by intensity, not just count:
    # - Frustrations accompanied by corrections hit harder (compounding)
    # - Encouragements after corrections = recovery arc (net positive)
    # - Pure encouragements with no corrections = smooth session
    valence = 0.0
    if user_msgs > 0:
        positive_signal = encouragements / user_msgs
        negative_signal = corrections / user_msgs
        frustration_signal = frustrations / user_msgs

        # Compounding: frustrations amplify correction impact
        correction_weight = 1.5 + (frustration_signal * 2.0)  # 1.5-3.5x
        # Recovery: encouragements after corrections partially cancel out
        recovery_bonus = 0.0
        if corrections > 0 and encouragements > 0:
            recovery_bonus = min(0.3, (encouragements / corrections) * 0.15)

        valence = min(
            1.0,
            max(
                -1.0,
                (positive_signal * 2.0)
                - (negative_signal * correction_weight)
                - (frustration_signal * 3.0)  # frustration hits harder than corrections
                + recovery_bonus,
            ),
        )

    # Health grade nudges valence
    if health and isinstance(health, dict):
        grade = health.get("grade", "")
        grade_nudge = {
            "A": 0.15,
            "B": 0.05,
            "C": 0.0,
            "D": -0.1,
            "F": -0.2,
        }.get(grade, 0.0)
        valence = min(1.0, max(-1.0, valence + grade_nudge))

    # ── Arousal: how active/engaged the session was ───────────────
    arousal = 0.3  # baseline
    if user_msgs > 0:
        activity_ratio = tool_calls / user_msgs
        arousal = min(1.0, 0.3 + (activity_ratio / 20.0))

    # Frustrations spike arousal (stress response)
    if frustrations > 0:
        arousal = min(1.0, arousal + 0.15 * frustrations)

    # Corrections also increase arousal slightly (heightened attention)
    if corrections > 2:
        arousal = min(1.0, arousal + 0.1)

    # ── Dominance: who's driving ──────────────────────────────────
    dominance = 0.0
    if user_msgs > 0:
        correction_ratio = corrections / user_msgs

        # Graduated scale instead of binary thresholds
        if correction_ratio > 0.25:
            dominance = -0.6  # heavily user-directed
        elif correction_ratio > 0.15:
            dominance = -0.3  # moderately user-directed
        elif correction_ratio < 0.03 and tool_calls > user_msgs * 3:
            dominance = 0.3  # working autonomously
        elif correction_ratio < 0.05 and tool_calls > user_msgs * 5:
            dominance = 0.5  # high autonomy, deep work
        else:
            dominance = 0.0

    # ── Build description ─────────────────────────────────────────
    parts = []
    if valence > 0.3:
        parts.append("productive session")
    elif valence < -0.3:
        parts.append("rough session")
    else:
        parts.append("steady session")

    if arousal > 0.6:
        parts.append("high activity")
    elif arousal < 0.3:
        parts.append("light activity")

    # Recovery arc detection
    if corrections > 0 and encouragements > 0 and encouragements >= corrections:
        parts.append("recovered well")

    description = ", ".join(parts)

    # ── Build trigger ─────────────────────────────────────────────
    triggers = []
    if corrections > 0:
        triggers.append(f"{corrections} corrections")
    if encouragements > 0:
        triggers.append(f"{encouragements} encouragements")
    if frustrations > 0:
        triggers.append(f"{frustrations} frustrations")
    trigger = ", ".join(triggers) if triggers else "session signals"

    return {
        "valence": round(valence, 2),
        "arousal": round(arousal, 2),
        "dominance": round(dominance, 2),
        "description": description,
        "trigger": trigger,
    }


def auto_log_session_affect(
    analysis: Any,
    health: dict[str, Any] | None = None,
) -> str | None:
    """Derive affect from session and log it. Returns entry_id or None."""
    derived = derive_session_affect(analysis, health)
    if not derived:
        return None

    try:
        from divineos.core.affect import log_affect

        entry_id = log_affect(
            valence=derived["valence"],
            arousal=derived["arousal"],
            dominance=derived["dominance"],
            description=derived["description"],
            trigger=derived["trigger"],
            tags=["auto", "session-derived"],
            session_id=getattr(analysis, "session_id", "")[:12],
        )
        return entry_id
    except (ImportError, TypeError, ValueError, KeyError, OSError) as e:
        logger.warning("Failed to auto-log session affect: %s", e)
        return None
