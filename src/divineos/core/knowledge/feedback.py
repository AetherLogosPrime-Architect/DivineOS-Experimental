"""Knowledge feedback — health check, confidence adjustment, effectiveness."""

import time
from typing import Any, cast

from loguru import logger

from divineos.core.constants import (
    CONFIDENCE_LOW,
    DECAY_AGGRESSIVE,
    DECAY_FLOOR,
    DECAY_HEAVY,
    DECAY_MILD,
    MATURITY_HYPOTHESIS_TO_TESTED_CONFIDENCE,
    MATURITY_RAW_TO_HYPOTHESIS_CONFIDENCE,
    MATURITY_TESTED_TO_CONFIRMED_CONFIDENCE,
    OVERLAP_DUPLICATE,
    SECONDS_PER_DAY,
    TIME_STALE_KNOWLEDGE_DAYS,
    TIME_TEMPORAL_DECAY_DAYS,
)
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
            if overlap > OVERLAP_DUPLICATE:
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

    Nothing decays without being seen. A lesson true on day 1 is true
    on day 100. Confidence only changes when there is EVIDENCE:

    1. Confirmed: knowledge keeps coming up across sessions -> trust more
    2. Recurring: a lesson happened 3+ times -> it's clearly a real problem
    3. Resolved: an improving lesson hasn't come back in 30+ days -> probably fixed
    4. Temporal: "currently broken" language becomes stale after 14 days
    5. Contradicted: entries contradicted 3+ times lose confidence
    6. Noise: extraction noise that slipped past old filters gets penalized

    Unseen entries (zero access, 30+ days old) are flagged for review,
    NOT decayed. The briefing surfaces them so someone can decide.
    """
    now = time.time()
    result: dict[str, Any] = {
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
            new_conf = _adjust_confidence(entry["knowledge_id"], DECAY_MILD, cap=1.0)
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
                if overlap > OVERLAP_DUPLICATE:
                    current = mistake["confidence"]
                    if current < 0.95:
                        _adjust_confidence(mistake["knowledge_id"], 0.95 - current)
                        result["recurring_escalated"] += 1
                    break

    # 3. Resolve old improving lessons — hasn't come back in 30 days = fixed
    improving_lessons = get_lessons(status="improving")
    for lesson in improving_lessons:
        age_days = (now - lesson["last_seen"]) / SECONDS_PER_DAY
        if age_days > TIME_STALE_KNOWLEDGE_DAYS:
            _resolve_lesson(lesson["lesson_id"])
            result["resolved_lessons"] += 1
            # Gently lower the associated MISTAKE — the problem went away,
            # but the knowledge is still worth keeping in case it comes back
            for mistake in mistakes:
                overlap = _compute_overlap(lesson["description"], mistake["content"])
                if overlap > OVERLAP_DUPLICATE:
                    _adjust_confidence(mistake["knowledge_id"], -DECAY_MILD, floor=0.5)
                    break

    # 4. Temporal markers only — "currently broken" language becomes stale
    # NOTE: We do NOT decay knowledge just because it hasn't been accessed.
    # Knowledge that's true on day 1 is true on day 100. Nothing decays
    # without being seen first. Only time-sensitive language loses confidence,
    # because the passage of time IS the counter-evidence.
    stale_count = 0
    temporal_decay_count = 0
    needs_review: list[str] = []
    for entry in all_entries:
        if entry["knowledge_type"] == "DIRECTIVE":
            continue

        age_days = (now - entry["created_at"]) / SECONDS_PER_DAY

        # Flag zero-access entries for review (but do NOT decay them)
        if entry["access_count"] == 0 and age_days > TIME_STALE_KNOWLEDGE_DAYS:
            needs_review.append(entry["knowledge_id"])
            stale_count += 1

        # Time-sensitive language older than 14 days decays —
        # "currently broken" after 2 weeks is probably stale
        if age_days > TIME_TEMPORAL_DECAY_DAYS and _has_temporal_markers(entry["content"]):
            new_conf = _adjust_confidence(entry["knowledge_id"], -DECAY_MILD, floor=DECAY_FLOOR)
            if new_conf is not None:
                temporal_decay_count += 1

    # 5. High contradiction count — entries contradicted 3+ times are suspect
    contradiction_flagged = 0
    for entry in all_entries:
        if entry.get("contradiction_count", 0) >= 3 and entry["confidence"] > CONFIDENCE_LOW:
            _adjust_confidence(entry["knowledge_id"], -DECAY_AGGRESSIVE, floor=DECAY_FLOOR)
            contradiction_flagged += 1

    # 6. Abandoned knowledge — previously decayed, now just tracked.
    # Knowledge that was accessed but idle does NOT decay. Being unused
    # is not evidence of being wrong. Nothing fades without being seen.
    abandoned_count = 0

    result["stale_decayed"] = 0  # No longer decays — flagged for review instead
    result["needs_review"] = needs_review
    result["needs_review_count"] = stale_count
    result["temporal_decayed"] = temporal_decay_count
    result["contradiction_flagged"] = contradiction_flagged
    result["abandoned_decayed"] = abandoned_count

    # 7. Retroactive noise sweep — re-evaluate existing entries against
    # the current noise filter. Entries that slipped in before the filter
    # was improved get penalized or superseded.
    noise_penalized = 0
    noise_superseded = 0
    conn_noise = _get_connection()
    try:
        for entry in all_entries:
            # Already superseded — leave it alone
            if entry.get("superseded_by"):
                continue
            if not _is_extraction_noise(entry["content"], entry["knowledge_type"]):
                continue

            # Already below floor — supersede it. This breaks the infinite
            # loop where entries sit at 0.1 forever being re-scanned.
            if entry["confidence"] <= 0.2:
                conn_noise.execute(
                    "UPDATE knowledge SET superseded_by = 'noise-sweep' WHERE knowledge_id = ?",
                    (entry["knowledge_id"],),
                )
                noise_superseded += 1
                continue

            new_conf = _adjust_confidence(entry["knowledge_id"], -DECAY_HEAVY, floor=0.1)
            if new_conf is not None:
                noise_penalized += 1
        if noise_superseded:
            conn_noise.commit()
    finally:
        conn_noise.close()
    result["noise_penalized"] = noise_penalized
    result["noise_superseded"] = noise_superseded

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
            if maturity == "CONFIRMED" and confidence < MATURITY_TESTED_TO_CONFIRMED_CONFIDENCE:
                new_maturity = "RAW"
            elif maturity == "TESTED" and confidence < MATURITY_HYPOTHESIS_TO_TESTED_CONFIDENCE:
                new_maturity = "RAW"
            elif maturity == "HYPOTHESIS" and confidence < MATURITY_RAW_TO_HYPOTHESIS_CONFIDENCE:
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
