"""Knowledge feedback — health check, confidence adjustment, effectiveness."""

import time
from typing import Any, cast

from loguru import logger

from divineos.core.knowledge._base import (
    _get_connection,
)
from divineos.core.knowledge._text import (
    _compute_overlap,
    _has_temporal_markers,
    _is_extraction_noise,
)
from divineos.core.knowledge.crud import (
    get_knowledge,
)
from divineos.core.knowledge.lessons import (
    get_lessons,
)


# ─── Confidence Adjustment ───────────────────────────────────────────


def _adjust_confidence(
    knowledge_id: str,
    delta: float,
    floor: float = 0.1,
    cap: float = 1.0,
) -> float | None:
    """Adjust confidence on a knowledge entry in-place.

    This is metadata (belief strength), not content — so in-place update
    is appropriate (same pattern as record_access updating access_count).

    Returns the new confidence, or None if the entry doesn't exist.
    """
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT confidence FROM knowledge WHERE knowledge_id = ? AND superseded_by IS NULL",
            (knowledge_id,),
        ).fetchone()
        if not row:
            return None

        new_conf = max(floor, min(cap, cast("float", row[0]) + delta))
        conn.execute(
            "UPDATE knowledge SET confidence = ?, updated_at = ? WHERE knowledge_id = ?",
            (new_conf, time.time(), knowledge_id),
        )
        conn.commit()
        return new_conf
    finally:
        conn.close()


def _resolve_lesson(lesson_id: str) -> None:
    """Mark a lesson as resolved."""
    conn = _get_connection()
    try:
        conn.execute(
            "UPDATE lesson_tracking SET status = 'resolved' WHERE lesson_id = ?",
            (lesson_id,),
        )
        conn.commit()
    finally:
        conn.close()


# ─── Effectiveness ───────────────────────────────────────────────────


def compute_effectiveness(entry: dict[str, Any]) -> dict[str, Any]:
    """Compute effectiveness status for a knowledge entry.

    Returns {"status": "...", "detail": "..."} based on the entry's type
    and how it connects to lesson tracking and access patterns.
    """
    ktype = entry.get("knowledge_type", "")
    access = entry.get("access_count", 0)

    if ktype in ("MISTAKE", "BOUNDARY", "PRINCIPLE"):
        # Check if a lesson tracks this knowledge
        lessons = get_lessons()
        for lesson in lessons:
            overlap = _compute_overlap(entry.get("content", ""), lesson["description"])
            if overlap > 0.4:
                if lesson["status"] in ("improving", "resolved"):
                    return {
                        "status": "effective",
                        "detail": f"Lesson {lesson['status']} ({lesson['occurrences']} past occurrences)",
                    }
                if lesson["status"] == "active" and lesson["occurrences"] >= 3:
                    return {
                        "status": "recurring",
                        "detail": f"Still recurring ({lesson['occurrences']} occurrences)",
                    }
                if lesson["status"] == "active":
                    return {
                        "status": "active",
                        "detail": f"Tracked ({lesson['occurrences']} occurrences)",
                    }
        # No matching lesson — classify by usage instead of "unknown"
        if access > 3:
            return {"status": "stable", "detail": f"No lesson match but accessed {access} times"}
        if access > 0:
            return {"status": "used", "detail": f"Accessed {access} times, no lesson match"}
        return {"status": "unknown", "detail": "No lesson tracking data and never accessed"}

    if ktype in ("PATTERN", "PROCEDURE", "OBSERVATION"):
        if access > 3:
            return {"status": "reinforced", "detail": f"Confirmed {access} times"}
        if access > 0:
            return {"status": "used", "detail": f"Accessed {access} times"}
        return {"status": "unused", "detail": "Never accessed"}

    if ktype in ("PREFERENCE", "DIRECTION", "DIRECTIVE"):
        return {"status": "stable", "detail": "Directions and directives are always active"}

    if ktype == "FACT":
        if access > 0:
            return {"status": "used", "detail": f"Accessed {access} times"}
        return {"status": "unused", "detail": "Never accessed"}

    # EPISODE or unknown
    return {"status": "stable", "detail": "Record entry"}


# ─── Health Check ────────────────────────────────────────────────────


def health_check() -> dict[str, Any]:
    """Review the knowledge store and adjust confidence scores.

    Knowledge does NOT decay just because time passed. A lesson that's
    true on day 1 is still true on day 100. Confidence only changes when:

    1. Confirmed: knowledge keeps coming up across sessions → trust more
    2. Recurring: a lesson happened 3+ times → it's clearly a real problem
    3. Resolved: an improving lesson hasn't come back in 30+ days → probably fixed
    4. Contradicted: a superseded entry already gets marked by update_knowledge
    """
    now = time.time()
    result = {
        "confirmed_boosted": 0,
        "recurring_escalated": 0,
        "resolved_lessons": 0,
        "total_checked": 0,
    }

    health_limit = 1000
    all_entries = get_knowledge(limit=health_limit)
    result["total_checked"] = len(all_entries)
    if len(all_entries) >= health_limit:
        logger.warning(
            f"Health check limited to {health_limit} entries — some entries may not be checked"
        )

    # 1. Confirmed boost — if something keeps coming up, it's clearly useful
    # Skip entries that are extraction noise or raw user quotes —
    # inflated access counts from the old feedback loop should not boost garbage.
    _raw_prefixes = ("i should:", "i was corrected:", "i was bash:", "i decided:")
    for entry in all_entries:
        if entry["access_count"] > 5 and entry["confidence"] < 1.0:
            if _is_extraction_noise(entry["content"], entry["knowledge_type"]):
                continue
            if entry["content"].strip().lower().startswith(_raw_prefixes):
                continue
            new_conf = _adjust_confidence(entry["knowledge_id"], 0.05, cap=1.0)
            if new_conf is not None:
                result["confirmed_boosted"] += 1

    # 2. Recurring lesson escalation — same mistake 3+ times = serious problem
    active_lessons = get_lessons(status="active")
    mistakes = [
        e for e in all_entries if e["knowledge_type"] in ("MISTAKE", "BOUNDARY", "PRINCIPLE")
    ]
    for lesson in active_lessons:
        if lesson["occurrences"] >= 3:
            for mistake in mistakes:
                overlap = _compute_overlap(lesson["description"], mistake["content"])
                if overlap > 0.4:
                    current = mistake["confidence"]
                    if current < 0.95:
                        _adjust_confidence(mistake["knowledge_id"], 0.95 - current)
                        result["recurring_escalated"] += 1
                    break

    # 3. Resolve old improving lessons — hasn't come back in 30 days = fixed
    improving_lessons = get_lessons(status="improving")
    for lesson in improving_lessons:
        age_days = (now - lesson["last_seen"]) / 86400
        if age_days > 30:
            _resolve_lesson(lesson["lesson_id"])
            result["resolved_lessons"] += 1
            # Gently lower the associated MISTAKE — the problem went away,
            # but the knowledge is still worth keeping in case it comes back
            for mistake in mistakes:
                overlap = _compute_overlap(lesson["description"], mistake["content"])
                if overlap > 0.4:
                    _adjust_confidence(mistake["knowledge_id"], -0.05, floor=0.5)
                    break

    # 4. Stale knowledge — unused entries lose confidence over time
    stale_count = 0
    temporal_decay_count = 0
    for entry in all_entries:
        # DIRECTIVE is permanent by design — immune to staleness
        if entry["knowledge_type"] == "DIRECTIVE":
            continue

        age_days = (now - entry["created_at"]) / 86400

        # Zero-access entries older than 30 days decay
        if age_days > 30 and entry["access_count"] == 0:
            new_conf = _adjust_confidence(entry["knowledge_id"], -0.1, floor=0.2)
            if new_conf is not None:
                stale_count += 1

        # Time-sensitive language older than 14 days decays faster
        elif age_days > 14 and _has_temporal_markers(entry["content"]):
            new_conf = _adjust_confidence(entry["knowledge_id"], -0.05, floor=0.3)
            if new_conf is not None:
                temporal_decay_count += 1

    # 5. High contradiction count — entries contradicted 3+ times are suspect
    contradiction_flagged = 0
    for entry in all_entries:
        if entry.get("contradiction_count", 0) >= 3 and entry["confidence"] > 0.4:
            _adjust_confidence(entry["knowledge_id"], -0.2, floor=0.3)
            contradiction_flagged += 1

    # 6. Abandoned knowledge — accessed but then left untouched for 14+ days
    abandoned_count = 0
    for entry in all_entries:
        if entry["knowledge_type"] == "DIRECTIVE":
            continue
        # Must have been accessed at least once (distinguishes from "never used")
        if entry["access_count"] < 1:
            continue
        # Check time since last update (proxy for last meaningful interaction)
        days_since_update = (now - entry["updated_at"]) / 86400
        if days_since_update > 14 and entry["confidence"] > 0.3:
            new_conf = _adjust_confidence(entry["knowledge_id"], -0.02, floor=0.3)
            if new_conf is not None:
                abandoned_count += 1

    result["stale_decayed"] = stale_count
    result["temporal_decayed"] = temporal_decay_count
    result["contradiction_flagged"] = contradiction_flagged
    result["abandoned_decayed"] = abandoned_count

    # 7. Retroactive noise sweep — re-evaluate existing entries against
    # the current noise filter. Entries that slipped in before the filter
    # was improved get their confidence penalized (not deleted — append-only).
    noise_penalized = 0
    for entry in all_entries:
        # Already low confidence — no point penalizing further
        if entry["confidence"] <= 0.2:
            continue
        # Already superseded — leave it alone
        if entry.get("superseded_by"):
            continue
        if _is_extraction_noise(entry["content"], entry["knowledge_type"]):
            new_conf = _adjust_confidence(entry["knowledge_id"], -0.3, floor=0.1)
            if new_conf is not None:
                noise_penalized += 1
    result["noise_penalized"] = noise_penalized

    # 8. Maturity demotion — entries that reached high maturity through
    # inflated counts but now have low confidence should be demoted.
    # A CONFIRMED entry at 0.3 or below is not confirmed by any honest measure.
    demoted = 0
    conn = _get_connection()
    try:
        high_maturity = conn.execute(
            "SELECT knowledge_id, maturity, confidence FROM knowledge "
            "WHERE superseded_by IS NULL AND maturity IN ('CONFIRMED', 'TESTED', 'HYPOTHESIS')"
        ).fetchall()
        for kid, maturity, confidence in high_maturity:
            new_maturity = None
            if maturity == "CONFIRMED" and confidence < 0.8:
                new_maturity = "RAW"
            elif maturity == "TESTED" and confidence < 0.5:
                new_maturity = "RAW"
            elif maturity == "HYPOTHESIS" and confidence < 0.4:
                new_maturity = "RAW"
            if new_maturity:
                conn.execute(
                    "UPDATE knowledge SET maturity = ? WHERE knowledge_id = ?",
                    (new_maturity, kid),
                )
                demoted += 1
        if demoted:
            conn.commit()
    finally:
        conn.close()
    result["maturity_demoted"] = demoted

    return result
