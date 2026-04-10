"""Active Memory — Importance scoring, promotion, retrieval, and formatting.

Active memory is a ranked view into the knowledge store. Entries are scored
by importance, promoted/demoted based on thresholds, and surfaced during recall.
"""

import math
import re
import sqlite3
import time
import uuid
from typing import Any, cast

from loguru import logger

from divineos.core.constants import (
    ACTIVE_MEMORY_CAP,
    CONFIDENCE_ACTIVE_MEMORY_FLOOR,
    CONFIDENCE_MODERATE,
    MATURITY_BOOST_CONFIRMED,
    MATURITY_PENALTY_HYPOTHESIS,
    OVERLAP_RELATIONSHIP,
    SCORE_WEIGHT_CONFIDENCE,
    SCORE_WEIGHT_LESSON,
    SCORE_WEIGHT_RECENCY,
    SCORE_WEIGHT_USAGE,
    SECONDS_PER_DAY,
    TIME_RECENCY_WINDOW_DAYS,
    TYPE_WEIGHT_BOUNDARY,
    TYPE_WEIGHT_DIRECTION,
    TYPE_WEIGHT_DIRECTIVE,
    TYPE_WEIGHT_EPISODE,
    TYPE_WEIGHT_FACT,
    TYPE_WEIGHT_MISTAKE,
    TYPE_WEIGHT_OBSERVATION,
    TYPE_WEIGHT_PATTERN,
    TYPE_WEIGHT_PREFERENCE,
    TYPE_WEIGHT_PRINCIPLE,
    TYPE_WEIGHT_PROCEDURE,
    USAGE_LOG_SCALE,
)
from divineos.core.knowledge import (
    _is_extraction_noise,
    get_connection,
    get_knowledge,
    get_lessons,
    record_access,
    search_knowledge,
)
from divineos.core.knowledge_maintenance import promote_maturity
from divineos.core.trust_tiers import weighted_source_bonus

_get_connection = get_connection


# ─── Importance Scoring ──────────────────────────────────────────────


def _is_session_specific(content: str) -> bool:
    """Return True if content is tied to a single session rather than timeless.

    A session ID in parentheses at the end is just a citation (provenance),
    not session-specific content. Only flag entries where the session IS the topic.
    """
    lower = content.lower()
    # Session ID as the SUBJECT — "Session f95a6c6a: We spent..."
    # But NOT "investigate errors (session 7015aa770e4d)" — that's a citation
    if re.match(r"^session [a-f0-9]{8}", lower):
        return True
    # Session tool usage stats
    if "tool usage" in lower and ("bash:" in lower or "read:" in lower or "grep:" in lower):
        return True
    # Exchange/tool call counts
    if re.search(r"\d+ exchanges.*\d+ tool calls", lower):
        return True
    if re.search(r"\d+ tool calls.*\d+ exchanges", lower):
        return True
    # "Most frequently used tool" — per-session stat
    if "most frequently used tool" in lower:
        return True
    # "this session" as subject — "I showed good honesty this session (session ...)"
    if re.search(r"this session \(session [a-f0-9]{8}", lower):
        return True
    return False


def compute_importance(
    entry: dict[str, Any],
    has_active_lesson: bool = False,
    context_words: set[str] | None = None,
) -> float:
    """Score a knowledge entry for active memory. 0.0 to 1.0.

    Principles and directives are timeless. Session-specific trivia
    (tool counts, exchange stats) gets penalized to stay out of active memory.

    context_words: if provided, entries whose content overlaps with current
    goals/priorities get a relevance multiplier. This differentiates
    "important right now" from "important in general."
    """
    score = 0.0

    # 30% from type — constraints and principles change behavior most
    type_weights = {
        "DIRECTIVE": TYPE_WEIGHT_DIRECTIVE,
        "BOUNDARY": TYPE_WEIGHT_BOUNDARY,
        "PRINCIPLE": TYPE_WEIGHT_PRINCIPLE,
        "DIRECTION": TYPE_WEIGHT_DIRECTION,
        "PROCEDURE": TYPE_WEIGHT_PROCEDURE,
        "FACT": TYPE_WEIGHT_FACT,
        "OBSERVATION": TYPE_WEIGHT_OBSERVATION,
        "EPISODE": TYPE_WEIGHT_EPISODE,
        # Legacy types — map to their successors
        "MISTAKE": TYPE_WEIGHT_MISTAKE,
        "PREFERENCE": TYPE_WEIGHT_PREFERENCE,
        "PATTERN": TYPE_WEIGHT_PATTERN,
    }
    score += type_weights.get(entry.get("knowledge_type", ""), TYPE_WEIGHT_FACT)

    # 25% from confidence
    score += entry.get("confidence", CONFIDENCE_MODERATE) * SCORE_WEIGHT_CONFIDENCE

    # 15% from usage — logarithmic, first few accesses matter most
    access = entry.get("access_count", 0)
    usage = min(1.0, math.log1p(access) / math.log1p(USAGE_LOG_SCALE))
    score += usage * SCORE_WEIGHT_USAGE

    # 10% from source — weighted by trust tier (MEASURED > BEHAVIORAL > SELF_REPORTED)
    score += weighted_source_bonus(entry.get("source", ""))

    # 20% from lesson connection
    if has_active_lesson:
        score += SCORE_WEIGHT_LESSON

    # 5% recency boost — fresh knowledge surfaces above stale entries
    # Decays linearly over TIME_RECENCY_WINDOW_DAYS
    created_at = entry.get("created_at", 0)
    if created_at:
        age_days = (time.time() - created_at) / SECONDS_PER_DAY
        recency = max(0.0, 1.0 - age_days / TIME_RECENCY_WINDOW_DAYS)
        score += recency * SCORE_WEIGHT_RECENCY

    # Maturity adjustments — trust level affects importance
    maturity = entry.get("maturity", "RAW")
    if maturity == "CONFIRMED":
        score += MATURITY_BOOST_CONFIRMED
    elif maturity == "HYPOTHESIS":
        score -= MATURITY_PENALTY_HYPOTHESIS

    # Context relevance — boost entries that match current goals/priorities.
    # This is a multiplier on the base score, not additive, so it amplifies
    # differences instead of clustering everything higher.
    if context_words:
        content_words = set((entry.get("content") or "").lower().split())
        if content_words and context_words:
            overlap = len(content_words & context_words)
            # Normalize by the smaller set so short goals can still match
            relevance = overlap / max(min(len(content_words), len(context_words)), 1)
            # Up to 30% boost for highly relevant entries
            score *= 1.0 + relevance * 0.30

    # Low confidence penalty — entries below active memory floor are suspect
    confidence = entry.get("confidence", CONFIDENCE_MODERATE)
    if confidence < CONFIDENCE_ACTIVE_MEMORY_FLOOR:
        score -= 0.1

    # Session-specific penalty — tool counts, exchange stats, session IDs
    # These are tied to one session and don't belong in persistent active memory
    content = entry.get("content", "")
    if _is_session_specific(content):
        score -= 0.30

    # Extraction noise penalty — raw user quotes, affirmations, task instructions
    # These slipped past earlier filters and shouldn't rank in active memory
    knowledge_type = entry.get("knowledge_type", "")
    if _is_extraction_noise(content, knowledge_type):
        score -= 0.35

    return cast("float", max(0.0, min(1.0, score)))


# ─── Active Memory ───────────────────────────────────────────────────


def promote_to_active(
    knowledge_id: str,
    reason: str,
    importance: float | None = None,
    pinned: bool = False,
) -> str:
    """Promote a knowledge entry to active memory. Returns memory_id."""
    conn = _get_connection()
    try:
        # Check if already in active memory
        existing = conn.execute(
            "SELECT memory_id FROM active_memory WHERE knowledge_id = ?",
            (knowledge_id,),
        ).fetchone()
        if existing:
            # Update importance and reason if re-promoted
            updates: dict[str, Any] = {"reason": reason}
            if importance is not None:
                updates["importance"] = importance
            if pinned:
                updates["pinned"] = 1
            set_clause = ", ".join(f"{k} = ?" for k in updates)
            conn.execute(
                f"UPDATE active_memory SET {set_clause} WHERE knowledge_id = ?",  # nosec B608 - column names from updates dict keys, all values passed as parameters
                (*updates.values(), knowledge_id),
            )
            conn.commit()
            return cast("str", existing[0])

        memory_id = uuid.uuid4().hex[:16]
        conn.execute(
            """INSERT INTO active_memory
               (memory_id, knowledge_id, importance, reason, promoted_at, pinned)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                memory_id,
                knowledge_id,
                importance if importance is not None else 0.5,
                reason,
                time.time(),
                1 if pinned else 0,
            ),
        )
        conn.commit()
        return memory_id
    finally:
        conn.close()


def demote_from_active(knowledge_id: str) -> bool:
    """Remove a knowledge entry from active memory. Returns True if it existed.
    Pinned items cannot be demoted — unpin first.
    """
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT pinned FROM active_memory WHERE knowledge_id = ?",
            (knowledge_id,),
        ).fetchone()
        if row is None:
            return False
        if row[0]:
            return False
        conn.execute("DELETE FROM active_memory WHERE knowledge_id = ?", (knowledge_id,))
        conn.commit()
        return True
    finally:
        conn.close()


def get_active_memory() -> list[dict[str, Any]]:
    """Get all active memory items ranked by importance (highest first)."""
    conn = _get_connection()
    try:
        rows = conn.execute(
            """SELECT am.memory_id, am.knowledge_id, am.importance,
                      am.reason, am.promoted_at, am.surface_count, am.pinned,
                      k.knowledge_type, k.content, k.confidence, k.access_count
               FROM active_memory am
               JOIN knowledge k ON am.knowledge_id = k.knowledge_id
               WHERE k.superseded_by IS NULL
               ORDER BY am.importance DESC""",
        ).fetchall()
        return [
            {
                "memory_id": r[0],
                "knowledge_id": r[1],
                "importance": r[2],
                "reason": r[3],
                "promoted_at": r[4],
                "surface_count": r[5],
                "pinned": bool(r[6]),
                "knowledge_type": r[7],
                "content": r[8],
                "confidence": r[9],
                "access_count": r[10],
            }
            for r in rows
        ]
    finally:
        conn.close()


def _gather_context_words() -> set[str]:
    """Build a set of words from current goals and priorities.

    This is the context signal that makes active memory relevance-aware.
    Goals and priorities change session to session, so entries relevant
    to current work surface above generic directives.
    """
    words: set[str] = set()
    # Common stop words to exclude from matching
    stop = {
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "shall",
        "can",
        "need",
        "must",
        "to",
        "of",
        "in",
        "for",
        "on",
        "with",
        "at",
        "by",
        "from",
        "as",
        "into",
        "through",
        "during",
        "before",
        "after",
        "above",
        "below",
        "between",
        "out",
        "off",
        "over",
        "under",
        "again",
        "further",
        "then",
        "once",
        "and",
        "but",
        "or",
        "nor",
        "not",
        "no",
        "so",
        "if",
        "than",
        "too",
        "very",
        "just",
        "don",
        "that",
        "this",
        "these",
        "those",
        "it",
        "its",
        "i",
        "my",
        "me",
        "we",
        "our",
        "you",
        "your",
        "all",
        "each",
        "every",
        "both",
        "few",
        "more",
        "most",
        "other",
        "some",
        "such",
        "only",
        "own",
        "same",
        "when",
        "where",
        "how",
        "what",
        "which",
        "who",
        "whom",
        "why",
        "up",
    }
    try:
        from divineos.core.hud_state import _ensure_hud_dir

        goals_path = _ensure_hud_dir() / "active_goals.json"
        if goals_path.exists():
            import json as _json

            goals = _json.loads(goals_path.read_text(encoding="utf-8"))
            for goal in goals:
                if goal.get("status") != "done":
                    text = (goal.get("text") or "").lower()
                    words.update(w for w in text.split() if len(w) > 2 and w not in stop)
    except (ImportError, OSError, ValueError):
        pass

    try:
        from divineos.core.memory import get_core

        core = get_core()
        priorities = core.get("priorities", "")
        if isinstance(priorities, str):
            words.update(w for w in priorities.lower().split() if len(w) > 2 and w not in stop)
    except (ImportError, OSError):
        pass

    return words


def refresh_active_memory(
    importance_threshold: float = CONFIDENCE_ACTIVE_MEMORY_FLOOR,
    max_active: int = ACTIVE_MEMORY_CAP,
) -> dict[str, int]:
    """Rebuild active memory from the knowledge store.

    Takes the top entries by importance, up to max_active. Pinned items
    are always kept (don't count toward the cap). Entries below the
    importance threshold are excluded regardless of cap.
    """
    all_entries = get_knowledge(limit=10000)
    active_lessons = get_lessons(status="active")
    improving_lessons = get_lessons(status="improving")
    context_words = _gather_context_words()

    # Build set of knowledge content that has active/improving lessons
    lesson_descriptions = set()
    for lesson in active_lessons + improving_lessons:
        desc = lesson.get("description") or ""
        if desc:
            lesson_descriptions.add(desc.lower())

    conn = _get_connection()
    try:
        # Get currently pinned items (never remove these)
        pinned = set()
        for row in conn.execute(
            "SELECT knowledge_id FROM active_memory WHERE pinned = 1",
        ).fetchall():
            pinned.add(row[0])

        promoted = 0
        demoted = 0
        kept = 0

        # Find archived entries so we can skip them
        archived_ids: set[str] = set()
        try:
            has_layer = any(
                col[1] == "layer" for col in conn.execute("PRAGMA table_info(knowledge)").fetchall()
            )
            if has_layer:
                for row in conn.execute(
                    "SELECT knowledge_id FROM knowledge WHERE layer = 'archive'"
                ).fetchall():
                    archived_ids.add(row[0])
        except (sqlite3.OperationalError, OSError) as exc:
            logger.debug(f"Failed to query archived entries: {exc}")

        # Score every knowledge entry (skip archived — they shouldn't surface)
        candidates = {}
        for entry in all_entries:
            if entry["knowledge_id"] in archived_ids:
                continue
            # Check if any active lesson matches this entry
            has_lesson = False
            content_lower = (entry.get("content") or "").lower()
            for desc in lesson_descriptions:
                # Simple word overlap check
                entry_words = set(content_lower.split())
                desc_words = set(desc.split())
                if entry_words and desc_words:
                    overlap = len(entry_words & desc_words) / max(len(entry_words), len(desc_words))
                    if overlap > OVERLAP_RELATIONSHIP:
                        has_lesson = True
                        break

            importance = compute_importance(
                entry, has_active_lesson=has_lesson, context_words=context_words
            )
            candidates[entry["knowledge_id"]] = (importance, has_lesson)

        # Determine what should be in active memory:
        # 1. Filter by threshold
        # 2. Rank by importance
        # 3. Take top max_active (pinned items don't count toward cap)
        above_threshold = [
            (kid, imp)
            for kid, (imp, _) in candidates.items()
            if imp >= importance_threshold and kid not in pinned
        ]
        above_threshold.sort(key=lambda x: x[1], reverse=True)
        should_be_active = {kid for kid, _ in above_threshold[:max_active]}

        # Always keep pinned items (outside the cap)
        should_be_active |= pinned

        # Get current active memory
        current_active = set()
        for row in conn.execute("SELECT knowledge_id FROM active_memory").fetchall():
            current_active.add(row[0])

        # Add new items
        for kid in should_be_active - current_active:
            importance, has_lesson = candidates.get(kid, (0.5, False))
            reason = "auto-promoted"
            if has_lesson:
                reason = "linked to active lesson"
            memory_id = uuid.uuid4().hex[:16]
            conn.execute(
                """INSERT INTO active_memory
                   (memory_id, knowledge_id, importance, reason, promoted_at, pinned)
                   VALUES (?, ?, ?, ?, ?, 0)""",
                (memory_id, kid, importance, reason, time.time()),
            )
            promoted += 1

        # Update importance scores for existing items
        for kid in should_be_active & current_active:
            importance, _ = candidates.get(kid, (0.5, False))
            conn.execute(
                "UPDATE active_memory SET importance = ? WHERE knowledge_id = ?",
                (importance, kid),
            )
            kept += 1

        # Remove items that fell below threshold (but not pinned)
        for kid in current_active - should_be_active:
            if kid not in pinned:
                conn.execute(
                    "DELETE FROM active_memory WHERE knowledge_id = ?",
                    (kid,),
                )
                demoted += 1

        conn.commit()
        return {"promoted": promoted, "demoted": demoted, "kept": kept}
    finally:
        conn.close()


# ─── Retrieval ───────────────────────────────────────────────────────


def recall(context_hint: str = "") -> dict[str, Any]:
    """The main retrieval function. Returns what the AI should remember.

    Returns:
        {
            "core": str,             # formatted core memory text
            "active": list[dict],    # all active memory, ranked by importance
            "relevant": list[dict],  # archive items matching context_hint (if given)
        }

    """
    from divineos.core.memory import format_core  # late import to avoid cycle

    core_text = format_core()
    active = get_active_memory()

    # If a topic hint is given, boost matching active items and search archive
    relevant = []
    if context_hint:
        hint_words = set(context_hint.lower().split())

        # Boost matching active items (move to top by adding bonus)
        for item in active:
            content_words = set(item["content"].lower().split())
            if hint_words & content_words:
                item["importance"] += 0.5  # temporary boost for this recall

        # Re-sort active by boosted importance
        active.sort(key=lambda x: x["importance"], reverse=True)

        # Search archive for items not already in active memory
        active_kids = {item["knowledge_id"] for item in active}
        archive_results = search_knowledge(context_hint, limit=20)
        for result in archive_results:
            if result["knowledge_id"] not in active_kids:
                relevant.append(result)

    # Track that these items were surfaced and register real access
    conn = _get_connection()
    try:
        for item in active:
            conn.execute(
                """UPDATE active_memory
                   SET surface_count = surface_count + 1
                   WHERE knowledge_id = ?""",
                (item["knowledge_id"],),
            )
        conn.commit()
    finally:
        conn.close()

    # Record access and check maturity promotion for surfaced knowledge
    for item in active:
        record_access(item["knowledge_id"])
        promote_maturity(item["knowledge_id"])
    for item in relevant:
        record_access(item["knowledge_id"])
        promote_maturity(item["knowledge_id"])

    return {
        "core": core_text,
        "active": active,
        "relevant": relevant,
    }


TYPOGRAPHIC_REPLACEMENTS: dict[str, str] = {
    "\u2014": "--",  # em-dash
    "\u2013": "-",  # en-dash
    "\u2018": "'",  # left single quote
    "\u2019": "'",  # right single quote
    "\u201c": '"',  # left double quote
    "\u201d": '"',  # right double quote
    "\u2026": "...",  # ellipsis
    "\u2022": "*",  # bullet
    "\u00d7": "x",  # multiplication sign
    "\u00f7": "/",  # division sign
    "\u2192": "->",  # right arrow
    "\u2190": "<-",  # left arrow
    "\u2191": "^",  # up arrow
    "\u2193": "v",  # down arrow
    "\u2194": "<->",  # left-right arrow
    "\u21d2": "=>",  # right double arrow
}


def _safe_text(text: str) -> str:
    """Replace typographic characters with ASCII equivalents."""
    for fancy, plain in TYPOGRAPHIC_REPLACEMENTS.items():
        text = text.replace(fancy, plain)
    return text.encode("ascii", errors="replace").decode("ascii")


def format_recall(result: dict[str, Any]) -> str:
    """Format a recall result into readable text."""
    lines = []

    if result["core"]:
        lines.append(result["core"])
        lines.append("")

    if result["active"]:
        lines.append("## Active Memory\n")
        for item in result["active"]:
            pin = " [pinned]" if item.get("pinned") else ""
            content = _safe_text(item["content"][:120])
            lines.append(f"- [{item['importance']:.2f}] {item['knowledge_type']}: {content}{pin}")
        lines.append("")

    if result["relevant"]:
        lines.append("## Also Relevant (from archive)\n")
        for item in result["relevant"]:
            content = _safe_text(item["content"][:120])
            lines.append(f"- {item['knowledge_type']}: {content}")
        lines.append("")

    return "\n".join(lines) if lines else "No memories yet."
