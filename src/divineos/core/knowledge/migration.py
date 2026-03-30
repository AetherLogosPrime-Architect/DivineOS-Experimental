"""Knowledge migration, lesson categorization, session feedback, health report."""

import re
from typing import Any
import sqlite3

from divineos.core.knowledge._base import (
    _get_connection,
)
from divineos.core.knowledge._text import (
    _compute_overlap,
    _is_extraction_noise,
)
from divineos.core.knowledge.crud import (
    get_knowledge,
    record_access,
    store_knowledge,
)
from divineos.core.knowledge.feedback import (
    _adjust_confidence,
    compute_effectiveness,
)
from divineos.core.knowledge.lessons import (
    get_lessons,
    mark_lesson_improving,
    record_lesson,
)

_MIGRATION_ERRORS = (
    ImportError,
    sqlite3.OperationalError,
    OSError,
    KeyError,
    TypeError,
    ValueError,
)


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
                except _MIGRATION_ERRORS:
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
