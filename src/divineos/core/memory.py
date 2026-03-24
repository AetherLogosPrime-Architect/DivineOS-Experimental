"""Personal Memory — The AI's Mind.

Two tiers on top of the knowledge store:

1. Core Memory: 8 fixed slots (identity, purpose, style, etc.)
   Always loaded. Rarely changes. ~200 words total.

2. Active Memory: Ranked view into the knowledge store.
   Everything that passes an importance threshold. No hard cap.
   Ranked by importance so the most critical stuff surfaces first.

The knowledge store is the archive. Personal memory is what matters.
"""

import math
import sqlite3
import time
import uuid
from typing import Any, cast

from divineos.core.ledger import DB_PATH, compute_hash

# ─── Core Memory Slots ───────────────────────────────────────────────

CORE_SLOTS = (
    "user_identity",
    "project_purpose",
    "communication_style",
    "current_priorities",
    "active_constraints",
    "known_strengths",
    "known_weaknesses",
    "relationship_context",
)


def _get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_memory_tables() -> None:
    """Create core_memory and active_memory tables if they don't exist."""
    conn = _get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS core_memory (
                slot_id      TEXT PRIMARY KEY,
                content      TEXT NOT NULL,
                updated_at   REAL NOT NULL,
                content_hash TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS active_memory (
                memory_id     TEXT PRIMARY KEY,
                knowledge_id  TEXT NOT NULL,
                importance    REAL NOT NULL DEFAULT 0.5,
                reason        TEXT NOT NULL,
                promoted_at   REAL NOT NULL,
                surface_count INTEGER NOT NULL DEFAULT 0,
                pinned        INTEGER NOT NULL DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_active_importance
            ON active_memory(importance DESC)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_active_knowledge
            ON active_memory(knowledge_id)
        """)
        conn.commit()
    finally:
        conn.close()


# ─── Core Memory ─────────────────────────────────────────────────────


def set_core(slot_id: str, content: str) -> None:
    """Set a core memory slot. Overwrites if exists."""
    if slot_id not in CORE_SLOTS:
        raise ValueError(f"Unknown slot '{slot_id}'. Valid: {', '.join(CORE_SLOTS)}")
    conn = _get_connection()
    try:
        conn.execute(
            """INSERT INTO core_memory (slot_id, content, updated_at, content_hash)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(slot_id) DO UPDATE SET
                 content = excluded.content,
                 updated_at = excluded.updated_at,
                 content_hash = excluded.content_hash""",
            (slot_id, content, time.time(), compute_hash(content)),
        )
        conn.commit()
    finally:
        conn.close()


def get_core(slot_id: str | None = None) -> dict[str, str]:
    """Get core memory. One slot or all. Returns {slot_id: content}."""
    conn = _get_connection()
    try:
        if slot_id:
            row = conn.execute(
                "SELECT slot_id, content FROM core_memory WHERE slot_id = ?",
                (slot_id,),
            ).fetchone()
            return {row[0]: row[1]} if row else {}
        rows = conn.execute(
            "SELECT slot_id, content FROM core_memory ORDER BY slot_id",
        ).fetchall()
        return {r[0]: r[1] for r in rows}
    finally:
        conn.close()


def clear_core(slot_id: str) -> bool:
    """Clear a core memory slot. Returns True if it existed."""
    if slot_id not in CORE_SLOTS:
        raise ValueError(f"Unknown slot '{slot_id}'. Valid: {', '.join(CORE_SLOTS)}")
    conn = _get_connection()
    try:
        cursor = conn.execute("DELETE FROM core_memory WHERE slot_id = ?", (slot_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def format_core() -> str:
    """Format all core memory as a text block for context injection."""
    slots = get_core()
    if not slots:
        return ""

    slot_labels = {
        "user_identity": "User",
        "project_purpose": "Project",
        "communication_style": "Communication",
        "current_priorities": "Priorities",
        "active_constraints": "Constraints",
        "known_strengths": "Strengths",
        "known_weaknesses": "Watch out for",
        "relationship_context": "Relationship",
    }

    lines = ["## Core Memory\n"]
    for slot_id in CORE_SLOTS:
        if slot_id in slots:
            label = slot_labels.get(slot_id, slot_id)
            lines.append(f"- **{label}:** {slots[slot_id]}")

    return "\n".join(lines)


# ─── Importance Scoring ──────────────────────────────────────────────


def compute_importance(entry: dict[str, Any], has_active_lesson: bool = False) -> float:
    """Score a knowledge entry for active memory. 0.0 to 1.0.

    No time decay. A mistake from day 1 scores the same as one from yesterday.
    Only real evidence changes importance.
    """
    score = 0.0

    # 30% from type — constraints and principles change behavior most
    type_weights = {
        # Sutra-style directives — always max priority
        "DIRECTIVE": 0.30,
        # New types
        "BOUNDARY": 0.30,  # Hard constraints — highest priority
        "PRINCIPLE": 0.28,  # Distilled wisdom from experience
        "DIRECTION": 0.25,  # How the user wants things done
        "PROCEDURE": 0.20,  # How to do something
        "FACT": 0.10,  # Something true about the world
        "OBSERVATION": 0.08,  # Noticed but unconfirmed
        "EPISODE": 0.05,  # A specific event
        # Legacy types — map to their successors
        "MISTAKE": 0.30,  # → BOUNDARY/PRINCIPLE
        "PREFERENCE": 0.25,  # → DIRECTION
        "PATTERN": 0.20,  # → PRINCIPLE/PROCEDURE
    }
    score += type_weights.get(entry.get("knowledge_type", ""), 0.1)

    # 25% from confidence
    score += entry.get("confidence", 0.5) * 0.25

    # 15% from usage — logarithmic, first few accesses matter most
    access = entry.get("access_count", 0)
    usage = min(1.0, math.log1p(access) / math.log1p(20))
    score += usage * 0.15

    # 10% from source — corrections carry more weight than synthesis
    source_bonus = {
        "CORRECTED": 0.10,
        "DEMONSTRATED": 0.07,
        "STATED": 0.05,
        "SYNTHESIZED": 0.03,
        "INHERITED": 0.02,
    }
    score += source_bonus.get(entry.get("source", ""), 0.02)

    # 20% from lesson connection
    if has_active_lesson:
        score += 0.2

    # Maturity adjustments — trust level affects importance
    maturity = entry.get("maturity", "RAW")
    if maturity == "CONFIRMED":
        score += 0.05
    elif maturity == "HYPOTHESIS":
        score -= 0.05

    # Low confidence penalty — entries below 0.3 are suspect
    confidence = entry.get("confidence", 0.5)
    if confidence < 0.3:
        score -= 0.1

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
        if not row:
            return False
        if row[0]:
            return False  # pinned — can't demote
        conn.execute(
            "DELETE FROM active_memory WHERE knowledge_id = ?",
            (knowledge_id,),
        )
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


def refresh_active_memory(importance_threshold: float = 0.3) -> dict[str, int]:
    """Rebuild active memory from the knowledge store.

    Everything above the importance threshold gets in. No hard cap.
    Pinned items are never removed. Superseded items are cleaned out.
    """
    from divineos.core.consolidation import get_knowledge, get_lessons

    all_entries = get_knowledge(limit=10000)
    active_lessons = get_lessons(status="active")
    improving_lessons = get_lessons(status="improving")

    # Build set of knowledge content that has active/improving lessons
    lesson_descriptions = set()
    for lesson in active_lessons + improving_lessons:
        lesson_descriptions.add(lesson["description"].lower())

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

        # Score every knowledge entry
        candidates = {}
        for entry in all_entries:
            # Check if any active lesson matches this entry
            has_lesson = False
            content_lower = entry["content"].lower()
            for desc in lesson_descriptions:
                # Simple word overlap check
                entry_words = set(content_lower.split())
                desc_words = set(desc.split())
                if entry_words and desc_words:
                    overlap = len(entry_words & desc_words) / max(len(entry_words), len(desc_words))
                    if overlap > 0.3:
                        has_lesson = True
                        break

            importance = compute_importance(entry, has_active_lesson=has_lesson)
            candidates[entry["knowledge_id"]] = (importance, has_lesson)

        # Determine what should be in active memory
        should_be_active = set()
        for kid, (importance, _) in candidates.items():
            if importance >= importance_threshold:
                should_be_active.add(kid)

        # Always keep pinned items
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
    core_text = format_core()
    active = get_active_memory()

    # If a topic hint is given, boost matching active items and search archive
    relevant = []
    if context_hint:
        from divineos.core.consolidation import search_knowledge

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

    # Track that these items were surfaced
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

    return {
        "core": core_text,
        "active": active,
        "relevant": relevant,
    }


def _safe_text(text: str) -> str:
    """Strip characters that can't be displayed on the current terminal."""
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
