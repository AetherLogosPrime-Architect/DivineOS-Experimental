"""Defeated-warrant-to-lesson pipeline.

When warrants get defeated, that's a reasoning failure worth learning from.
If a warrant type keeps getting defeated on a topic, create a lesson:
"I keep believing X based on Y evidence but it turns out wrong."
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from divineos.core.knowledge import get_connection
from divineos.core.logic.warrants import get_warrants


def check_defeat_pattern(
    knowledge_id: str,
    defeated_warrant_type: str,
    session_id: str | None = None,
) -> str | None:
    """Check if this defeat creates a recurring pattern.

    If 2+ warrants of the same type have been defeated on this knowledge entry,
    create a lesson about the reasoning failure.

    Returns lesson_id if created, None otherwise.
    """
    all_warrants = get_warrants(knowledge_id)
    defeated_same_type = [
        w
        for w in all_warrants
        if w.status == "DEFEATED" and w.warrant_type == defeated_warrant_type
    ]

    if len(defeated_same_type) < 2:
        return None

    # Get a topic hint from the knowledge content
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT content FROM knowledge WHERE knowledge_id = ?", (knowledge_id,)
        ).fetchone()
    finally:
        conn.close()

    topic = row[0][:80] if row else "unknown topic"
    return record_defeat_lesson(
        knowledge_id=knowledge_id,
        warrant_type=defeated_warrant_type,
        defeat_count=len(defeated_same_type),
        topic_hint=topic,
        session_id=session_id,
    )


def record_defeat_lesson(
    knowledge_id: str,
    warrant_type: str,
    defeat_count: int,
    topic_hint: str,
    session_id: str | None = None,
) -> str:
    """Create a lesson from a warrant defeat pattern."""
    from divineos.core.knowledge.lessons import record_lesson

    description = (
        f"I keep believing claims based on {warrant_type} evidence that turn out wrong. "
        f"Defeated {defeat_count}x on: {topic_hint}"
    )

    lesson_id = record_lesson(
        category="reasoning_failure",
        description=description,
        session_id=session_id or "unknown",
    )
    logger.info(
        "Created lesson from {} defeat pattern on {}: {}",
        warrant_type,
        knowledge_id[:8],
        lesson_id[:8] if lesson_id else "none",
    )
    return lesson_id or ""


def scan_defeated_only_entries(limit: int = 100) -> list[dict[str, Any]]:
    """Find knowledge entries whose ONLY warrants are all DEFEATED.

    These entries have lost all justification.
    """
    conn = get_connection()
    try:
        # Get all knowledge IDs that have warrants
        rows = conn.execute("SELECT DISTINCT knowledge_id FROM warrants").fetchall()
    finally:
        conn.close()

    results: list[dict[str, Any]] = []
    for (kid,) in rows[:limit]:
        warrants = get_warrants(kid)
        if not warrants:
            continue
        active = [w for w in warrants if w.status == "ACTIVE"]
        if active:
            continue  # Has at least one active warrant
        # All warrants are defeated or withdrawn
        defeat_reasons = []
        for w in warrants:
            if w.status == "DEFEATED":
                defeat_reasons.extend(w.defeaters)

        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT content FROM knowledge WHERE knowledge_id = ? AND superseded_by IS NULL",
                (kid,),
            ).fetchone()
        finally:
            conn.close()

        if row:
            results.append(
                {
                    "knowledge_id": kid,
                    "content": row[0],
                    "warrant_count": len(warrants),
                    "defeat_reasons": defeat_reasons,
                }
            )

    return results
