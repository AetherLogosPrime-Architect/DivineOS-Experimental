"""Seed Manager — validates and versions seed data.

Ensures seed.json is well-formed before loading, tracks which version
has been applied, and supports merge-mode reseeding when the seed
is updated.
"""

from __future__ import annotations

import time
from typing import Any

from loguru import logger


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
    from divineos.core.knowledge import _get_connection

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
    from divineos.core.knowledge import _get_connection

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
    from divineos.core.knowledge import (
        get_knowledge,
        store_knowledge,
    )
    from divineos.core.memory import set_core

    counts = {"core_slots": 0, "knowledge": 0, "lessons": 0, "skipped": 0}

    # Core memory — always update (identity may have changed)
    for slot_id, content in seed_data.get("core_memory", {}).items():
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
        from divineos.core.knowledge import _get_connection

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
        store_knowledge(
            knowledge_type=entry["type"],
            content=content,
            confidence=entry.get("confidence", 1.0),
            tags=entry.get("tags", []),
            maturity=entry.get("maturity", "RAW"),
        )
        counts["knowledge"] += 1

    # Lessons — only seed categories that don't already exist
    from divineos.core.knowledge import get_lessons, record_lesson

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
