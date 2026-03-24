"""Outcome measurement — how well is the system actually working?

Measures real signals from the knowledge store, lesson tracking, and session
analysis to answer: are we learning, or are we spinning?

Four measurements:
- Rework: lessons that keep recurring without resolving
- Knowledge drift: entries that get superseded quickly (unstable knowledge)
- Correction rate: ratio of corrections to encouragements per session
- Session health: composite score from a session analysis
"""

import json
import re
import time
from typing import Any

from loguru import logger

from divineos.core.consolidation import (
    _get_connection,
    get_lessons,
)


def measure_rework(lookback_days: int = 30) -> list[dict[str, Any]]:
    """Find lessons that keep recurring without being resolved.

    A lesson is rework if:
    - status is still 'active' (not improving or resolved)
    - occurrences >= 3
    - appeared in multiple distinct sessions

    These are the things we keep messing up. They need attention.

    Returns:
        List of rework items, each with lesson details and a severity score.
        Sorted by severity (worst first).
    """
    lessons = get_lessons(status="active")
    rework: list[dict[str, Any]] = []

    cutoff = time.time() - (lookback_days * 86400)

    for lesson in lessons:
        if lesson["occurrences"] < 3:
            continue

        sessions = (
            json.loads(lesson["sessions"])
            if isinstance(lesson["sessions"], str)
            else lesson["sessions"]
        )
        if len(sessions) < 2:
            continue

        # Only count if it was seen recently
        if lesson["last_seen"] < cutoff:
            continue

        # Severity: more occurrences + more sessions = worse
        severity = lesson["occurrences"] * len(sessions)

        rework.append(
            {
                "lesson_id": lesson["lesson_id"],
                "category": lesson["category"],
                "description": lesson["description"],
                "occurrences": lesson["occurrences"],
                "session_count": len(sessions),
                "last_seen": lesson["last_seen"],
                "severity": severity,
            }
        )

    rework.sort(key=lambda x: x["severity"], reverse=True)
    logger.debug(f"Found {len(rework)} rework items in last {lookback_days} days")
    return rework


def measure_knowledge_drift(lookback_days: int = 14) -> dict[str, Any]:
    """Measure how stable our knowledge is.

    Looks at supersession patterns: if knowledge entries get superseded
    quickly after creation, it means we're storing things before they're
    settled. Stable knowledge doesn't get replaced.

    Returns:
        {
            "total_superseded": int,
            "avg_lifespan_hours": float,
            "short_lived": list[dict],  # entries that lasted < 24 hours
            "churn_rate": float,  # superseded / total active (0.0-1.0)
        }
    """
    conn = _get_connection()
    try:
        cutoff = time.time() - (lookback_days * 86400)

        # Entries that were superseded recently
        superseded = conn.execute(
            """SELECT k.knowledge_id, k.knowledge_type, k.content,
                      k.created_at, k.updated_at, k.superseded_by
               FROM knowledge k
               WHERE k.superseded_by IS NOT NULL
                 AND k.updated_at > ?
               ORDER BY k.updated_at DESC""",
            (cutoff,),
        ).fetchall()

        # Total active entries
        active_count = conn.execute(
            "SELECT COUNT(*) FROM knowledge WHERE superseded_by IS NULL",
        ).fetchone()[0]

        # Filter out manual cleanup supersessions from churn calculations.
        # These are quality improvements (removing noise), not real instability.
        # Organic supersessions (updates, contradictions) still count.
        _CLEANUP_MARKERS = (
            "Momentary",
            "Caught by noise",
            "Duplicate of",
            "Stale:",
            "Accidental",
            "Parsing artifact",
            "Momentary conversational",
            "Covered by existing",
            "Philosophy already",
            "User context already",
            "Question, not a",
            "Too short,",
        )
        organic_superseded = [
            row
            for row in superseded
            if not any(marker in str(row[5]) for marker in _CLEANUP_MARKERS)
        ]

        total_superseded = len(organic_superseded)
        churn_rate = total_superseded / max(active_count, 1)

        lifespans: list[float] = []
        short_lived: list[dict[str, Any]] = []

        for row in organic_superseded:
            kid, ktype, content, created_at, updated_at, _ = row
            lifespan_hours = (updated_at - created_at) / 3600

            lifespans.append(lifespan_hours)

            if lifespan_hours < 24:
                short_lived.append(
                    {
                        "knowledge_id": kid,
                        "knowledge_type": ktype,
                        "content": content[:100],
                        "lifespan_hours": round(lifespan_hours, 1),
                    }
                )

        avg_lifespan = sum(lifespans) / max(len(lifespans), 1)

        result = {
            "total_superseded": total_superseded,
            "avg_lifespan_hours": round(avg_lifespan, 1),
            "short_lived": short_lived[:10],
            "churn_rate": round(churn_rate, 3),
        }
        logger.debug(
            f"Knowledge drift: {total_superseded} superseded, "
            f"avg lifespan {avg_lifespan:.1f}h, churn {churn_rate:.1%}"
        )
        return result
    finally:
        conn.close()


def measure_correction_rate(session_id: str | None = None) -> dict[str, Any]:
    """Measure the ratio of corrections to encouragements.

    Uses the session analysis signals (corrections, encouragements) stored
    as EPISODE knowledge entries. A high correction rate means the user is
    spending energy fixing the AI instead of doing productive work.

    If session_id is given, measures just that session.
    Otherwise, measures across all sessions.

    Returns:
        {
            "corrections": int,
            "encouragements": int,
            "ratio": float,  # corrections / (corrections + encouragements), 0.0-1.0
            "assessment": str,  # "healthy", "mixed", or "struggling"
        }
    """
    conn = _get_connection()
    try:
        if session_id:
            tag = f"session-{session_id[:12]}"
            rows = conn.execute(
                """SELECT content FROM knowledge
                   WHERE knowledge_type = 'EPISODE'
                     AND superseded_by IS NULL
                     AND tags LIKE ?""",
                (f"%{tag}%",),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT content FROM knowledge
                   WHERE knowledge_type = 'EPISODE'
                     AND superseded_by IS NULL
                     AND tags LIKE '%session-analysis%'""",
            ).fetchall()

        total_corrections = 0
        total_encouragements = 0

        for (content,) in rows:
            corr_match = re.search(r"(\d+) correction", content)
            enc_match = re.search(r"(\d+) encouragement", content)
            if corr_match:
                total_corrections += int(corr_match.group(1))
            if enc_match:
                total_encouragements += int(enc_match.group(1))

        total = total_corrections + total_encouragements
        ratio = total_corrections / max(total, 1)

        if ratio < 0.3:
            assessment = "healthy"
        elif ratio < 0.6:
            assessment = "mixed"
        else:
            assessment = "struggling"

        result = {
            "corrections": total_corrections,
            "encouragements": total_encouragements,
            "ratio": round(ratio, 3),
            "assessment": assessment,
        }
        logger.debug(
            f"Correction rate: {total_corrections}c/{total_encouragements}e "
            f"= {ratio:.1%} ({assessment})"
        )
        return result
    finally:
        conn.close()


def measure_correction_trend(limit: int = 10) -> dict[str, Any]:
    """Show correction rate per session over time.

    Instead of just an aggregate, this shows the trajectory: are corrections
    going down (learning) or staying flat (stuck)?

    Returns:
        {
            "sessions": [{session_tag, corrections, encouragements, ratio}],
            "trend": "improving" | "stable" | "worsening" | "insufficient_data",
            "recent_avg": float,  # avg ratio of last 3 sessions
            "overall_avg": float,  # avg ratio of all sessions
        }
    """
    conn = _get_connection()
    try:
        rows = conn.execute(
            """SELECT content, created_at FROM knowledge
               WHERE knowledge_type = 'EPISODE'
                 AND superseded_by IS NULL
                 AND tags LIKE '%session-analysis%'
                 AND tags LIKE '%episode%'
               ORDER BY created_at ASC""",
        ).fetchall()

        sessions: list[dict[str, Any]] = []
        for content, created_at in rows:
            corr_match = re.search(r"(\d+) correction", content)
            enc_match = re.search(r"(\d+) encouragement", content)
            corr = int(corr_match.group(1)) if corr_match else 0
            enc = int(enc_match.group(1)) if enc_match else 0
            total = corr + enc
            ratio = corr / max(total, 1)

            # Extract session tag
            tag_match = re.search(r"Session (\w+):", content)
            tag = tag_match.group(1) if tag_match else "unknown"

            sessions.append(
                {
                    "session_tag": tag,
                    "corrections": corr,
                    "encouragements": enc,
                    "ratio": round(ratio, 3),
                    "created_at": created_at,
                }
            )

        sessions = sessions[-limit:]

        if len(sessions) < 2:
            trend = "insufficient_data"
            recent_avg = sessions[0]["ratio"] if sessions else 0.0
            overall_avg = recent_avg
        else:
            ratios = [s["ratio"] for s in sessions]
            overall_avg = sum(ratios) / len(ratios)
            recent = ratios[-3:] if len(ratios) >= 3 else ratios
            recent_avg = sum(recent) / len(recent)
            earlier = ratios[: len(ratios) // 2]
            later = ratios[len(ratios) // 2 :]
            earlier_avg = sum(earlier) / max(len(earlier), 1)
            later_avg = sum(later) / max(len(later), 1)

            if later_avg < earlier_avg - 0.1:
                trend = "improving"
            elif later_avg > earlier_avg + 0.1:
                trend = "worsening"
            else:
                trend = "stable"

        return {
            "sessions": sessions,
            "trend": trend,
            "recent_avg": round(recent_avg, 3),
            "overall_avg": round(overall_avg, 3),
        }
    finally:
        conn.close()


def measure_session_health(
    corrections: int,
    encouragements: int,
    context_overflows: int,
    tool_calls: int,
    user_messages: int,
) -> dict[str, Any]:
    """Score a session's health from its analysis signals.

    Produces a 0.0-1.0 composite score:
    - Correction penalty: more corrections = lower score
    - Encouragement bonus: user approval signal
    - Overflow penalty: hitting context limits means inefficiency
    - Interaction ratio: tool_calls / user_messages (higher = more autonomous)

    Args:
        corrections: Number of user corrections detected
        encouragements: Number of user encouragements detected
        context_overflows: Number of context window overflows
        tool_calls: Total tool calls in session
        user_messages: Total user messages in session

    Returns:
        {
            "score": float,  # 0.0-1.0
            "grade": str,  # A/B/C/D/F
            "factors": dict,  # breakdown of each factor
        }
    """
    factors: dict[str, float] = {}

    # Correction penalty (0.0 = many corrections, 1.0 = none)
    correction_factor = max(0.0, 1.0 - (corrections * 0.15))
    factors["corrections"] = round(correction_factor, 2)

    # Encouragement bonus (caps at 0.2 extra)
    encouragement_factor = min(0.2, encouragements * 0.04)
    factors["encouragements"] = round(encouragement_factor, 2)

    # Overflow penalty (each overflow is a sign of inefficiency)
    overflow_factor = max(0.0, 1.0 - (context_overflows * 0.25))
    factors["overflows"] = round(overflow_factor, 2)

    # Autonomy: tool_calls per user message (more = more autonomous)
    if user_messages > 0:
        autonomy = min(1.0, (tool_calls / user_messages) / 10.0)
    else:
        autonomy = 0.5
    factors["autonomy"] = round(autonomy, 2)

    # Composite: weighted average
    score = (
        correction_factor * 0.35 + encouragement_factor + overflow_factor * 0.25 + autonomy * 0.20
    )
    score = max(0.0, min(1.0, score))

    if score >= 0.85:
        grade = "A"
    elif score >= 0.70:
        grade = "B"
    elif score >= 0.55:
        grade = "C"
    elif score >= 0.40:
        grade = "D"
    else:
        grade = "F"

    result = {
        "score": round(score, 2),
        "grade": grade,
        "factors": factors,
    }
    logger.debug(f"Session health: {score:.2f} ({grade})")
    return result
