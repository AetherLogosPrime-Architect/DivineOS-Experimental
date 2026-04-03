"""Goal Cull — Evidence-based staleness detection for goals.

Goals accumulate across sessions and many become stale without being
formally completed. This module checks each goal against the knowledge
store and decision journal to find evidence that the work was done,
and flags old goals that have no recent activity.
"""

import time
from typing import Any

# Goals older than this (in seconds) are candidates for culling
_STALENESS_THRESHOLD_DAYS = 3
_STALENESS_THRESHOLD = _STALENESS_THRESHOLD_DAYS * 86400


def _extract_goal_keywords(text: str) -> list[str]:
    """Extract meaningful keywords from a goal for searching."""
    # Strip common filler words
    filler = {
        "the",
        "a",
        "an",
        "to",
        "for",
        "of",
        "in",
        "on",
        "is",
        "it",
        "and",
        "or",
        "but",
        "with",
        "from",
        "that",
        "this",
        "lets",
        "let",
        "also",
        "as",
        "so",
        "we",
        "you",
        "i",
        "my",
        "our",
        "up",
        "all",
        "new",
        "old",
        "just",
        "well",
    }
    words = text.lower().replace("..", " ").replace(",", " ").split()
    keywords = [
        w.strip("'\"()[]") for w in words if w.strip("'\"()[]") not in filler and len(w) > 2
    ]
    return keywords[:8]  # cap at 8 to avoid noise


def _search_knowledge_for_goal(keywords: list[str]) -> list[str]:
    """Search knowledge store for entries matching goal keywords."""
    evidence: list[str] = []
    if not keywords:
        return evidence

    try:
        from divineos.core.memory import _get_connection

        conn = _get_connection()
        try:
            # Search for knowledge entries that mention goal keywords
            for kw in keywords[:4]:  # check top 4 keywords
                rows = conn.execute(
                    "SELECT knowledge_type, content FROM knowledge "
                    "WHERE superseded_by IS NULL AND content LIKE ? "
                    "LIMIT 2",
                    (f"%{kw}%",),
                ).fetchall()
                for row in rows:
                    snippet = row[1][:80].replace("\n", " ")
                    evidence.append(f"Knowledge [{row[0]}]: {snippet}")
        finally:
            conn.close()
    except Exception:  # noqa: BLE001
        pass

    # Deduplicate
    return list(dict.fromkeys(evidence))[:3]


def _search_decisions_for_goal(keywords: list[str]) -> list[str]:
    """Search decision journal for entries matching goal keywords."""
    evidence: list[str] = []
    if not keywords:
        return evidence

    try:
        from divineos.core.decision_journal import search_decisions

        for kw in keywords[:3]:
            results = search_decisions(kw, limit=2)
            for r in results:
                snippet = r["content"][:80]
                evidence.append(f"Decision: {snippet}")
    except Exception:  # noqa: BLE001
        pass

    return list(dict.fromkeys(evidence))[:3]


def assess_goal_staleness(goal: dict[str, Any], now: float | None = None) -> dict[str, Any]:
    """Assess whether a goal is stale and gather evidence.

    Returns:
        {
            "stale": bool,
            "age_days": int,
            "evidence": list[str],  # evidence of completion or staleness
            "reason": str,
        }
    """
    if now is None:
        now = time.time()

    added_at = goal.get("added_at", now)
    age_seconds = now - added_at
    age_days = int(age_seconds / 86400)

    text = goal.get("text", "")
    keywords = _extract_goal_keywords(text)

    # Check if goal is old enough to consider
    if age_seconds < _STALENESS_THRESHOLD:
        return {
            "stale": False,
            "age_days": age_days,
            "evidence": [],
            "reason": f"Goal is only {age_days} day(s) old",
        }

    # Search for evidence of completion
    knowledge_evidence = _search_knowledge_for_goal(keywords)
    decision_evidence = _search_decisions_for_goal(keywords)
    all_evidence = knowledge_evidence + decision_evidence

    if all_evidence:
        return {
            "stale": True,
            "age_days": age_days,
            "evidence": [f"Age: {age_days} days"] + all_evidence,
            "reason": "Old goal with related knowledge/decisions found",
        }

    # Old with no evidence — still stale, just no proof of completion
    return {
        "stale": True,
        "age_days": age_days,
        "evidence": [
            f"Age: {age_days} days",
            "No recent knowledge or decisions reference this goal",
        ],
        "reason": "Old goal with no related activity",
    }
