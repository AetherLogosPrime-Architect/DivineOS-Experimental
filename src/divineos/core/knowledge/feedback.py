"""Knowledge feedback — health check, confidence adjustment, migration, categorization."""

import re
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
    record_access,
    store_knowledge,
)
from divineos.core.knowledge.lessons import (
    get_lessons,
    mark_lesson_improving,
    record_lesson,
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


# ─── Knowledge Type Migration ────────────────────────────────────────

# How old types map to new types
_MIGRATION_RULES: dict[str, dict[str, Any]] = {
    "MISTAKE": {
        # Keywords that indicate a hard constraint → BOUNDARY
        "boundary_keywords": re.compile(
            r"\b(never|always|must|don't|do not|cannot|forbidden|prohibited)\b",
            re.IGNORECASE,
        ),
        "default": "PRINCIPLE",  # teaching/direction
        "boundary": "BOUNDARY",  # hard constraint
        "source": "CORRECTED",
        "default_maturity": "HYPOTHESIS",
        "boundary_maturity": "TESTED",
    },
    "PREFERENCE": {
        "new_type": "DIRECTION",
        "source": "STATED",
        "maturity": "CONFIRMED",
    },
    "PATTERN": {
        # Keywords indicating how-to → PROCEDURE
        "procedure_keywords": re.compile(
            r"\b(step|how to|process|workflow|first.*then|procedure)\b",
            re.IGNORECASE,
        ),
        "default": "PRINCIPLE",
        "procedure": "PROCEDURE",
        "source": "DEMONSTRATED",
        "maturity": "HYPOTHESIS",
    },
}


def migrate_knowledge_types(dry_run: bool = True) -> list[dict[str, Any]]:
    """Reclassify old-type entries (MISTAKE, PATTERN, PREFERENCE) to new types.

    Uses the supersede pattern: old entry gets superseded_by pointing to new entry.
    In dry_run mode, returns planned changes without writing anything.

    Returns list of {"old_id", "old_type", "new_type", "source", "maturity", "content"}.
    """
    planned: list[dict[str, Any]] = []

    for old_type, rules in _MIGRATION_RULES.items():
        entries = get_knowledge(knowledge_type=old_type, limit=1000)
        for entry in entries:
            content = entry["content"]

            # Skip noise and session-specific entries — don't promote them
            if _is_extraction_noise(content, old_type):
                continue
            from divineos.core.memory import _is_session_specific

            if _is_session_specific(content):
                continue

            if old_type == "MISTAKE":
                if rules["boundary_keywords"].search(content):
                    new_type = rules["boundary"]
                    maturity = rules["boundary_maturity"]
                else:
                    new_type = rules["default"]
                    maturity = rules["default_maturity"]
                source = rules["source"]

            elif old_type == "PREFERENCE":
                new_type = rules["new_type"]
                source = rules["source"]
                maturity = rules["maturity"]

            elif old_type == "PATTERN":
                if rules["procedure_keywords"].search(content):
                    new_type = rules["procedure"]
                else:
                    new_type = rules["default"]
                source = rules["source"]
                maturity = rules["maturity"]

            else:
                continue

            change = {
                "old_id": entry["knowledge_id"],
                "old_type": old_type,
                "new_type": new_type,
                "source": source,
                "maturity": maturity,
                "content": content[:200],
            }
            planned.append(change)

            if not dry_run:
                # Mark old entry as superseded FIRST (so store_knowledge
                # doesn't dedup against it via content_hash)
                placeholder = "migrating"
                conn = _get_connection()
                try:
                    conn.execute(
                        "UPDATE knowledge SET superseded_by = ? WHERE knowledge_id = ?",
                        (placeholder, entry["knowledge_id"]),
                    )
                    conn.commit()
                finally:
                    conn.close()

                try:
                    # Create new entry with new type
                    new_kid = store_knowledge(
                        knowledge_type=new_type,
                        content=content,
                        confidence=entry["confidence"],
                        source_events=entry.get("source_events", []),
                        tags=entry.get("tags", []),
                        source=source,
                        maturity=maturity,
                    )
                except Exception:
                    # Rollback: clear the placeholder so old entry isn't orphaned
                    conn = _get_connection()
                    try:
                        conn.execute(
                            "UPDATE knowledge SET superseded_by = NULL WHERE knowledge_id = ?",
                            (entry["knowledge_id"],),
                        )
                        conn.commit()
                    finally:
                        conn.close()
                    raise

                # Update superseded_by to point to actual new ID
                conn = _get_connection()
                try:
                    conn.execute(
                        "UPDATE knowledge SET superseded_by = ? WHERE knowledge_id = ?",
                        (new_kid, entry["knowledge_id"]),
                    )
                    conn.commit()
                finally:
                    conn.close()
                change["new_id"] = new_kid

    return planned


# ─── Lesson Categorization ────────────────────────────────────────────

# Semantic lesson categories — corrections get mapped to these buckets
# based on keyword matching, instead of using raw word fragments.
_LESSON_CATEGORIES = (
    (
        "blind_coding",
        re.compile(
            r"\bblind|without reading|without checking|without looking|study.+first|"
            r"understand.+before|research.+first|don.t just|not blindly",
            re.IGNORECASE,
        ),
    ),
    (
        "incomplete_fix",
        re.compile(
            r"\bonly fixed one|didn.t fix|still broken|still fail|also fail|"
            r"missed.+other|forgot.+other|the rest",
            re.IGNORECASE,
        ),
    ),
    (
        "ignored_instruction",
        re.compile(
            r"\bdid you not see|did you not read|i already said|i told you|"
            r"i just said|not listening|ignoring what",
            re.IGNORECASE,
        ),
    ),
    (
        "wrong_scope",
        re.compile(
            r"\bi mean.+(?:in|the|this)|not that.+(?:this|the)|wrong (?:file|place|thing)|"
            r"\binstead of\b.+\d|folder.+instead",
            re.IGNORECASE,
        ),
    ),
    (
        "overreach",
        re.compile(
            r"\bnot supposed to|isnt supposed|shouldn.t (?:make|decide|choose)|"
            r"don.t (?:make|decide).+decision|"
            r"\btoo (?:much|far|complex)|over.?engineer|rabbit hole|scope",
            re.IGNORECASE,
        ),
    ),
    (
        "jargon_usage",
        re.compile(
            r"\bjargon|plain english|like.+(?:dumb|stupid|5|new)|break it down|"
            r"\bsimpl(?:e|ify|er)|not a coder|don.t speak",
            re.IGNORECASE,
        ),
    ),
    (
        "shallow_output",
        re.compile(
            r"\bdoesn.t feel|don.t feel|still feel|not.+(?:like people|real|alive|genuine)|"
            r"\bembody|more (?:life|depth|soul)|concise.+not.+concern|token limit",
            re.IGNORECASE,
        ),
    ),
    (
        "perspective_error",
        re.compile(
            r"\bpronoun|when i say you|say i or me|possessive|first person|"
            r"\bperspective|point of view",
            re.IGNORECASE,
        ),
    ),
    (
        "misunderstood",
        re.compile(
            r"\bno i mean|that.s not what|misunderst|wrong idea|confused about|"
            r"\bwhat i meant|trying to stop you|wasn.t denying",
            re.IGNORECASE,
        ),
    ),
)


def _categorize_correction(text: str) -> str | None:
    """Map a correction's text to a semantic lesson category.

    Returns None if no category matches (the correction is probably noise).
    """
    for category, pattern in _LESSON_CATEGORIES:
        if pattern.search(text):
            return category
    return None


def _is_noise_correction(text: str) -> bool:
    """Return True if a correction is noise — not a real lesson.

    Filters: too short, file path dumps, task notifications, forwarded
    messages that are instructions rather than corrections.
    """
    stripped = text.strip()

    # Too short to be meaningful
    if len(stripped) < 20:
        return True

    # Task notification XML
    if "<task-notification>" in stripped or "<task-id>" in stripped:
        return True

    # File path dump (starts with @ and a path)
    if stripped.startswith("@") and ("\\" in stripped[:60] or "/" in stripped[:60]):
        return True

    # Mostly file paths
    path_chars = stripped.count("\\") + stripped.count("/")
    return bool(path_chars > 5 and path_chars > len(stripped) / 20)


# ─── Session Feedback ────────────────────────────────────────────────


def apply_session_feedback(
    analysis: "Any",  # SessionAnalysis
    session_id: str,
) -> dict[str, Any]:
    """Compare new session findings against existing knowledge.

    Called after scan --store. Checks if corrections match existing MISTAKEs
    (recurrences), if encouragements confirm PATTERNs, and marks lessons
    as improving when no matching correction is found.

    Corrections are filtered for noise and categorized into semantic buckets
    before recording lessons.
    """
    result = {
        "recurrences_found": 0,
        "patterns_reinforced": 0,
        "lessons_improving": 0,
        "noise_skipped": 0,
    }

    corrections = getattr(analysis, "corrections", [])
    encouragements = getattr(analysis, "encouragements", [])

    # Step A: Check corrections against existing mistakes/boundaries/principles
    existing_corrections = []
    for ktype in ("MISTAKE", "BOUNDARY", "PRINCIPLE"):
        existing_corrections.extend(get_knowledge(knowledge_type=ktype, limit=200))

    for correction in corrections:
        # Skip noise
        if _is_noise_correction(correction.content):
            result["noise_skipped"] += 1
            continue

        for entry in existing_corrections:
            overlap = _compute_overlap(correction.content, entry["content"])
            if overlap > 0.4:
                _adjust_confidence(entry["knowledge_id"], 0.05, cap=1.0)
                result["recurrences_found"] += 1
                # Record in lesson tracking with semantic category
                category = _categorize_correction(correction.content)
                if category:
                    record_lesson(category, correction.content[:200], session_id)
                break

    # Step B: Check encouragements against existing patterns/principles
    existing_positives = []
    for ktype in ("PATTERN", "PRINCIPLE"):
        existing_positives.extend(get_knowledge(knowledge_type=ktype, limit=200))
    for enc in encouragements:
        for entry in existing_positives:
            overlap = _compute_overlap(enc.content, entry["content"])
            if overlap > 0.4:
                _adjust_confidence(entry["knowledge_id"], 0.05, cap=1.0)
                record_access(entry["knowledge_id"])
                result["patterns_reinforced"] += 1
                break

    # Step C: Mark lessons improving when no matching correction
    active_lessons = get_lessons(status="active")
    for lesson in active_lessons:
        recurred = False
        for correction in corrections:
            if _is_noise_correction(correction.content):
                continue
            overlap = _compute_overlap(correction.content, lesson["description"])
            if overlap > 0.4:
                recurred = True
                break
        if not recurred:
            mark_lesson_improving(lesson["category"], session_id)
            result["lessons_improving"] += 1

    return result


# ─── Health Report ───────────────────────────────────────────────────


def knowledge_health_report() -> dict[str, Any]:
    """Aggregate effectiveness stats across all active knowledge."""
    entries = get_knowledge(limit=1000)
    by_status: dict[str, int] = {}
    by_type: dict[str, dict[str, int]] = {}

    for entry in entries:
        eff = compute_effectiveness(entry)
        status = eff["status"]
        ktype = entry["knowledge_type"]

        by_status[status] = by_status.get(status, 0) + 1
        if ktype not in by_type:
            by_type[ktype] = {}
        by_type[ktype][status] = by_type[ktype].get(status, 0) + 1

    return {
        "total": len(entries),
        "by_status": by_status,
        "by_type": by_type,
    }
