"""Session Quality Trending — tracks trajectory across sessions.

Analyzes the last N session episodes to determine if quality is
improving, declining, or stable. Provides a summary for the HUD
so the agent knows its trajectory at a glance.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SessionTrend:
    """Quality trend across recent sessions."""

    direction: str  # "improving", "declining", "stable"
    sessions_analyzed: int
    avg_corrections: float
    avg_encouragements: float
    detail: str


def get_session_trend(n: int = 5) -> SessionTrend:
    """Analyze the last N session episodes for quality trajectory.

    Looks at EPISODE entries which contain corrections and encouragements
    counts from each session.
    """
    from divineos.core.consolidation import get_knowledge

    episodes = get_knowledge(knowledge_type="EPISODE", limit=n * 2)

    # Filter to actual session episodes (contain "exchanges" and "corrected")
    session_episodes = [
        e
        for e in episodes
        if "exchanges" in e.get("content", "") and "corrected" in e.get("content", "")
    ][:n]

    if len(session_episodes) < 2:
        return SessionTrend(
            direction="stable",
            sessions_analyzed=len(session_episodes),
            avg_corrections=0.0,
            avg_encouragements=0.0,
            detail="Not enough sessions for trend analysis.",
        )

    # Parse corrections and encouragements from episode content
    corrections_list: list[int] = []
    encouragements_list: list[int] = []

    for ep in session_episodes:
        content = ep.get("content", "")
        corrections = _extract_count(content, "corrected")
        encouragements = _extract_count(content, "encouraged")
        corrections_list.append(corrections)
        encouragements_list.append(encouragements)

    avg_corr = sum(corrections_list) / len(corrections_list)
    avg_enc = sum(encouragements_list) / len(encouragements_list)

    # Split into halves: episodes are sorted newest-first
    # So first half = newer sessions, second half = older sessions
    mid = len(corrections_list) // 2
    newer_corr = sum(corrections_list[:mid]) / max(1, mid)
    older_corr = sum(corrections_list[mid:]) / max(1, len(corrections_list) - mid)

    newer_enc = sum(encouragements_list[:mid]) / max(1, mid)
    older_enc = sum(encouragements_list[mid:]) / max(1, len(encouragements_list) - mid)

    # Determine direction
    # Fewer corrections + more encouragements = improving
    corr_change = newer_corr - older_corr
    enc_change = newer_enc - older_enc

    if corr_change < -0.5 or enc_change > 0.5:
        direction = "improving"
        detail = "Fewer corrections and/or more encouragements in recent sessions."
    elif corr_change > 0.5 or enc_change < -0.5:
        direction = "declining"
        detail = "More corrections and/or fewer encouragements in recent sessions."
    else:
        direction = "stable"
        detail = "Quality metrics are consistent across recent sessions."

    return SessionTrend(
        direction=direction,
        sessions_analyzed=len(session_episodes),
        avg_corrections=avg_corr,
        avg_encouragements=avg_enc,
        detail=detail,
    )


def _extract_count(content: str, keyword: str) -> int:
    """Extract a count from episode content like 'corrected 3 times'."""
    import re

    pattern = rf"{keyword}\s+(\d+)\s+time"
    match = re.search(pattern, content)
    if match:
        return int(match.group(1))
    return 0


def format_trend_summary(trend: SessionTrend) -> str:
    """Format trend for HUD display."""
    icons = {"improving": "[+]", "declining": "[!]", "stable": "[~]"}
    icon = icons.get(trend.direction, "[~]")

    parts = [f"{icon} Trend: {trend.direction}"]
    if trend.sessions_analyzed >= 2:
        parts.append(
            f"(avg {trend.avg_corrections:.1f} corrections, "
            f"{trend.avg_encouragements:.1f} encouragements "
            f"across {trend.sessions_analyzed} sessions)"
        )

    return " ".join(parts)
