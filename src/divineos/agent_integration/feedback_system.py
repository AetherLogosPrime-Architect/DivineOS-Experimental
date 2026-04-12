"""Feedback System for Agent Integration.

Generates actionable feedback from real session analysis data.
Identifies tool performance issues, correction patterns, and generates
recommendations for the next session.
"""

from loguru import logger

from divineos.agent_integration.types import SessionFeedback
from divineos.core.knowledge import store_knowledge
import sqlite3

_FS_ERRORS = (ImportError, sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError)


def generate_session_feedback(analysis: object) -> SessionFeedback:
    """Generate feedback from a completed session's analysis.

    Args:
        analysis: SessionAnalysis object from session_analyzer

    Returns:
        SessionFeedback with tool usage, error patterns, and recommendations
    """
    session_id = getattr(analysis, "session_id", "unknown")
    tool_usage = getattr(analysis, "tool_usage", {})
    corrections = getattr(analysis, "corrections", [])
    encouragements = getattr(analysis, "encouragements", [])
    frustrations = getattr(analysis, "frustrations", [])
    tool_calls_total = getattr(analysis, "tool_calls_total", 0)

    logger.debug(f"Generating feedback for session {session_id[:8]}...")

    # Build error list from corrections
    errors = [c.content for c in corrections] if corrections else []

    # Build lessons from signals
    lessons = []
    if corrections:
        lessons.append(f"{len(corrections)} corrections -- areas where approach needed adjustment")
    if encouragements:
        lessons.append(f"{len(encouragements)} encouragements -- approaches that worked well")
    if frustrations:
        lessons.append(f"{len(frustrations)} frustrations -- user pain points to address")

    # Generate recommendations from real data
    recommendations = _generate_recommendations(
        tool_usage=tool_usage,
        corrections=corrections,
        encouragements=encouragements,
        frustrations=frustrations,
        tool_calls_total=tool_calls_total,
    )

    # Compute simple success rates per tool category
    success_rates = {}
    if tool_calls_total > 0:
        error_count = len(corrections)
        success_rates["overall"] = max(0.0, (tool_calls_total - error_count) / tool_calls_total)

    return SessionFeedback(
        session_id=session_id,
        tool_usage=tool_usage,
        success_rates=success_rates,
        timing={},
        errors=errors,
        lessons_learned=lessons,
        recommendations=recommendations,
        improvements=[e.content for e in encouragements] if encouragements else [],
        regressions=[f.content for f in frustrations] if frustrations else [],
    )


def _generate_recommendations(
    tool_usage: dict,
    corrections: list,
    encouragements: list,
    frustrations: list,
    tool_calls_total: int,
) -> list[str]:
    """Generate actionable recommendations from session data."""
    recommendations = []

    # High correction rate
    if corrections and tool_calls_total > 0:
        ratio = len(corrections) / tool_calls_total
        if ratio > 0.3:
            recommendations.append(
                f"High correction rate ({ratio:.0%}). "
                "Slow down, read more before writing, and verify assumptions."
            )
        elif ratio > 0.1:
            recommendations.append(
                f"Moderate correction rate ({ratio:.0%}). "
                "Consider reading existing code more carefully before making changes."
            )

    # Frustration patterns
    if frustrations:
        recommendations.append(
            f"{len(frustrations)} user frustrations detected. "
            "Review what caused them and adjust approach."
        )

    # Tool usage imbalance (writing way more than reading)
    reads = tool_usage.get("Read", 0) + tool_usage.get("Grep", 0) + tool_usage.get("Glob", 0)
    writes = tool_usage.get("Write", 0) + tool_usage.get("Edit", 0)
    if writes > 0 and reads < writes:
        recommendations.append(
            f"Read/write ratio is low ({reads}:{writes}). "
            "Read more before writing to reduce corrections."
        )

    # Encouragement patterns
    if encouragements and not corrections:
        recommendations.append("Clean session with positive feedback. Maintain this approach.")
    elif encouragements and corrections:
        recommendations.append(
            f"Mixed signals: {len(encouragements)} encouragements, "
            f"{len(corrections)} corrections. "
            "Focus on what earned the encouragements."
        )

    if not recommendations:
        recommendations.append("Session completed normally. No specific improvements needed.")

    return recommendations


def store_feedback_as_knowledge(
    session_id: str, feedback: SessionFeedback, session_tag: str
) -> str | None:
    """Store session feedback summary as a knowledge entry.

    Args:
        session_id: Session ID
        feedback: SessionFeedback object
        session_tag: Tag for deduplication

    Returns:
        Knowledge entry ID, or None on failure
    """
    try:
        recs = "; ".join(feedback.recommendations[:3])
        content = (
            f"Session feedback ({session_id[:8]}): "
            f"{len(feedback.errors)} errors, "
            f"{len(feedback.lessons_learned)} lessons. "
            f"Recs: {recs}"
        )

        entry_id = store_knowledge(
            knowledge_type="EPISODE",
            content=content,
            confidence=0.9,
            tags=["session-feedback", session_tag],
            source="SYNTHESIZED",
        )
        logger.debug(f"Stored feedback as knowledge: {entry_id[:8]}...")
        return entry_id
    except _FS_ERRORS as e:
        logger.warning(f"Failed to store feedback: {e}")
        return None
