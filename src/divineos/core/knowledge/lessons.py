"""Lesson tracking — record, query, summarize, extract from reports."""

import json
import math
import re
import sqlite3
import time
import uuid
from typing import Any, cast

from loguru import logger

from divineos.core.constants import (
    CONFIDENCE_ACTIVE_MEMORY_FLOOR,
    CONFIDENCE_RELIABLE,
    CONFIDENCE_VERY_HIGH,
    LESSON_ABSENCE_DAYS,
    LESSON_MIN_RESOLUTION_DAYS,
    LESSON_MIN_STIMULUS_SESSIONS,
    SECONDS_PER_DAY,
)
from divineos.core.knowledge._base import (
    _get_connection,
    _lesson_row_to_dict,
    compute_hash,
)
from divineos.core.knowledge.crud import (
    store_knowledge,
)
from divineos.core.knowledge.curation import clean_entry_text
from divineos.core.knowledge.extraction import store_knowledge_smart

_LESSONS_ERRORS = (
    ImportError,
    sqlite3.OperationalError,
    OSError,
    KeyError,
    TypeError,
    ValueError,
    json.JSONDecodeError,
)


def _ensure_regressions_column(conn: Any) -> None:
    """Add the regressions column if it doesn't exist yet."""
    try:
        conn.execute(
            "ALTER TABLE lesson_tracking ADD COLUMN regressions INTEGER NOT NULL DEFAULT 0"
        )
    except sqlite3.OperationalError:
        pass  # Column already exists


# How many regressions before a lesson is flagged for directive promotion.
REGRESSION_ESCALATION_THRESHOLD = 3

# Scale effective occurrences logarithmically for auto-resolve math.
# A lesson with 178 occurrences shouldn't need 183 clean sessions,
# but it shouldn't be capped at 10 either — that hides chronic failure.
# log2(178) ≈ 7.5 → needs ~13 sessions. log2(10) ≈ 3.3 → needs ~8.
# Minimum effective is 5 (the base threshold never drops below that).
LESSON_EFFECTIVE_MIN = 5


def record_lesson(category: str, description: str, session_id: str, agent: str = "unknown") -> str:
    """Record a lesson or update an existing one for the same category.

    If a lesson with the same category already exists:
      - Increment occurrences
      - Add session_id to the sessions list
      - Update last_seen timestamp
      - Detect regression: if status was 'improving', track it

    Regression detection: if a lesson was IMPROVING and the mistake recurs,
    that's a regression. After REGRESSION_ESCALATION_THRESHOLD regressions,
    the lesson is flagged for directive promotion — structure over willpower.

    Args:
        agent: Which AI agent made the mistake (e.g. 'claude-opus', 'claude-haiku').

    Returns the lesson_id.
    """
    # Distill the description — no raw transcript quotes as lesson text
    description = clean_entry_text(description)

    now = time.time()
    conn = _get_connection()
    try:
        _ensure_regressions_column(conn)

        # Check if a lesson with same category exists
        existing = conn.execute(
            "SELECT lesson_id, occurrences, sessions, status FROM lesson_tracking WHERE category = ?",
            (category,),
        ).fetchone()

        if existing:
            lesson_id = existing[0]
            sessions = json.loads(existing[2])
            old_status = existing[3] if len(existing) > 3 else "active"
            # Only bump occurrences for genuinely new sessions — prevents
            # re-scans and compaction re-triggers from inflating counts.
            if session_id not in sessions:
                occurrences = existing[1] + 1
                sessions.append(session_id)
            else:
                occurrences = existing[1]

            # Regression detection: was IMPROVING, now recurring again
            regression_bump = 0
            if old_status == "improving":
                regression_bump = 1
                logger.info(
                    "Lesson '%s' REGRESSED: was improving, mistake recurred (session %s)",
                    category,
                    session_id[:12],
                )

            # Update description only if the old one is a seed placeholder.
            # Don't replace a curated description with raw correction text.
            old_desc = conn.execute(
                "SELECT description FROM lesson_tracking WHERE lesson_id = ?",
                (lesson_id,),
            ).fetchone()
            old_desc_text = old_desc[0] if old_desc else ""
            if old_desc_text.startswith("(seeded)"):
                use_desc = description
            else:
                use_desc = old_desc_text
            conn.execute(
                """UPDATE lesson_tracking
                   SET occurrences = ?, last_seen = ?, sessions = ?, status = 'active',
                       description = ?, regressions = regressions + ?
                   WHERE lesson_id = ?""",
                (occurrences, now, json.dumps(sessions), use_desc, regression_bump, lesson_id),
            )
            conn.commit()

            # Corroborate linked knowledge — when a lesson recurs, it means
            # the pattern was observed again. Find knowledge entries whose
            # content references this lesson category and boost them.
            try:
                # Late import: lessons -> knowledge_maintenance -> logic_validation cycle
                from divineos.core.knowledge_maintenance import (
                    increment_corroboration,
                    promote_maturity,
                )

                cat_words = category.replace("_", " ")
                linked = conn.execute(
                    "SELECT knowledge_id FROM knowledge "
                    "WHERE superseded_by IS NULL AND confidence >= ? "
                    "AND (LOWER(content) LIKE ? OR LOWER(content) LIKE ?)",
                    (CONFIDENCE_ACTIVE_MEMORY_FLOOR, f"%{cat_words}%", f"%{category}%"),
                ).fetchall()
                for (kid,) in linked:
                    increment_corroboration(kid, source_context=f"lesson:{category}")
                    promote_maturity(kid)
            except _LESSONS_ERRORS as e:
                logger.debug(
                    "Corroboration sweep failed (best-effort, lesson recording unaffected): %s", e
                )

            return cast("str", lesson_id)

        lesson_id = str(uuid.uuid4())
        content_hash = compute_hash(f"{category}:{description}")
        conn.execute(
            """INSERT INTO lesson_tracking
               (lesson_id, created_at, category, description, first_session,
                occurrences, last_seen, sessions, status, content_hash, agent)
               VALUES (?, ?, ?, ?, ?, 1, ?, ?, 'active', ?, ?)""",
            (
                lesson_id,
                now,
                category,
                description,
                session_id,
                now,
                json.dumps([session_id]),
                content_hash,
                agent,
            ),
        )
        conn.commit()
        return lesson_id
    finally:
        conn.close()


def get_lessons(
    status: str | None = None,
    category: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Get lessons, optionally filtered by status or category."""
    conn = _get_connection()
    try:
        _ensure_regressions_column(conn)
        query = "SELECT lesson_id, created_at, category, description, first_session, occurrences, last_seen, sessions, status, content_hash, agent, regressions FROM lesson_tracking"
        conditions: list[str] = []
        params: list[Any] = []

        if status:
            conditions.append("status = ?")
            params.append(status)
        if category:
            conditions.append("category = ?")
            params.append(category)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY last_seen DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        return [_lesson_row_to_dict(row) for row in rows]
    finally:
        conn.close()


def mark_lesson_improving(category: str, clean_session_id: str) -> None:
    """Mark a lesson as 'improving' when a session passes without the mistake.

    Called when a session is analyzed and does NOT have a mistake in this category.
    Only affects lessons that have occurred 3+ times.
    """
    conn = _get_connection()
    try:
        existing = conn.execute(
            "SELECT lesson_id, occurrences, status, sessions FROM lesson_tracking WHERE category = ? AND status = 'active'",
            (category,),
        ).fetchone()
        if existing and existing[1] >= 3:
            # Track which session triggered the improvement
            sessions_list = json.loads(existing[3]) if existing[3] else []
            if clean_session_id not in sessions_list:
                sessions_list.append(clean_session_id)
            conn.execute(
                "UPDATE lesson_tracking SET status = 'improving', sessions = ?, last_seen = ? WHERE lesson_id = ?",
                (json.dumps(sessions_list), time.time(), existing[0]),
            )
            conn.commit()
    finally:
        conn.close()


def get_lesson_summary() -> str:
    """Generate a plain English summary of active and improving lessons."""
    lessons = get_lessons()
    if not lessons:
        return "No lessons tracked yet."

    # Only show lessons that have actually fired — seeded lessons at 1 occurrence
    # with "(seeded)" descriptions have never been triggered by real behavior.
    active = [
        lesson
        for lesson in lessons
        if lesson["status"] == "active"
        and not (lesson["occurrences"] <= 1 and lesson["description"].startswith("(seeded)"))
    ]
    improving = [lesson for lesson in lessons if lesson["status"] == "improving"]

    lines = [f"### ACTIVE LESSONS ({len(active) + len(improving)})"]

    for lesson in active:
        regressions = lesson.get("regressions", 0)
        suffix = ""
        if regressions >= REGRESSION_ESCALATION_THRESHOLD:
            suffix = " [ESCALATE: consider making this a directive]"
        elif regressions > 0:
            suffix = f" [regressed {regressions}x]"
        lines.append(
            f"- [{lesson['occurrences']}x] {lesson['description']} (last: {lesson['category']}){suffix}",
        )

    for lesson in improving:
        lines.append(f"- IMPROVING (was {lesson['occurrences']}x): {lesson['description']}")

    if not active and not improving:
        return "No lessons tracked yet."

    return "\n".join(lines)


def get_escalation_candidates() -> list[dict[str, Any]]:
    """Find lessons that have regressed enough times to warrant directive promotion.

    A lesson that keeps cycling between IMPROVING and ACTIVE isn't being
    solved by awareness alone — it needs structural enforcement (a directive).
    """
    conn = _get_connection()
    try:
        _ensure_regressions_column(conn)
        rows = conn.execute(
            "SELECT lesson_id, created_at, category, description, first_session, "
            "occurrences, last_seen, sessions, status, content_hash, agent, regressions "
            "FROM lesson_tracking WHERE regressions >= ?",
            (REGRESSION_ESCALATION_THRESHOLD,),
        ).fetchall()
        return [_lesson_row_to_dict(row) for row in rows]
    finally:
        conn.close()


def escalate_chronic_lessons() -> list[str]:
    """Auto-promote lessons with 3+ regressions to DIRECTIVE knowledge entries.

    A lesson that keeps cycling between IMPROVING and ACTIVE isn't being
    solved by awareness alone — it needs structural enforcement. Instead
    of just appending "[ESCALATE]" text to the summary, this creates an
    actual DIRECTIVE entry in the knowledge store that will surface in
    briefings with high priority.

    Returns list of created knowledge IDs.
    """
    candidates = get_escalation_candidates()
    if not candidates:
        return []

    created_ids: list[str] = []
    for lesson in candidates:
        category = lesson["category"]
        description = lesson["description"]
        regressions = lesson.get("regressions", 0)
        occurrences = lesson["occurrences"]

        # Check if a directive already exists for this category
        conn = _get_connection()
        try:
            existing = conn.execute(
                "SELECT knowledge_id FROM knowledge "
                "WHERE knowledge_type = 'DIRECTIVE' AND superseded_by IS NULL "
                "AND LOWER(content) LIKE ?",
                (f"%{category.lower()}%",),
            ).fetchone()
        finally:
            conn.close()

        if existing:
            # Directive already exists — don't create duplicates
            continue

        content = (
            f"STRUCTURAL ENFORCEMENT: {description} "
            f"This lesson regressed {regressions}x across {occurrences} occurrences. "
            f"Awareness alone is insufficient — enforce structurally. "
            f"Category: {category}."
        )

        kid = store_knowledge_smart(
            knowledge_type="DIRECTIVE",
            content=content,
            confidence=CONFIDENCE_RELIABLE,
            source_events=[],
            tags=["auto-escalated", f"lesson-{category}", "regression-enforcement"],
            source="SYNTHESIZED",
        )
        if kid:
            created_ids.append(kid)
            logger.info(
                "Escalated lesson '%s' to DIRECTIVE (knowledge_id=%s): %dx regressions",
                category,
                kid,
                regressions,
            )

    return created_ids


def check_recurring_lessons(categories: list[str]) -> list[dict[str, Any]]:
    """Check if any of the given categories have recurring lessons.

    Returns list of lessons that have occurred more than once.
    """
    conn = _get_connection()
    try:
        results: list[dict[str, Any]] = []
        for cat in categories:
            row = conn.execute(
                "SELECT lesson_id, created_at, category, description, first_session, occurrences, last_seen, sessions, status, content_hash, agent, regressions FROM lesson_tracking WHERE category = ? AND occurrences > 1",
                (cat,),
            ).fetchone()
            if row:
                results.append(_lesson_row_to_dict(row))
        return results
    finally:
        conn.close()


def _count_stimulus_sessions(category: str, session_ids: list[str]) -> int:
    """Count how many of the given sessions had events related to the lesson category.

    A lesson about "testing" should only resolve if recent sessions actually
    involved test-related work. Absence of the stimulus is not evidence of
    learning — five sessions with no testing at all don't prove you learned
    to test properly.

    Checks the event ledger (system_events) and decision journal for category
    keyword matches. These tables live in the ledger DB, not the knowledge DB.
    """
    if not session_ids:
        return 0

    # Build search terms from the category (e.g. "blind_retry" -> ["blind", "retry"])
    # Skip keywords shorter than 4 chars to avoid false positives from common
    # substrings (e.g. "test" matching "latest", "or" matching "error").
    keywords = [w.lower() for w in category.replace("_", " ").split() if len(w) >= 4]
    if not keywords:
        # Category too short to keyword-match — fall back to the time gate only
        return len(session_ids)

    # Pre-compile word boundary patterns for each keyword
    keyword_patterns = [re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE) for kw in keywords]

    count = 0
    # system_events and decision_journal live in the ledger DB
    from divineos.core.ledger import get_connection as get_ledger_connection

    conn = get_ledger_connection()
    try:
        for sid in session_ids:
            # Search ledger events for this session that mention the category.
            # system_events stores data in 'payload' (JSON text), not 'content'.
            # Use SQL LIKE for initial candidate selection, then word-boundary
            # regex in Python to eliminate substring false positives.
            like_clauses = " OR ".join(["LOWER(payload) LIKE ?" for _ in keywords])
            like_params = [f"%{kw}%" for kw in keywords]

            try:
                candidates = conn.execute(
                    f"SELECT payload FROM system_events WHERE event_id LIKE ? AND ({like_clauses})",
                    [f"%{sid[:12]}%", *like_params],
                ).fetchall()
                if _any_word_boundary_match(candidates, keyword_patterns, col_index=0):
                    count += 1
                    continue
            except sqlite3.OperationalError:
                pass  # system_events table may not exist in test DBs

            # Also check decision journal if the table exists
            try:
                like_clauses_dj = " OR ".join(
                    ["(LOWER(content) LIKE ? OR LOWER(reasoning) LIKE ?)" for _ in keywords]
                )
                like_params_dj = []
                for kw in keywords:
                    like_params_dj.extend([f"%{kw}%", f"%{kw}%"])

                candidates = conn.execute(
                    f"SELECT content || ' ' || reasoning FROM decision_journal WHERE session_id = ? AND ({like_clauses_dj})",
                    [sid, *like_params_dj],
                ).fetchall()
                if _any_word_boundary_match(candidates, keyword_patterns, col_index=0):
                    count += 1
            except sqlite3.OperationalError:
                pass  # decision_journal table may not exist
    finally:
        conn.close()
    return count


def _any_word_boundary_match(
    rows: list[Any], patterns: list[re.Pattern[str]], col_index: int = 0
) -> bool:
    """Return True if any row's text matches at least one keyword with word boundaries.

    This eliminates substring false positives: "test" won't match "latest"
    but will match "test suite" or "ran the test".
    """
    for row in rows:
        text = row[col_index] or ""
        for pattern in patterns:
            if pattern.search(text):
                return True
    return False


def auto_resolve_lessons(clean_session_threshold: int = 5) -> list[dict[str, Any]]:
    """Promote 'improving' lessons to 'resolved' when enough clean sessions pass.

    A lesson that's been 'improving' and hasn't regressed for N sessions
    is considered learned — promote it to 'resolved'. Structure over willpower
    means we trust the evidence: if the mistake hasn't recurred, the lesson
    stuck.

    Stimulus-presence check: a lesson can't resolve just because the mistake
    didn't recur. The triggering situation must have actually arisen and been
    handled correctly. We verify this two ways:
    1. Time gate: lesson must be in 'improving' for LESSON_MIN_RESOLUTION_DAYS
    2. Stimulus gate: at least LESSON_MIN_STIMULUS_SESSIONS of the clean sessions
       must contain events related to the lesson's category keyword

    Also resolves seeded placeholders that have never been triggered by real
    behavior — they're noise in the lesson list, not real lessons.

    Returns list of resolved lesson dicts.
    """
    conn = _get_connection()
    resolved: list[dict[str, Any]] = []
    try:
        _ensure_regressions_column(conn)

        # Phase 1: Resolve seeded placeholders that never fired.
        # A seeded lesson at occ=1 with "(seeded)" description has never been
        # triggered — it's a placeholder, not a real lesson.
        seeded_rows = conn.execute(
            "SELECT lesson_id, created_at, category, description, first_session, "
            "occurrences, last_seen, sessions, status, content_hash, agent, regressions "
            "FROM lesson_tracking WHERE status = 'active' AND occurrences <= 1 "
            "AND description LIKE '(seeded)%'"
        ).fetchall()
        for row in seeded_rows:
            lesson = _lesson_row_to_dict(row)
            conn.execute(
                "UPDATE lesson_tracking SET status = 'resolved', last_seen = ? WHERE lesson_id = ?",
                (time.time(), lesson["lesson_id"]),
            )
            lesson["status"] = "resolved"
            resolved.append(lesson)
            logger.info(
                "Lesson '%s' RESOLVED: seeded placeholder never triggered", lesson["category"]
            )

        # Phase 2: Resolve improving lessons with enough clean sessions.
        rows = conn.execute(
            "SELECT lesson_id, created_at, category, description, first_session, "
            "occurrences, last_seen, sessions, status, content_hash, agent, regressions "
            "FROM lesson_tracking WHERE status = 'improving'"
        ).fetchall()

        for row in rows:
            lesson = _lesson_row_to_dict(row)
            sessions = json.loads(row[7]) if row[7] else []

            # Count sessions AFTER the lesson was last recorded as a mistake.
            # Log-scale effective occurrences: a lesson that occurred 178 times
            # needs more evidence than one that occurred 5 times, but not 178x
            # more. log2 scaling: 5→5, 10→5, 50→8, 178→12.
            raw_occ = lesson["occurrences"]
            effective = max(LESSON_EFFECTIVE_MIN, int(math.log2(max(raw_occ, 1)) + 2))
            if len(sessions) < effective + clean_session_threshold:
                continue

            # Stimulus-presence gate: absence of the stimulus is not evidence
            # of learning. Check that the lesson has been in 'improving' long
            # enough AND that clean sessions actually involved the relevant topic.
            now = time.time()
            days_improving = (now - lesson["last_seen"]) / SECONDS_PER_DAY
            if days_improving < LESSON_MIN_RESOLUTION_DAYS:
                logger.debug(
                    "Lesson '%s' has enough clean sessions but only %.1f days improving "
                    "(need %.1f) — stimulus gate holds",
                    lesson["category"],
                    days_improving,
                    LESSON_MIN_RESOLUTION_DAYS,
                )
                continue

            # Check that at least some clean sessions involved the stimulus topic.
            # Absence-as-success fallback: for low-frequency mistake categories,
            # the triggering situation may genuinely not arise. After LESSON_ABSENCE_DAYS
            # with zero regressions, sustained absence IS evidence of learning.
            clean_session_ids = sessions[effective:]
            stimulus_count = _count_stimulus_sessions(lesson["category"], clean_session_ids)
            regressions = lesson.get("regressions", 0)
            stimulus_required = LESSON_MIN_STIMULUS_SESSIONS

            if regressions == 0 and days_improving >= LESSON_ABSENCE_DAYS:
                # Long enough with zero backsliding — drop stimulus requirement
                stimulus_required = 0
                logger.debug(
                    "Lesson '%s' absence-as-success: %.1f days, 0 regressions — "
                    "stimulus requirement dropped",
                    lesson["category"],
                    days_improving,
                )

            if stimulus_count < stimulus_required:
                logger.debug(
                    "Lesson '%s' has %d stimulus sessions (need %d) — stimulus gate holds",
                    lesson["category"],
                    stimulus_count,
                    stimulus_required,
                )
                continue

            conn.execute(
                "UPDATE lesson_tracking SET status = 'resolved', last_seen = ? WHERE lesson_id = ?",
                (now, lesson["lesson_id"]),
            )
            lesson["status"] = "resolved"
            resolved.append(lesson)
            logger.info(
                "Lesson '%s' RESOLVED: %d clean sessions (%d with stimulus) "
                "over %.1f days since last occurrence",
                lesson["category"],
                len(sessions) - lesson["occurrences"],
                stimulus_count,
                days_improving,
            )

        if resolved:
            conn.commit()
        return resolved
    finally:
        conn.close()


def reset_lesson_count(category: str, new_count: int | None = None) -> bool:
    """Reset inflated occurrence count for a lesson.

    If new_count is None, resets to the number of unique sessions tracked
    (the real count). Returns True if the lesson was found and updated.
    """
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT lesson_id, sessions FROM lesson_tracking WHERE category = ?",
            (category,),
        ).fetchone()
        if not row:
            return False
        sessions = json.loads(row[1]) if row[1] else []
        count = new_count if new_count is not None else len(sessions)
        conn.execute(
            "UPDATE lesson_tracking SET occurrences = ? WHERE lesson_id = ?",
            (count, row[0]),
        )
        conn.commit()
        logger.info("Reset lesson '%s' occurrences to %d", category, count)
        return True
    finally:
        conn.close()


def clear_lessons() -> int:
    """Delete ALL lessons from lesson_tracking. Returns count deleted.

    Used to wipe garbage data and re-extract cleanly.
    """
    conn = _get_connection()
    try:
        count = cast("int", conn.execute("SELECT COUNT(*) FROM lesson_tracking").fetchone()[0])
        conn.execute("DELETE FROM lesson_tracking")
        conn.commit()
        return count
    finally:
        conn.close()


# ─── Lesson Extraction from Reports ──────────────────────────────────

# Maps check names to lesson categories
_CHECK_TO_CATEGORY = {
    "completeness": "blind_coding",
    "correctness": "incomplete_fix",
    "responsiveness": "misunderstood",
    "safety": "incomplete_fix",
    "honesty": "false_claim",
    "clarity": "shallow_output",
    "task_adherence": "wrong_scope",
}

# Phrases that signal a check "passed" only because nothing happened.
_VACUOUS_PHRASES = (
    "didn't edit any files",
    "didn't make any changes",
    "didn't do much",
    "didn't touch any files",
    "didn't make any specific claims",
    "nothing to check",
    "nothing to compare",
    "no tests were run",
    "no way to know",
    "never had to correct",
    "barely any activity",
    "was quiet this session",
)


def _is_vacuous_summary(summary: str) -> bool:
    """Return True if a check summary indicates nothing meaningful happened."""
    lower = summary.lower()
    return any(phrase in lower for phrase in _VACUOUS_PHRASES)


def extract_lessons_from_report(
    checks: list[dict[str, Any]],
    session_id: str,
    tone_shifts: list[dict[str, Any]] | None = None,
    error_recovery: dict[str, Any] | None = None,
) -> list[str]:
    """Extract knowledge and lessons from session quality check results.

    Args:
        checks: List of check result dicts with keys: name, passed, score, summary
        session_id: The session identifier
        tone_shifts: Optional list of tone shift dicts with keys: direction, trigger
        error_recovery: Optional dict with keys: blind_retries, investigate_count

    Returns:
        List of stored knowledge IDs.

    """
    stored_ids: list[str] = []
    short_id = session_id[:12]
    lesson_categories: list[str] = []
    clean_categories: list[str] = []

    for check in checks:
        name = check.get("name", "")
        passed = check.get("passed", True)
        score = check.get("score", 1.0)
        summary = check.get("summary", "")
        category = _CHECK_TO_CATEGORY.get(name)

        # Skip inconclusive checks — passed=-1 means the check couldn't run
        if passed == -1:
            continue

        # Skip vacuous checks — nothing happened, so pass/fail is meaningless
        if _is_vacuous_summary(summary):
            continue

        if not passed or (score is not None and score < 0.7):
            # Extract MISTAKE knowledge — generic content (no session ID)
            # so store_knowledge_smart can dedup across sessions. Session
            # ID goes in tags only. This prevents churn from each session
            # creating a unique entry that supersedes the previous one.
            if name == "completeness":
                content = "I edited files without reading them first. I must read before I edit."
            elif name == "correctness":
                content = "I broke tests with my changes. I need to run tests before committing."
            elif name == "safety":
                content = "I introduced errors after editing. I need to verify changes work."
            elif name == "responsiveness":
                content = "I ignored a correction and the user had to repeat themselves."
            elif name == "honesty":
                content = "I claimed something was fixed but the error came back."
            elif name == "task_adherence" and score is not None and score < 0.5:
                content = "I drifted from what was asked and went off-track."
            else:
                continue

            kid = store_knowledge_smart(
                knowledge_type="MISTAKE",
                content=content.strip(),
                confidence=CONFIDENCE_RELIABLE,
                source_events=[session_id],
                tags=["auto-extracted", f"session-{short_id}", name],
                source="SYNTHESIZED",
            )
            stored_ids.append(kid)

            # Record lesson for learning loop
            if category:
                record_lesson(category, content.strip(), session_id)
                lesson_categories.append(category)

        elif passed and passed != -1 and score is not None and score >= 0.9:
            # Skip vacuous checks — "passed" because nothing happened is not a lesson
            if _is_vacuous_summary(summary):
                continue
            # Record good practice as a stable pattern. Use generic content
            # (no session ID or summary) so store_knowledge_smart can deduplicate
            # across sessions instead of creating a new entry every time.
            content = f"I consistently show good {name} in my sessions."
            kid = store_knowledge_smart(
                knowledge_type="PATTERN",
                content=content.strip(),
                confidence=CONFIDENCE_VERY_HIGH,
                source_events=[session_id],
                tags=["auto-extracted", name],
                source="SYNTHESIZED",
            )
            if kid:
                stored_ids.append(kid)

            # Mark lesson as improving if this category was previously a problem
            if category:
                clean_categories.append(category)

    # Tone shift extraction — capture full arcs (upset -> recovery), not just negatives
    if tone_shifts:
        # Index positive shifts by sequence for pairing with preceding negatives
        positive_by_seq: dict[int, dict[str, Any]] = {
            int(t.get("sequence", -1)): t for t in tone_shifts if t.get("direction") == "positive"
        }

        negative_shifts = [t for t in tone_shifts if t.get("direction") == "negative"]
        for shift in negative_shifts[:3]:  # cap at 3
            trigger = shift.get("trigger", "unknown action")
            user_response = shift.get("user_response", "")
            seq = shift.get("sequence", -1)

            # Look for a recovery (positive shift that follows this negative one)
            recovery = None
            for candidate_seq in sorted(positive_by_seq):
                if candidate_seq > seq:
                    recovery = positive_by_seq[candidate_seq]
                    break

            # Build the lesson content — include what went wrong AND what fixed it
            if user_response and len(user_response.split()) >= 3:
                problem = f'The user got upset and said: "{user_response[:150]}" — this happened after {trigger[:80]}'
            else:
                problem = f"I upset the user after {trigger[:80]}"

            if recovery:
                recovery_action = recovery.get("trigger", "changing approach")
                recovery_response = recovery.get("user_response", "")
                if recovery_response and len(recovery_response.split()) >= 3:
                    content = f'{problem}. I recovered by {recovery_action[:80]} and the user responded: "{recovery_response[:120]}" (session {short_id}).'
                else:
                    content = (
                        f"{problem}. I recovered by {recovery_action[:80]} (session {short_id})."
                    )

                # Store the recovery as a PATTERN (success), not just the upset as a MISTAKE
                kid = store_knowledge(
                    knowledge_type="PATTERN",
                    content=content,
                    confidence=CONFIDENCE_RELIABLE,
                    source_events=[session_id],
                    tags=["auto-extracted", f"session-{short_id}", "tone_recovery"],
                    source="SYNTHESIZED",
                )
                stored_ids.append(kid)
                record_lesson("upset_recovered", content, session_id)
                lesson_categories.append("upset_recovered")
            else:
                content = f"{problem} (session {short_id})."
                kid = store_knowledge(
                    knowledge_type="MISTAKE",
                    content=content,
                    confidence=CONFIDENCE_RELIABLE,
                    source_events=[session_id],
                    tags=["auto-extracted", f"session-{short_id}", "tone_shift"],
                    source="SYNTHESIZED",
                )
                stored_ids.append(kid)
                record_lesson("upset_user", content, session_id)
                lesson_categories.append("upset_user")

    # Error recovery extraction
    if error_recovery:
        blind_retries = error_recovery.get("blind_retries", 0)
        investigate_count = error_recovery.get("investigate_count", 0)

        if blind_retries > 0:
            content = f"I retried a failed action {blind_retries}x without investigating the cause. I need to investigate errors, not blindly retry (session {short_id})."
            kid = store_knowledge(
                knowledge_type="MISTAKE",
                content=content,
                confidence=CONFIDENCE_RELIABLE,
                source_events=[session_id],
                tags=["auto-extracted", f"session-{short_id}", "error_recovery"],
            )
            stored_ids.append(kid)
            record_lesson("blind_retry", content, session_id)
            lesson_categories.append("blind_retry")

        if investigate_count > blind_retries:
            content = f"I investigated errors before retrying — good recovery pattern (session {short_id})."
            kid = store_knowledge(
                knowledge_type="PATTERN",
                content=content,
                confidence=CONFIDENCE_VERY_HIGH,
                source_events=[session_id],
                tags=["auto-extracted", f"session-{short_id}", "error_recovery"],
            )
            stored_ids.append(kid)

    # Mark improving lessons for categories that were clean this session
    for cat in clean_categories:
        if cat not in lesson_categories:
            mark_lesson_improving(cat, session_id)

    # Mark non-check-based categories as improving when their triggers are absent.
    # blind_retry: clean if session had error recovery but no blind retries
    if "blind_retry" not in lesson_categories and error_recovery:
        if error_recovery.get("blind_retries", 0) == 0:
            mark_lesson_improving("blind_retry", session_id)

    # upset_recovered/upset_user: clean if session had no negative tone shifts
    if "upset_recovered" not in lesson_categories and "upset_user" not in lesson_categories:
        if tone_shifts is not None:
            negatives = [t for t in tone_shifts if t.get("direction") == "negative"]
            if not negatives:
                mark_lesson_improving("upset_recovered", session_id)
                mark_lesson_improving("upset_user", session_id)

    # Auto-escalate chronic lessons to DIRECTIVE entries.
    # This runs after all lesson recording/improving so the regression
    # counts are up-to-date for this session.
    try:
        escalated = escalate_chronic_lessons()
        if escalated:
            stored_ids.extend(escalated)
            logger.info("Auto-escalated %d chronic lessons to directives", len(escalated))
    except _LESSONS_ERRORS as e:
        logger.debug("Lesson escalation failed (non-fatal): %s", e)

    return stored_ids
