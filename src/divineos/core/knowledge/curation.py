"""Knowledge curation — layer assignment, archival, and text cleanup.

Memory is layers. Not everything needs to be in your face every session.

Layers:
    urgent  — Recent corrections, active lessons, things that need attention NOW
    active  — Current working knowledge, directives, recent entries
    stable  — Established principles (high access, confirmed). Brief one-liner in briefing.
    archive — Resolved lessons, old episodes, stale entries. Only loaded on request.

Curation runs at SESSION_END after knowledge extraction. It:
1. Assigns layers to new entries (default: active)
2. Promotes well-established entries to stable
3. Archives resolved/stale entries
4. Cleans up raw text (removes Python reprs, truncates conversation dumps)
"""

import re
import sqlite3
import time
from typing import Any

from loguru import logger

from divineos.core.knowledge._base import _get_connection

# ─── Layer Constants ──────────────────────────────────────────────────

LAYERS = ("urgent", "active", "stable", "archive")


# ─── Schema Migration ────────────────────────────────────────────────


def ensure_layer_column() -> None:
    """Add the layer column to the knowledge table if missing."""
    conn = _get_connection()
    try:
        conn.execute("ALTER TABLE knowledge ADD COLUMN layer TEXT NOT NULL DEFAULT 'active'")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # column already exists
    finally:
        conn.close()


# ─── Text Cleanup ─────────────────────────────────────────────────────


def clean_entry_text(content: str) -> str:
    """Clean up raw conversational text into something readable.

    Handles:
    - Python repr strings like UserSignal(signal_type=...) → strips them
    - Casual text markers (.., :), contractions) → cleans up
    - "I should: X" → just "X" (type already says DIRECTION)
    - "I decided: X" → just "X" (type already says PRINCIPLE)
    - "I was corrected: X" → just "X"
    - "User correction: X" / "User affirmed: X" → just "X"
    """
    cleaned = content

    # Remove Python repr objects like UserSignal(signal_type='correction', content='...')
    cleaned = re.sub(
        r"UserSignal\(signal_type=['\"]?\w+['\"]?,\s*content=['\"]?",
        "",
        cleaned,
    )
    cleaned = re.sub(r"['\"]?,\s*timestamp=['\"]?[\dT:.-]+['\"]?\)", "", cleaned)

    # Normalize dashes: em dash (—), en dash (–) → double hyphen (--)
    cleaned = cleaned.replace("\u2014", "--").replace("\u2013", "--")

    # Strip stale prefixes — the knowledge TYPE already says what it is
    for prefix_pattern in (
        r"^User correction:\s*",
        r"^User affirmed:\s*",
        r"^I was corrected:\s*",
        r"^I should:\s*",
        r"^I decided:\s*",
    ):
        match = re.match(prefix_pattern, cleaned, re.IGNORECASE)
        if match:
            rest = cleaned[match.end() :].strip()
            if len(rest) > 15:  # Only strip if there's substance after the prefix
                cleaned = rest
                break

    # Clean up "I was X, but got corrected -- Y" → just the Y part
    match = re.match(
        r"I was .{5,80}?,\s*but (?:got corrected|the correct approach is:?)\s*[-—]*\s*(.+)",
        cleaned,
        re.DOTALL,
    )
    if match:
        correction = match.group(1).strip()
        if len(correction) > 20:
            cleaned = correction

    # Clean casual text markers
    cleaned = re.sub(r"\.\.+", ".", cleaned)  # ".." → "."
    cleaned = re.sub(r"\s*:\)+", "", cleaned)  # :)
    cleaned = re.sub(r"\s*lol\b", "", cleaned, flags=re.IGNORECASE)

    # Remove double spaces and normalize whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # Capitalize first letter
    if cleaned and cleaned[0].islower():
        cleaned = cleaned[0].upper() + cleaned[1:]

    # Ensure ends with punctuation
    if cleaned and cleaned[-1] not in ".!?":
        cleaned = cleaned.rstrip(". ") + "."

    return cleaned


def is_raw_transcript_noise(content: str, knowledge_type: str) -> bool:
    """Detect entries that are raw transcript dumps, not distilled knowledge.

    These should be auto-archived during curation — they pollute the briefing.
    """
    if knowledge_type in ("DIRECTIVE", "BOUNDARY"):
        return False  # Never auto-archive rules

    lower = content.lower()

    # Raw user affirmations stored as knowledge
    if re.match(r"^(perfect|wonderful|great|ok|okay|yes)\s", lower):
        words = lower.split()
        # If it's mostly an affirmation with no substance
        if len(words) < 15:
            return True

    # Raw audit/review dumps (long paste-ins from external tools)
    if any(
        marker in lower
        for marker in (
            "audit results:",
            "round 3 audit",
            "round 2 audit",
            "here is the audit",
            "here is the review",
            "here is the report",
            "scrutinized test coverage",
        )
    ):
        return True

    # Messages from other people (not user instructions)
    if any(
        marker in lower
        for marker in (
            "my friend sent",
            "make sure you opt out",
            "allow github to use my data",
        )
    ):
        return True

    # Excessive casual markers in a PRINCIPLE/DIRECTION
    if knowledge_type in ("PRINCIPLE", "DIRECTION"):
        casual_count = len(re.findall(r"\.\.+|:\)|lol\b|haha\b|soooo|:D", lower))
        if casual_count >= 3:
            return True

    return False


# ─── Layer Assignment Rules ───────────────────────────────────────────


def assign_layer(entry: dict[str, Any]) -> str:
    """Determine which layer a knowledge entry belongs in.

    Rules:
    - urgent: Recent corrections (< 24h, source=CORRECTED), active lessons with 3+ occurrences
    - stable: High confidence (>=0.9), high access (>=15), maturity CONFIRMED/TESTED, age > 7 days
    - archive: Very old episodes (>30 days), confidence < 0.3, very stale entries
    - active: Everything else
    """
    now = time.time()
    age_days = (now - entry.get("created_at", now)) / 86400
    confidence = entry.get("confidence", 1.0)
    access = entry.get("access_count", 0)
    maturity = entry.get("maturity", "RAW")
    source = entry.get("source", "INHERITED")
    ktype = entry.get("knowledge_type", "FACT")

    # Directives are always active — operating principles, never hidden
    if ktype == "DIRECTIVE":
        return "active"

    # Urgent: recent corrections or mistakes
    if source == "CORRECTED" and age_days < 1:
        return "urgent"
    if ktype == "MISTAKE" and age_days < 3:
        return "urgent"

    # Archive: stale, low-value, or old episodes
    if confidence < 0.3:
        return "archive"
    if ktype == "EPISODE" and age_days > 30:
        return "archive"
    if ktype == "OBSERVATION" and age_days > 14 and access < 3:
        return "archive"

    # Stable: well-established knowledge
    if (
        confidence >= 0.9
        and access >= 15
        and maturity in ("CONFIRMED", "TESTED")
        and age_days > 7
        and ktype in ("PRINCIPLE", "BOUNDARY", "DIRECTION", "PROCEDURE")
    ):
        return "stable"

    return "active"


# ─── Lesson Layer Assignment ──────────────────────────────────────────


def assign_lesson_layers() -> dict[str, int]:
    """Archive resolved lessons and flag urgent ones.

    Returns counts of changes made.
    """
    conn = _get_connection()
    counts = {"archived": 0, "urgent": 0}
    try:
        # Resolved lessons → archive their linked knowledge
        resolved = conn.execute(
            "SELECT lesson_id, description FROM lesson_tracking WHERE status = 'resolved'"
        ).fetchall()
        for lesson_id, description in resolved:
            # Find knowledge entries linked to this lesson via content overlap
            rows = conn.execute(
                "SELECT knowledge_id FROM knowledge "
                "WHERE superseded_by IS NULL AND layer != 'archive' "
                "AND content LIKE ? LIMIT 5",
                (f"%{description[:50]}%",),
            ).fetchall()
            for (kid,) in rows:
                conn.execute(
                    "UPDATE knowledge SET layer = 'archive' WHERE knowledge_id = ?",
                    (kid,),
                )
                counts["archived"] += 1

        conn.commit()
    except (sqlite3.Error, KeyError, TypeError) as e:
        logger.warning("Lesson layer assignment failed: %s", e)
    finally:
        conn.close()
    return counts


# ─── Full Curation Pass ──────────────────────────────────────────────


def run_curation() -> dict[str, Any]:
    """Run a full curation pass — assign layers, clean text, archive stale entries.

    Called at SESSION_END after knowledge extraction.
    Returns summary of changes made.
    """
    ensure_layer_column()
    conn = _get_connection()
    result: dict[str, Any] = {
        "layers_assigned": 0,
        "text_cleaned": 0,
        "archived": 0,
        "promoted_stable": 0,
        "promoted_urgent": 0,
    }

    try:
        rows = conn.execute(
            "SELECT knowledge_id, created_at, updated_at, knowledge_type, content, "
            "confidence, access_count, superseded_by, source, maturity, "
            "corroboration_count, layer "
            "FROM knowledge WHERE superseded_by IS NULL"
        ).fetchall()

        for row in rows:
            entry = {
                "knowledge_id": row[0],
                "created_at": row[1],
                "updated_at": row[2],
                "knowledge_type": row[3],
                "content": row[4],
                "confidence": row[5],
                "access_count": row[6],
                "superseded_by": row[7],
                "source": row[8],
                "maturity": row[9],
                "corroboration_count": row[10],
                "layer": row[11] if len(row) > 11 else "active",
            }

            # Auto-archive raw transcript noise before layer assignment
            if is_raw_transcript_noise(entry["content"], entry["knowledge_type"]):
                if entry.get("layer") != "archive":
                    conn.execute(
                        "UPDATE knowledge SET layer = 'archive', confidence = 0.1 "
                        "WHERE knowledge_id = ?",
                        (entry["knowledge_id"],),
                    )
                    result["archived"] += 1
                continue

            new_layer = assign_layer(entry)
            old_layer = entry.get("layer", "active")

            # Don't demote from urgent to active within the same day
            # (let urgent entries stay urgent until next curation)
            if old_layer == "urgent" and new_layer == "active":
                age_hours = (time.time() - entry["created_at"]) / 3600
                if age_hours < 24:
                    new_layer = "urgent"

            # Clean up text
            cleaned = clean_entry_text(entry["content"])
            text_changed = cleaned != entry["content"]

            if new_layer != old_layer or text_changed:
                updates = []
                params: list[Any] = []

                if new_layer != old_layer:
                    updates.append("layer = ?")
                    params.append(new_layer)
                    result["layers_assigned"] += 1
                    if new_layer == "archive":
                        result["archived"] += 1
                    elif new_layer == "stable":
                        result["promoted_stable"] += 1
                    elif new_layer == "urgent":
                        result["promoted_urgent"] += 1

                if text_changed:
                    updates.append("content = ?")
                    params.append(cleaned)
                    result["text_cleaned"] += 1

                if updates:
                    params.append(entry["knowledge_id"])
                    conn.execute(
                        f"UPDATE knowledge SET {', '.join(updates)} WHERE knowledge_id = ?",  # nosec B608
                        params,
                    )

        conn.commit()
    except (sqlite3.Error, KeyError, TypeError) as e:
        logger.warning("Curation pass failed: %s", e)
    finally:
        conn.close()

    # Also curate lessons
    lesson_counts = assign_lesson_layers()
    result["archived"] += lesson_counts["archived"]

    return result
