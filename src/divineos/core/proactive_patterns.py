"""Proactive Pattern Detection — prescriptive recommendations from experience.

Complements anticipation.py (which warns about past mistakes) by
recommending patterns that worked well in similar contexts. Instead of
just "watch out for X," this says "last time you did something like
this, Y worked well."

Sources recommendations from:
1. Knowledge store (PRINCIPLE, PROCEDURE entries with high confidence)
2. Decision journal (decisions with positive outcomes in similar contexts)
3. Opinion store (relevant opinions with high confidence)

Sanskrit anchor: prajna (wisdom, practical insight applied to action).
"""

import re
import sqlite3
import time
import uuid
from typing import Any

from loguru import logger

from divineos.core.constants import (
    PATTERN_ARCHIVE_THRESHOLD,
    PATTERN_FAILURE_DELTA,
    PATTERN_SUCCESS_DELTA,
    PATTERN_TACTICAL_FAILURE_MAX,
)
from divineos.core.knowledge import get_connection
from divineos.core.knowledge._text import _compute_overlap, _is_extraction_noise

_PP_ERRORS = (ImportError, sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError)

# Conversational openers that indicate raw user quotes, not actionable knowledge.
# These entries slipped in before the extraction noise filter existed.
_LEGACY_NOISE_OPENERS = re.compile(
    r"^(yes |ok |oh |well |wonderful |it still |both fixes |auto memories |"
    r"absolutely |here is |heres |here's |the audit was |this is what )",
    re.IGNORECASE,
)
# The literal 'andrew,' opener was removed per fresh-Claude audit round 2
# Finding 2 (blank-slate cleanup): personal-name patterns in regex are
# dead code for non-Andrew instances and a trust-hygiene cost for the
# public skill library that ships this module.

# Noise anywhere in content — conversational artifacts that shouldn't be recommendations
_LEGACY_NOISE_MARKERS = re.compile(
    r"(claude said|what me and claude|what claude and i|i told claude|claude told me)",
    re.IGNORECASE,
)


def _is_recommendation_noise(content: str, knowledge_type: str) -> bool:
    """Check if a knowledge entry is too noisy to recommend as a TRY pattern.

    Uses the extraction noise filter plus additional checks for entries
    that slipped through before the filter existed.
    """
    if _is_extraction_noise(content, knowledge_type):
        return True

    # Legacy entries: raw user quotes that start with conversational openers
    if _LEGACY_NOISE_OPENERS.match(content.strip()):
        return True

    # Conversational artifacts anywhere in the content
    if _LEGACY_NOISE_MARKERS.search(content):
        return True

    return False


def _get_positive_patterns() -> list[dict[str, Any]]:
    """Collect patterns that worked well — principles, procedures, high-confidence knowledge."""
    patterns: list[dict[str, Any]] = []

    conn = get_connection()
    try:
        knowledge_rows = conn.execute(
            "SELECT knowledge_id, knowledge_type, content, confidence, access_count "
            "FROM knowledge "
            "WHERE knowledge_type IN ('PRINCIPLE', 'PROCEDURE', 'OBSERVATION') "
            "AND superseded_by IS NULL AND confidence >= 0.6 "
            "ORDER BY confidence DESC, access_count DESC LIMIT 30"
        ).fetchall()
        for row in knowledge_rows:
            # Skip entries that are conversational noise (pre-filter legacy)
            if _is_recommendation_noise(row[2], row[1]):
                continue
            patterns.append(
                {
                    "source": "knowledge",
                    "id": row[0],
                    "type": row[1],
                    "text": row[2],
                    "confidence": row[3],
                    "access_count": row[4],
                    "weight": min(row[3] * 0.15, 0.2),
                }
            )
    except sqlite3.OperationalError:
        pass
    finally:
        conn.close()

    # Add opinions if available
    try:
        from divineos.core.opinion_store import get_opinions, init_opinion_table

        init_opinion_table()
        opinions = get_opinions(min_confidence=0.6, limit=15)
        for op in opinions:
            patterns.append(
                {
                    "source": "opinion",
                    "id": op["opinion_id"],
                    "type": "OPINION",
                    "text": f"[{op['topic']}] {op['position']}",
                    "confidence": op["confidence"],
                    "access_count": 0,
                    "weight": op["confidence"] * 0.2,
                }
            )
    except _PP_ERRORS:
        pass

    # Add successful advice — recommendations that actually worked
    try:
        from divineos.core.advice_tracking import init_advice_table

        init_advice_table()
        aconn = get_connection()
        try:
            advice_rows = aconn.execute(
                "SELECT advice_id, content, category FROM advice_tracking "
                "WHERE outcome = 'successful' "
                "ORDER BY assessed_at DESC LIMIT 15"
            ).fetchall()
        finally:
            aconn.close()
        for row in advice_rows:
            patterns.append(
                {
                    "source": "advice",
                    "id": row[0],
                    "type": "ADVICE",
                    "text": f"[{row[2]}] {row[1]}",
                    "confidence": 0.85,  # proven successful
                    "access_count": 0,
                    "weight": 0.35,  # higher weight — empirically validated
                }
            )
    except _PP_ERRORS:
        pass

    # Add positive decisions if available
    try:
        from divineos.core.decision_journal import init_decision_journal

        init_decision_journal()
        dconn = get_connection()
        try:
            decision_rows = dconn.execute(
                "SELECT decision_id, content, tension FROM decision_journal "
                "WHERE tension != '' ORDER BY created_at DESC LIMIT 20"
            ).fetchall()
        finally:
            dconn.close()
        for row in decision_rows:
            patterns.append(
                {
                    "source": "decision",
                    "id": row[0],
                    "type": "DECISION",
                    "text": row[1],
                    "confidence": 0.6,
                    "access_count": 0,
                    "weight": 0.15,
                }
            )
    except _PP_ERRORS:
        pass

    return patterns


def recommend(context: str, max_recommendations: int = 3) -> list[dict[str, Any]]:
    """Match current context against positive patterns and recommend applicable ones.

    Returns recommendations ranked by relevance. Each has:
    text, relevance (0-1), source, type, reason.
    """
    if not context or not context.strip():
        return []

    patterns = _get_positive_patterns()
    if not patterns:
        return []

    context_lower = context.lower()
    context_words = set(re.findall(r"\b\w{3,}\b", context_lower))

    scored: list[dict[str, Any]] = []

    for pattern in patterns:
        text = pattern["text"]
        overlap = _compute_overlap(context, text)

        # Keyword signal boost
        text_lower = text.lower()
        signal_boost = 0.0
        for word in context_words:
            if len(word) > 4 and word in text_lower:
                signal_boost += 0.1
        signal_boost = min(signal_boost, 0.3)

        # Frequently accessed patterns are more likely useful
        access_boost = min(pattern.get("access_count", 0) * 0.01, 0.1)

        relevance = overlap + signal_boost + pattern["weight"] + access_boost

        if relevance >= 0.3:
            reason_parts = []
            if overlap >= 0.2:
                reason_parts.append(f"content match ({overlap:.0%})")
            if signal_boost > 0:
                reason_parts.append("keyword match")
            if access_boost > 0:
                reason_parts.append(f"well-tested ({pattern.get('access_count', 0)}x)")

            scored.append(
                {
                    "text": text,
                    "relevance": min(relevance, 1.0),
                    "source": pattern["source"],
                    "type": pattern["type"],
                    "id": pattern["id"],
                    "confidence": pattern["confidence"],
                    "reason": ", ".join(reason_parts) if reason_parts else "relevant principle",
                }
            )

    scored.sort(key=lambda r: r["relevance"], reverse=True)
    return scored[:max_recommendations]


def format_recommendations(recs: list[dict[str, Any]]) -> str:
    """Format recommendations for display."""
    if not recs:
        return ""

    lines = ["**Relevant patterns:**"]
    for r in recs:
        conf = r.get("confidence", 0)
        icon = "★" if conf >= 0.8 else "☆"
        lines.append(f"  {icon} {r['text'][:150]}")
        lines.append(f"    from: {r['source']} ({r['type']}) | {r['reason']}")
    return "\n".join(lines)


def get_full_context_advice(context: str) -> str:
    """Combined anticipation warnings + proactive recommendations.

    This is the single function to call for full context-aware guidance.
    """
    from divineos.core.anticipation import anticipate, format_anticipation

    warnings = anticipate(context)
    recommendations = recommend(context)

    parts = []
    if warnings:
        parts.append(format_anticipation(warnings))
    if recommendations:
        parts.append(format_recommendations(recommendations))
    if not parts:
        return ""
    return "\n\n".join(parts)


# ─── Pattern Outcome Tracking ──────────────────────────────────────


def _init_pattern_outcomes_table() -> None:
    """Create the pattern outcome tracking table."""
    conn = get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pattern_outcomes (
                outcome_id TEXT PRIMARY KEY,
                pattern_id TEXT NOT NULL,
                pattern_source TEXT NOT NULL,
                outcome TEXT NOT NULL CHECK(outcome IN ('success', 'failure')),
                context TEXT NOT NULL DEFAULT '',
                created_at REAL NOT NULL
            )
        """)
        conn.commit()
    finally:
        conn.close()


def record_pattern_outcome(
    pattern_id: str,
    pattern_source: str,
    outcome: str,
    context: str = "",
) -> dict[str, Any]:
    """Record outcome after following a proactive recommendation.

    When a recommendation leads to a bad outcome, the underlying pattern's
    confidence is weakened. Good outcomes strengthen it. This closes the
    feedback loop — patterns that consistently mislead get archived.

    Args:
        pattern_id: The ID of the pattern (knowledge_id, opinion_id, etc.)
        pattern_source: Where the pattern came from ('knowledge', 'opinion', 'advice', 'decision')
        outcome: 'success' or 'failure'
        context: Optional description of what happened

    Returns dict with: adjusted_confidence, archived, failures_total
    """
    _init_pattern_outcomes_table()

    # Record the outcome
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO pattern_outcomes (outcome_id, pattern_id, pattern_source, outcome, context, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), pattern_id, pattern_source, outcome, context, time.time()),
        )
        conn.commit()
    finally:
        conn.close()

    # Apply confidence adjustment to the source
    delta = PATTERN_SUCCESS_DELTA if outcome == "success" else PATTERN_FAILURE_DELTA
    result: dict[str, Any] = {"archived": False, "failures_total": 0}

    if pattern_source == "knowledge":
        result = _adjust_knowledge_confidence(pattern_id, delta)
    elif pattern_source == "opinion":
        result = _adjust_opinion_confidence(pattern_id, delta)
    # advice and decision sources don't have adjustable confidence — just track

    # Check tactical failure count for archiving
    conn = get_connection()
    try:
        failure_count = conn.execute(
            "SELECT COUNT(*) FROM pattern_outcomes WHERE pattern_id = ? AND outcome = 'failure'",
            (pattern_id,),
        ).fetchone()[0]
        result["failures_total"] = failure_count

        if failure_count >= PATTERN_TACTICAL_FAILURE_MAX and not result.get("archived"):
            _archive_pattern(pattern_id, pattern_source)
            result["archived"] = True
            logger.info(
                "Pattern %s archived: %d tactical failures exceeded threshold %d",
                pattern_id[:12],
                failure_count,
                PATTERN_TACTICAL_FAILURE_MAX,
            )
    finally:
        conn.close()

    logger.debug(
        "Pattern outcome recorded: %s %s → confidence %s%.2f%s",
        pattern_id[:12],
        outcome,
        "+" if delta > 0 else "",
        delta,
        " [ARCHIVED]" if result.get("archived") else "",
    )

    return result


def _adjust_knowledge_confidence(knowledge_id: str, delta: float) -> dict[str, Any]:
    """Adjust a knowledge entry's confidence by delta. Archive if below threshold."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT confidence, superseded_by FROM knowledge WHERE knowledge_id = ?",
            (knowledge_id,),
        ).fetchone()
        if not row or row[1] is not None:
            return {"adjusted_confidence": 0.0, "archived": False}

        new_conf = max(row[0] + delta, -1.0)  # Allow negative for archiving signal
        conn.execute(
            "UPDATE knowledge SET confidence = ?, updated_at = ? WHERE knowledge_id = ?",
            (new_conf, time.time(), knowledge_id),
        )
        conn.commit()

        archived = new_conf <= PATTERN_ARCHIVE_THRESHOLD
        if archived:
            logger.info(
                "Knowledge %s confidence dropped to %.2f (below %.2f) — archiving",
                knowledge_id[:12],
                new_conf,
                PATTERN_ARCHIVE_THRESHOLD,
            )
        return {"adjusted_confidence": new_conf, "archived": archived}
    finally:
        conn.close()


def _adjust_opinion_confidence(opinion_id: str, delta: float) -> dict[str, Any]:
    """Adjust an opinion's confidence by delta.

    Uses the opinion store API so timestamps and revision counts
    stay consistent (raw SQL would bypass those updates).
    """
    try:
        if delta > 0:
            from divineos.core.opinion_store import strengthen_opinion

            new_conf = strengthen_opinion(opinion_id, "pattern outcome: positive", boost=delta)
        else:
            from divineos.core.opinion_store import challenge_opinion

            new_conf = challenge_opinion(
                opinion_id, "pattern outcome: negative", penalty=abs(delta)
            )
        return {
            "adjusted_confidence": new_conf,
            "archived": new_conf <= PATTERN_ARCHIVE_THRESHOLD,
        }
    except _PP_ERRORS:
        return {"adjusted_confidence": 0.0, "archived": False}


def _archive_pattern(pattern_id: str, source: str) -> None:
    """Mark a pattern as archived — too many failures to recommend."""
    if source == "knowledge":
        conn = get_connection()
        try:
            # Set confidence to archive threshold so it drops out of recommendations
            conn.execute(
                "UPDATE knowledge SET confidence = ? WHERE knowledge_id = ?",
                (PATTERN_ARCHIVE_THRESHOLD, pattern_id),
            )
            conn.commit()
        finally:
            conn.close()


def get_pattern_outcome_stats(pattern_id: str) -> dict[str, Any]:
    """Get success/failure stats for a pattern."""
    try:
        _init_pattern_outcomes_table()
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT outcome, COUNT(*) FROM pattern_outcomes WHERE pattern_id = ? GROUP BY outcome",
                (pattern_id,),
            ).fetchall()
            successes = 0
            failures = 0
            for outcome, count in rows:
                if outcome == "success":
                    successes = count
                else:
                    failures = count
            total = successes + failures
            return {
                "successes": successes,
                "failures": failures,
                "total": total,
                "success_rate": successes / total if total > 0 else 0.0,
            }
        finally:
            conn.close()
    except _PP_ERRORS:
        return {"successes": 0, "failures": 0, "total": 0, "success_rate": 0.0}
