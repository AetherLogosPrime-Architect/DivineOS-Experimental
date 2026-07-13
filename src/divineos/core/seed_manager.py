"""Seed Manager — validates and versions seed data.

Ensures seed.json is well-formed before loading, tracks which version
has been applied, and supports merge-mode reseeding when the seed
is updated.
"""

from __future__ import annotations

import time
from typing import Any

from loguru import logger

from divineos.core.knowledge import (
    _get_connection,
    get_knowledge,
    get_lessons,
    record_lesson,
    store_knowledge,
)
from divineos.core.memory import set_core


def validate_seed(seed_data: dict[str, Any]) -> list[str]:
    """Validate seed data structure. Returns list of errors (empty = valid)."""
    errors: list[str] = []

    if not isinstance(seed_data, dict):
        return ["Seed data must be a dict"]

    # Version field
    if "version" not in seed_data:
        errors.append("Missing 'version' field")

    # Core memory
    core = seed_data.get("core_memory", {})
    if not isinstance(core, dict):
        errors.append("'core_memory' must be a dict")
    else:
        required_slots = {"user_identity", "project_purpose"}
        missing = required_slots - set(core.keys())
        if missing:
            errors.append(f"Core memory missing required slots: {missing}")
        for slot_id, content in core.items():
            if not isinstance(content, str) or not content.strip():
                errors.append(f"Core memory slot '{slot_id}' must be a non-empty string")

    # Knowledge entries
    knowledge = seed_data.get("knowledge", [])
    if not isinstance(knowledge, list):
        errors.append("'knowledge' must be a list")
    else:
        for i, entry in enumerate(knowledge):
            if not isinstance(entry, dict):
                errors.append(f"knowledge[{i}] must be a dict")
                continue
            if "type" not in entry:
                errors.append(f"knowledge[{i}] missing 'type'")
            if "content" not in entry:
                errors.append(f"knowledge[{i}] missing 'content'")
            elif not entry["content"].strip():
                errors.append(f"knowledge[{i}] has empty content")

    # Lessons
    lessons = seed_data.get("lessons", [])
    if not isinstance(lessons, list):
        errors.append("'lessons' must be a list")
    else:
        for i, lesson in enumerate(lessons):
            if not isinstance(lesson, dict):
                errors.append(f"lessons[{i}] must be a dict")
                continue
            if "category" not in lesson:
                errors.append(f"lessons[{i}] missing 'category'")

    return errors


def get_applied_seed_version() -> str | None:
    """Get the version of the seed that was last applied to this database."""
    conn = _get_connection()
    try:
        # Check if metadata table exists
        table_exists = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='seed_metadata'"
        ).fetchone()
        if not table_exists:
            return None
        row = conn.execute("SELECT value FROM seed_metadata WHERE key = 'seed_version'").fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def set_applied_seed_version(version: str) -> None:
    """Record which seed version was applied."""

    conn = _get_connection()
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS seed_metadata (key TEXT PRIMARY KEY, value TEXT, updated_at REAL)"
        )
        conn.execute(
            "INSERT OR REPLACE INTO seed_metadata (key, value, updated_at) VALUES (?, ?, ?)",
            ("seed_version", version, time.time()),
        )
        conn.commit()
        logger.info(f"Applied seed version: {version}")
    finally:
        conn.close()


def should_reseed(current_version: str | None, seed_version: str) -> bool:
    """Check if the seed needs to be (re)applied.

    Returns True if:
    - No seed version has been applied yet
    - The seed version is newer than the applied version
    """
    if current_version is None:
        return True

    # Simple semver comparison: split on dots, compare numerically
    try:
        current_parts = [int(x) for x in current_version.split(".")]
        seed_parts = [int(x) for x in seed_version.split(".")]
        return seed_parts > current_parts
    except (ValueError, AttributeError):
        # If parsing fails, reseed to be safe
        return True


def apply_seed(
    seed_data: dict[str, Any],
    mode: str = "merge",
) -> dict[str, int]:
    """Apply seed data to the database.

    Args:
        seed_data: validated seed data
        mode: "merge" (only add new entries) or "full" (apply everything)

    Returns:
        Counts of what was applied.
    """
    # `skipped` counts knowledge + lesson entries that were deduplicated.
    # `core_slots_skipped` tracks preserved-filled-slot skips separately so
    # existing callers/tests that read `skipped` as knowledge-dedup count
    # keep their meaning.
    counts = {"core_slots": 0, "knowledge": 0, "lessons": 0, "skipped": 0, "core_slots_skipped": 0}

    # Core memory — in merge mode, preserve existing filled slots. The seed
    # may ship template placeholders (e.g. "[TEMPLATE — fill this in…]") for
    # identity slots. Overwriting a lived-in identity with a template would
    # be destructive, and overwriting any grown-into slot with seed defaults
    # would silently erase session learning. So merge = "fill empties only."
    # Full mode still overwrites (explicit re-seed).
    existing_core: dict[str, str] = {}
    if mode == "merge":
        from divineos.core.memory import get_core

        existing_core = {k: v for k, v in get_core().items() if v and v.strip()}

    for slot_id, content in seed_data.get("core_memory", {}).items():
        if mode == "merge" and slot_id in existing_core:
            counts["core_slots_skipped"] += 1
            continue
        try:
            set_core(slot_id, content)
            counts["core_slots"] += 1
        except ValueError:
            pass

    # Knowledge — in merge mode, skip entries that already exist
    # Include superseded entries so we don't resurrect knowledge that was
    # intentionally retired. get_knowledge only returns active entries,
    # so we also query superseded ones directly.
    existing_contents = set()
    if mode == "merge":
        for entry in get_knowledge(limit=1000):
            existing_contents.add(entry["content"].strip().lower())
        # Also check superseded entries to prevent resurrection
        conn = _get_connection()
        try:
            rows = conn.execute(
                "SELECT content FROM knowledge WHERE superseded_by IS NOT NULL"
            ).fetchall()
            for row in rows:
                existing_contents.add(row[0].strip().lower())
        finally:
            conn.close()

    for entry in seed_data.get("knowledge", []):
        content = entry.get("content", "").strip()
        if mode == "merge" and content.lower() in existing_contents:
            counts["skipped"] += 1
            continue
        # Seed entries are INHERITED by definition — I was "born knowing"
        # them, they have no session evidence behind them. If an entry
        # explicitly specifies a source, honor it (e.g., a seed entry that
        # encodes a corroborated observation); otherwise default to
        # INHERITED so the epistemic reporter classifies it correctly.
        store_knowledge(
            knowledge_type=entry["type"],
            content=content,
            confidence=entry.get("confidence", 1.0),
            tags=entry.get("tags", []),
            maturity=entry.get("maturity", "RAW"),
            source=entry.get("source", "INHERITED"),
        )
        counts["knowledge"] += 1

    # Lessons — only seed categories that don't already exist
    existing_categories = {les["category"] for les in get_lessons()}
    for lesson in seed_data.get("lessons", []):
        category = lesson["category"]
        if category in existing_categories:
            counts["skipped"] += 1
            continue
        record_lesson(
            category=category,
            description=f"(seeded) {category}",
            session_id="seed",
        )
        counts["lessons"] += 1

    # Record version
    version = seed_data.get("version", "0.0.0")
    set_applied_seed_version(version)

    return counts


def reclassify_seed_as_inherited(seed_data: dict[str, Any]) -> dict[str, int]:
    """Migration: fix legacy seed entries whose source was defaulted to STATED.

    Before the seed-source fix, `apply_seed` called `store_knowledge` without
    passing `source`, so seed entries landed with source='STATED' — which the
    epistemic reporter classifies as "told by the user". That's wrong: seed
    entries are INHERITED (I was born knowing them, no session evidence).

    This walks the canonical seed content list, finds matching entries in the
    knowledge table that are currently tagged STATED, and reclassifies them
    as INHERITED. Idempotent — safe to run repeatedly.

    Only rewrites entries that match seed content exactly AND are currently
    STATED (not DEMONSTRATED, not CORRECTED — those were set intentionally).
    """
    counts = {"reclassified": 0, "already_correct": 0, "not_seed": 0}
    seed_contents = {e.get("content", "").strip() for e in seed_data.get("knowledge", [])}
    if not seed_contents:
        return counts

    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT knowledge_id, content, source FROM knowledge WHERE superseded_by IS NULL"
        ).fetchall()
        now = time.time()
        for kid, content, source in rows:
            trimmed = (content or "").strip()
            if trimmed not in seed_contents:
                counts["not_seed"] += 1
                continue
            if source == "INHERITED":
                counts["already_correct"] += 1
                continue
            if source != "STATED":
                # Don't overwrite intentional assignments (DEMONSTRATED etc).
                counts["not_seed"] += 1
                continue
            conn.execute(
                "UPDATE knowledge SET source = 'INHERITED', updated_at = ? WHERE knowledge_id = ?",
                (now, kid),
            )
            counts["reclassified"] += 1
        conn.commit()
    finally:
        conn.close()

    logger.info(
        "Seed reclassification: %d fixed, %d already correct, %d non-seed",
        counts["reclassified"],
        counts["already_correct"],
        counts["not_seed"],
    )
    return counts


# Confidence that the broken orphan-flagger was demoting entries to.
# Kept in sync with CONFIDENCE_ORPHAN_DEMOTE. If an INHERITED entry is
# sitting at exactly this value it was almost certainly the bug's victim.
_ORPHAN_DEMOTE_SENTINEL = 0.5


def restore_inherited_confidence(seed_data: dict[str, Any]) -> dict[str, int]:
    """Migration: restore INHERITED entries spuriously demoted by the orphan bug.

    Before the orphan-flagger fix, `_flag_orphans` ignored its age gate and
    had no INHERITED exemption. Fresh seed entries got demoted to confidence
    0.5 the same day they loaded. On one worktree this hit 13 of 19 seed
    entries (68%).

    This walks the canonical seed, finds INHERITED entries currently at the
    sentinel confidence (0.5) whose content still matches a seed entry, and
    restores them to the seed-specified confidence. Idempotent.

    Safety guards:
    - Only touches INHERITED entries (won't restore extracted claims)
    - Only touches entries at exactly the orphan-demote sentinel (0.5)
    - Only touches entries whose content still matches the current seed
      (so if an entry was superseded by a newer one, it stays down)
    """
    counts = {"restored": 0, "already_ok": 0, "not_victim": 0}
    # Map seed content -> seed-specified confidence (default 1.0)
    seed_by_content: dict[str, float] = {}
    for entry in seed_data.get("knowledge", []):
        content = entry.get("content", "").strip()
        if content:
            seed_by_content[content] = float(entry.get("confidence", 1.0))
    if not seed_by_content:
        return counts

    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT knowledge_id, content, source, confidence FROM knowledge "
            "WHERE superseded_by IS NULL AND source = 'INHERITED'"
        ).fetchall()
        now = time.time()
        for kid, content, _source, confidence in rows:
            trimmed = (content or "").strip()
            target = seed_by_content.get(trimmed)
            if target is None:
                counts["not_victim"] += 1
                continue
            # Only touch entries at the bug's sentinel value
            if abs(confidence - _ORPHAN_DEMOTE_SENTINEL) > 1e-6:
                counts["already_ok"] += 1
                continue
            conn.execute(
                "UPDATE knowledge SET confidence = ?, updated_at = ? WHERE knowledge_id = ?",
                (target, now, kid),
            )
            counts["restored"] += 1
        conn.commit()
    finally:
        conn.close()

    logger.info(
        "Seed confidence restoration: %d restored, %d already ok, %d non-victim",
        counts["restored"],
        counts["already_ok"],
        counts["not_victim"],
    )
    return counts
