"""Pattern Anticipation — proactive warnings based on current context.

Instead of passively listing past mistakes, this module matches what
I'm currently doing against what's gone wrong before. If the context
I'm working in resembles a past correction or recurring lesson,
I should know about it before I repeat it.
"""

import re
from typing import Any

from divineos.core.knowledge._base import _get_connection
from divineos.core.knowledge._text import _compute_overlap


def _get_active_warnings() -> list[dict[str, Any]]:
    """Get lessons and MISTAKE/BOUNDARY knowledge that could be relevant warnings."""
    conn = _get_connection()
    try:
        # Active and improving lessons with 2+ occurrences
        lessons = conn.execute(
            "SELECT lesson_id, category, description, occurrences, status "
            "FROM lesson_tracking WHERE occurrences >= 2 "
            "ORDER BY occurrences DESC LIMIT 20"
        ).fetchall()

        # MISTAKE and BOUNDARY knowledge with decent confidence
        mistakes = conn.execute(
            "SELECT knowledge_id, knowledge_type, content, confidence "
            "FROM knowledge "
            "WHERE knowledge_type IN ('MISTAKE', 'BOUNDARY') "
            "AND superseded_by IS NULL AND confidence >= 0.4 "
            "ORDER BY confidence DESC LIMIT 20"
        ).fetchall()
    finally:
        conn.close()

    warnings: list[dict[str, Any]] = []
    for row in lessons:
        warnings.append(
            {
                "source": "lesson",
                "id": row[0],
                "category": row[1],
                "text": row[2],
                "occurrences": row[3],
                "status": row[4],
                "weight": row[3] * 0.3,  # base weight from recurrence
            }
        )
    for row in mistakes:
        warnings.append(
            {
                "source": "knowledge",
                "id": row[0],
                "type": row[1],
                "text": row[2],
                "confidence": row[3],
                "weight": row[3] * 0.2,  # base weight from confidence
            }
        )
    return warnings


def anticipate(context: str, max_warnings: int = 5) -> list[dict[str, Any]]:
    """Match current context against past mistakes and lessons.

    Takes a context string (what I'm currently doing or asking about)
    and returns relevant warnings ranked by relevance.

    Each warning has: text, relevance (0-1), source, reason.
    """
    if not context or not context.strip():
        return []

    warnings = _get_active_warnings()
    if not warnings:
        return []

    context_lower = context.lower()
    context_words = set(re.findall(r"\b\w{3,}\b", context_lower))

    scored: list[dict[str, Any]] = []

    for warning in warnings:
        text = warning["text"]
        overlap = _compute_overlap(context, text)

        # Word-level matching for category names
        category_match = 0.0
        if "category" in warning:
            cat_words = set(warning["category"].replace("_", " ").split())
            if cat_words & context_words:
                category_match = 0.3

        # Boost for specific high-signal words in the warning
        text_lower = text.lower()
        signal_boost = 0.0
        for word in context_words:
            if len(word) > 4 and word in text_lower:
                signal_boost += 0.1
        signal_boost = min(signal_boost, 0.3)

        relevance = overlap + category_match + signal_boost + warning["weight"]

        if relevance >= 0.3:
            reason_parts = []
            if overlap >= 0.3:
                reason_parts.append(f"content overlap ({overlap:.0%})")
            if category_match > 0:
                reason_parts.append("category match")
            if signal_boost > 0:
                reason_parts.append("keyword match")

            scored.append(
                {
                    "text": text,
                    "relevance": min(relevance, 1.0),
                    "source": warning["source"],
                    "reason": ", ".join(reason_parts) if reason_parts else "base relevance",
                    "occurrences": warning.get("occurrences", 0),
                    "id": warning["id"],
                }
            )

    scored.sort(key=lambda w: w["relevance"], reverse=True)
    return scored[:max_warnings]


def format_anticipation(warnings: list[dict[str, Any]]) -> str:
    """Format anticipation warnings for display."""
    if not warnings:
        return ""

    lines = ["**Watch out:**"]
    for w in warnings:
        icon = "!!" if w["relevance"] >= 0.6 else "!"
        occ = f" ({w['occurrences']}x)" if w.get("occurrences", 0) >= 2 else ""
        lines.append(f"  [{icon}] {w['text'][:150]}{occ}")
        lines.append(f"       why: {w['reason']}")
    return "\n".join(lines)
