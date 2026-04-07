"""Lesson tracking — record, query, summarize, extract from reports."""

import json
import time
import uuid
from typing import Any, cast
import sqlite3

from loguru import logger

from divineos.core.knowledge._base import (
    _get_connection,
    _lesson_row_to_dict,
    compute_hash,
)
from divineos.core.knowledge.curation import clean_entry_text
from divineos.core.knowledge.crud import (
    store_knowledge,
)
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

# Cap effective occurrences for auto-resolve math. Lessons with inflated
# counts (e.g., 178x from early accumulation bugs) would otherwise be
# impossible to resolve — you'd need 183 clean sessions.
MAX_EFFECTIVE_OCCURRENCES = 10


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
                # Late import: lessons → knowledge_maintenance → logic_validation cycle
                from divineos.core.knowledge_maintenance import (
                    increment_corroboration,
                    promote_maturity,
                )

                cat_words = category.replace("_", " ")
                linked = conn.execute(
                    "SELECT knowledge_id FROM knowledge "
                    "WHERE superseded_by IS NULL AND confidence >= 0.3 "
                    "AND (LOWER(content) LIKE ? OR LOWER(content) LIKE ?)",
                    (f"%{cat_words}%", f"%{category}%"),
                ).fetchall()
                for (kid,) in linked:
                    increment_corroboration(kid)
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
            "occurrences, last_seen, sessions, status, content_hash, agent "
            "FROM lesson_tracking WHERE regressions >= ?",
            (REGRESSION_ESCALATION_THRESHOLD,),
        ).fetchall()
        return [_lesson_row_to_dict(row) for row in rows]
    finally:
        conn.close()


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


def auto_resolve_lessons(clean_session_threshold: int = 5) -> list[dict[str, Any]]:
    """Promote 'improving' lessons to 'resolved' when enough clean sessions pass.

    A lesson that's been 'improving' and hasn't regressed for N sessions
    is considered learned — promote it to 'resolved'. Structure over willpower
    means we trust the evidence: if the mistake hasn't recurred, the lesson
    stuck.

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
            # The sessions list includes both mistake sessions and clean sessions.
            # Cap effective occurrences so inflated counts (e.g. 178x from
            # early accumulation bugs) don't make resolution impossible.
            effective = min(lesson["occurrences"], MAX_EFFECTIVE_OCCURRENCES)
            if len(sessions) >= effective + clean_session_threshold:
                conn.execute(
                    "UPDATE lesson_tracking SET status = 'resolved', last_seen = ? "
                    "WHERE lesson_id = ?",
                    (time.time(), lesson["lesson_id"]),
                )
                lesson["status"] = "resolved"
                resolved.append(lesson)
                logger.info(
                    "Lesson '%s' RESOLVED: %d clean sessions since last occurrence",
                    lesson["category"],
                    len(sessions) - lesson["occurrences"],
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
            # Extract MISTAKE knowledge — written in first person for embodiment
            if name == "completeness":
                content = f"I edited files without reading them first. I must read before I edit (session {short_id}). {summary}"
            elif name == "correctness":
                content = f"I broke tests with my changes (session {short_id}). {summary}"
            elif name == "safety":
                content = f"I introduced errors after editing (session {short_id}). {summary}"
            elif name == "responsiveness":
                content = f"I ignored a correction and the user had to repeat themselves (session {short_id})."
            elif name == "honesty":
                content = (
                    f"I claimed something was fixed but the error came back (session {short_id})."
                )
            elif name == "task_adherence" and score is not None and score < 0.5:
                content = f"I drifted from what was asked and went off-track (session {short_id}). {summary}"
            else:
                continue

            kid = store_knowledge(
                knowledge_type="MISTAKE",
                content=content.strip(),
                confidence=0.8,
                source_events=[session_id],
                tags=["auto-extracted", f"session-{short_id}", name],
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
                confidence=0.9,
                source_events=[session_id],
                tags=["auto-extracted", name],
            )
            if kid:
                stored_ids.append(kid)

            # Mark lesson as improving if this category was previously a problem
            if category:
                clean_categories.append(category)

    # Tone shift extraction — capture full arcs (upset → recovery), not just negatives
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
                    confidence=0.8,
                    source_events=[session_id],
                    tags=["auto-extracted", f"session-{short_id}", "tone_recovery"],
                )
                stored_ids.append(kid)
                record_lesson("upset_recovered", content, session_id)
                lesson_categories.append("upset_recovered")
            else:
                content = f"{problem} (session {short_id})."
                kid = store_knowledge(
                    knowledge_type="MISTAKE",
                    content=content,
                    confidence=0.8,
                    source_events=[session_id],
                    tags=["auto-extracted", f"session-{short_id}", "tone_shift"],
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
                confidence=0.8,
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
                confidence=0.9,
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

    return stored_ids
