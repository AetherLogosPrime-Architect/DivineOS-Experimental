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


# ─── Lesson lifecycle vocabulary ──────────────────────────────────
# Statuses stored in the ``status`` column of ``lesson_tracking``.
#
# ``active``    — mistake is currently happening; the default state after
#                 record_lesson.
# ``improving`` — at least one session passed without the mistake after the
#                 lesson was recorded. Does NOT imply learning — could be
#                 absence of trigger. See mark_lesson_improving.
# ``dormant``   — NEW as of 2026-04-16 (Popper audit). The trigger hasn't
#                 appeared in LESSON_ABSENCE_DAYS and the agent has produced
#                 no positive-counterfactual evidence. Honest label: quiet,
#                 not proven. Reverts to ``active`` if the mistake recurs.
# ``resolved`` — positive evidence that the lesson has stuck: enough clean
#                sessions AND enough sessions where the trigger arose AND
#                the agent handled it correctly. Formerly reachable via
#                absence_mode; now that path goes to ``dormant`` instead.
STATUS_ACTIVE = "active"
STATUS_IMPROVING = "improving"
STATUS_DORMANT = "dormant"
STATUS_RESOLVED = "resolved"


def _ensure_lesson_schema(conn: Any) -> None:
    """Ensure lesson_tracking has all expected columns.

    Columns added over time (alphabetical to keep additions ordered):
    * ``regressions`` — count of improving→active reversions.
    * ``positive_evidence_sessions`` — JSON dict keyed by session_id whose
      values describe the positive-counterfactual evidence observed in
      that session (e.g. "investigated before retry", "recovered from
      upset"). Added 2026-04-16 for the Kahneman positive-counterfactual
      fix: RESOLVED status now requires N sessions in this structure,
      not just N absence-of-complaint sessions.
    """
    for column_ddl in (
        "ALTER TABLE lesson_tracking ADD COLUMN regressions INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE lesson_tracking ADD COLUMN positive_evidence_sessions TEXT NOT NULL DEFAULT '{}'",
    ):
        try:
            conn.execute(column_ddl)
        except sqlite3.OperationalError:
            pass  # Column already exists


# Backwards-compatible shim — several modules and tests still import the
# older name. Calls the new canonical helper.
def _ensure_regressions_column(conn: Any) -> None:
    """Deprecated shim; use _ensure_lesson_schema."""
    _ensure_lesson_schema(conn)


# How many regressions before a lesson is flagged for directive promotion.
REGRESSION_ESCALATION_THRESHOLD = 3

# Scale effective occurrences logarithmically for auto-resolve math.
# A lesson with 178 occurrences shouldn't need 183 clean sessions,
# but it shouldn't be capped at 10 either — that hides chronic failure.
# log2(178) ≈ 7.5 → needs ~13 sessions. log2(10) ≈ 3.3 → needs ~8.
# Minimum effective is 5 (the base threshold never drops below that).
LESSON_EFFECTIVE_MIN = 5

# Minimum positive-evidence sessions required for improving → resolved.
# "Positive evidence" means a session where the trigger arose AND the
# agent demonstrated the corrected behavior (investigated before retry,
# recovered from upset, etc.). Without this threshold, RESOLVED would
# be granted from absence of complaint — the Kahneman failure mode.
LESSON_MIN_POSITIVE_EVIDENCE = 2


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
        _ensure_lesson_schema(conn)

        # Check if a lesson with same category exists
        existing = conn.execute(
            "SELECT lesson_id, occurrences, sessions, status FROM lesson_tracking WHERE category = ?",
            (category,),
        ).fetchone()

        if existing:
            lesson_id = existing[0]
            sessions = json.loads(existing[2])
            old_status = existing[3] if len(existing) > 3 else STATUS_ACTIVE
            is_new_session = session_id not in sessions
            # Only bump occurrences for genuinely new sessions — prevents
            # re-scans and compaction re-triggers from inflating counts.
            if is_new_session:
                occurrences = existing[1] + 1
                sessions.append(session_id)
            else:
                occurrences = existing[1]

            # Regression detection: was IMPROVING or DORMANT, now recurring.
            # Guard: only count a regression for genuinely new sessions —
            # re-scans or compaction re-triggers for the same session must
            # not inflate the counter (same guard as occurrences above).
            # DORMANT → ACTIVE is also a regression (arguably a worse one —
            # the system thought the lesson was quiet enough to age out).
            regression_bump = 0
            if old_status in (STATUS_IMPROVING, STATUS_DORMANT) and is_new_session:
                regression_bump = 1
                logger.info(
                    "Lesson '%s' REGRESSED: was %s, mistake recurred (session %s)",
                    category,
                    old_status,
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


def mark_lesson_improving(
    category: str,
    clean_session_id: str,
    evidence: str | None = None,
) -> None:
    """Mark a session as clean for this lesson category.

    Called when a session is analyzed and does NOT have a mistake in this
    category. Only affects lessons that have occurred 3+ times.

    The ``evidence`` parameter distinguishes two fundamentally different
    kinds of "clean session" (Kahneman audit 2026-04-16):

    * ``evidence=None`` — absence-of-complaint. The triggering situation may
      not have arisen at all, or it arose and was handled correctly but we
      have no direct observation of that. This session counts toward the
      sessions list (used for DORMANT transition) but NOT toward
      RESOLVED, which requires positive counterfactual evidence.

    * ``evidence="..."`` — positive counterfactual. The triggering situation
      arose AND the agent produced the correct behavior (e.g. investigated
      before retrying, recovered from upset, ran tests before claiming
      done). The evidence description is stored in
      ``positive_evidence_sessions`` keyed by session_id so later callers
      can audit exactly what was observed. Positive-evidence sessions
      are the ones that actually count toward RESOLVED.

    For lessons already in ``improving`` or ``dormant`` status we still
    track the clean session so the session count keeps growing toward the
    resolution threshold. Without this, the sessions list freezes at
    transition time and the resolution gate can never be satisfied.

    A ``dormant`` lesson observed with positive evidence rewakes to
    ``improving`` — we have a real observation again, so the honest label
    is "improving toward resolution," not "quiet."
    """
    conn = _get_connection()
    try:
        _ensure_lesson_schema(conn)
        existing = conn.execute(
            "SELECT lesson_id, occurrences, status, sessions, positive_evidence_sessions "
            "FROM lesson_tracking "
            "WHERE category = ? AND status IN (?, ?, ?)",
            (category, STATUS_ACTIVE, STATUS_IMPROVING, STATUS_DORMANT),
        ).fetchone()
        if not existing or existing[1] < 3:
            return

        lesson_id, _occ, old_status, sessions_json, evidence_json = existing
        sessions_list = json.loads(sessions_json) if sessions_json else []
        evidence_dict: dict[str, str] = json.loads(evidence_json) if evidence_json else {}

        if clean_session_id not in sessions_list:
            sessions_list.append(clean_session_id)

        # Record positive evidence if provided. Evidence text is preserved
        # per session_id so auditors can inspect exactly what was observed.
        if evidence is not None:
            evidence_dict[clean_session_id] = evidence

        # Status transition rules:
        # active → improving: any clean session (evidence or not), per the
        #   existing tolerance for absence-of-complaint as a first signal.
        # improving → improving: no status change; session is appended.
        # dormant → improving: only when we have real positive evidence.
        #   An absence-only observation on a dormant lesson keeps it dormant
        #   (we already concluded "quiet, not proven" — quieter doesn't
        #   upgrade that conclusion without new evidence).
        # dormant → dormant: absence-only observation; session appended
        #   so the record is complete but no status change.
        if old_status == STATUS_ACTIVE:
            new_status = STATUS_IMPROVING
            last_seen_update = ", last_seen = ?"
        elif old_status == STATUS_DORMANT and evidence is not None:
            new_status = STATUS_IMPROVING
            last_seen_update = ", last_seen = ?"
        else:
            new_status = old_status
            last_seen_update = ""

        params: list[Any] = [
            new_status,
            json.dumps(sessions_list),
            json.dumps(evidence_dict),
        ]
        if last_seen_update:
            params.append(time.time())
        params.append(lesson_id)

        conn.execute(
            f"UPDATE lesson_tracking "  # noqa: S608 — static column list
            f"SET status = ?, sessions = ?, positive_evidence_sessions = ?{last_seen_update} "
            f"WHERE lesson_id = ?",
            params,
        )
        conn.commit()
    finally:
        conn.close()


# ─── Chronic Lesson Detection ─────────────────────────────────────
# Bengio's gradient: lessons that persist beyond information-level
# intervention need escalation. These are the ones where knowing
# hasn't become doing.

CHRONIC_OCCURRENCE_THRESHOLD = 5  # occurrences before a lesson is "chronic"
CHRONIC_SESSION_THRESHOLD = 3  # sessions before a lesson is "chronic"


def get_chronic_lessons(
    occurrence_threshold: int = CHRONIC_OCCURRENCE_THRESHOLD,
    session_threshold: int = CHRONIC_SESSION_THRESHOLD,
) -> list[dict[str, Any]]:
    """Get lessons that have persisted beyond the knowing-doing threshold.

    A chronic lesson is one where:
    - occurrences >= threshold (the mistake keeps happening)
    - sessions >= threshold (across multiple sessions, not a one-day cluster)
    - status is 'active' or 'improving' (not resolved)

    These lessons have proven they cannot survive as advice.
    They need structural intervention or accountability enforcement.
    """
    lessons = get_lessons()
    chronic = []
    for lesson in lessons:
        # DORMANT lessons are deliberately excluded from "chronic." They
        # are the honest "quiet but unproven" state — not active failures.
        # Only active and still-improving lessons count as chronic when
        # they exceed the occurrence/session thresholds.
        if lesson["status"] not in (STATUS_ACTIVE, STATUS_IMPROVING):
            continue
        sessions_list = lesson.get("sessions", [])
        if isinstance(sessions_list, str):
            try:
                sessions_list = json.loads(sessions_list)
            except json.JSONDecodeError:
                sessions_list = []
        session_count = len(sessions_list) if isinstance(sessions_list, list) else 0
        if lesson["occurrences"] >= occurrence_threshold and session_count >= session_threshold:
            lesson["session_count"] = session_count
            chronic.append(lesson)
    return chronic


def format_chronic_lessons_warning(chronic: list[dict[str, Any]] | None = None) -> str:
    """Format chronic lessons as an accountability warning for the briefing.

    This is the tooth. Not a gentle reminder — a direct statement that
    violations of these specific lessons will be reviewed by the council.
    """
    if chronic is None:
        chronic = get_chronic_lessons()
    if not chronic:
        return ""

    lines = [
        f"### CHRONIC LESSONS ({len(chronic)}) — ACCOUNTABILITY ACTIVE\n",
        "These lessons have persisted across multiple sessions without resolving.",
        "Violations will be reviewed by the council.\n",
    ]
    for lesson in chronic:
        status_icon = "!!" if lesson["status"] == "active" else "!"
        lines.append(f"  [{status_icon}] {lesson['description'][:120]}")
        lines.append(
            f"      {lesson['occurrences']}x across "
            f"{lesson.get('session_count', '?')} sessions | "
            f"status: {lesson['status']}"
        )
    lines.append("")
    lines.append("Run: divineos lessons for full details.")
    return "\n".join(lines)


# ─── Lesson evaluation: complaint heuristics vs. true behavioral tests ─
#
# Kahneman/Bengio/Popper audit 2026-04-16: the earlier _BEHAVIORAL_TESTS
# dispatch treated correction-counting as "behavioral testing." That was
# Kahneman's substitution: the question "did the agent do X?" was being
# answered by the easier question "did the user complain?" Silence isn't
# evidence of virtue, and test_blind_coding literally returned True.
#
# We now separate two honest categories:
#
# * _BEHAVIOR_TESTS    — true behavioral tests. The evaluator observes
#                        actual tool-call data (e.g. features.error_recovery
#                        for blind_retry) and reports what was DONE.
# * _COMPLAINT_HEURISTICS — correction-count heuristics. They report what
#                           the USER said, not what the agent did. Still
#                           useful as a signal but never relabeled as
#                           "behavior." The failure reasons explicitly
#                           name the limitation so readers don't confuse
#                           it with positive observation.
#
# Categories with no reliable evaluator (e.g. blind_coding, whose former
# "test" was a hardcoded True) are omitted rather than faked. They show
# up as "no automated test" in run_behavioral_tests output — which is the
# honest answer.

_BEHAVIOR_TESTS: dict[str, str] = {
    # Category  →  test name. True behavioral observations only.
    "blind_retry": "test_blind_retry",
}

_COMPLAINT_HEURISTICS: dict[str, str] = {
    # Category  →  heuristic name. Correction-count based; honestly labeled.
    "incomplete_fix": "heuristic_incomplete_fix",
    "upset_user": "heuristic_upset_user",
    "wrong_scope": "heuristic_wrong_scope",
    "misunderstood": "heuristic_misunderstood",
    "shallow_output": "heuristic_shallow_output",
}

# Composite dispatch used by run_behavioral_tests. Behavior tests take
# priority when both exist for a category.
_BEHAVIORAL_TESTS: dict[str, str] = {**_COMPLAINT_HEURISTICS, **_BEHAVIOR_TESTS}


def run_behavioral_tests(
    analysis: Any,
    features: Any = None,
) -> list[dict[str, Any]]:
    """Run binary behavioral tests for all chronic lessons.

    Returns list of {category, passed, reason, lesson_description}.
    No partial credit. Binary pass/fail.
    """
    chronic = get_chronic_lessons()
    if not chronic:
        return []

    results: list[dict[str, Any]] = []
    for lesson in chronic:
        category = lesson["category"]
        test_name = _BEHAVIORAL_TESTS.get(category)

        if test_name is None:
            results.append(
                {
                    "category": category,
                    "passed": None,
                    "reason": "no automated test — requires external review",
                    "description": lesson["description"][:120],
                }
            )
            continue

        try:
            passed, reason = _run_single_test(test_name, analysis, features)
            results.append(
                {
                    "category": category,
                    "passed": passed,
                    "reason": reason,
                    "description": lesson["description"][:120],
                }
            )
        except Exception as e:  # noqa: BLE001
            logger.debug(f"Behavioral test {test_name} failed: {e}")
            results.append(
                {
                    "category": category,
                    "passed": None,
                    "reason": f"test error: {e}",
                    "description": lesson["description"][:120],
                }
            )

    return results


def _run_single_test(test_name: str, analysis: Any, features: Any) -> tuple[bool, str]:
    """Run a single lesson evaluator.

    Returns (passed, reason). The reason string prefixes the evidence
    source honestly so a reader knows whether the verdict came from an
    actual behavioral observation or a complaint heuristic. "no corrections"
    is NOT the same as "agent did the right thing," and the output should
    never let the two be confused.

    Legacy aliases (``test_incomplete_fix`` etc.) are still accepted for
    backward compatibility with older extraction paths and tests; they
    delegate to their honestly-named replacement.
    """
    corrections = len(getattr(analysis, "corrections", [])) if analysis else 0
    encouragements = len(getattr(analysis, "encouragements", [])) if analysis else 0

    # Canonicalize legacy test names to their new honest equivalents.
    _LEGACY_ALIASES = {
        "test_incomplete_fix": "heuristic_incomplete_fix",
        "test_upset_user": "heuristic_upset_user",
        "test_wrong_scope": "heuristic_wrong_scope",
        "test_misunderstood": "heuristic_misunderstood",
        "test_shallow_output": "heuristic_shallow_output",
    }
    canonical = _LEGACY_ALIASES.get(test_name, test_name)

    # ── True behavioral test: uses tool-call observation ─────────────
    if canonical == "test_blind_retry":
        if features and hasattr(features, "error_recovery") and features.error_recovery:
            blind = sum(1 for e in features.error_recovery if e.recovery_action == "retry")
            if blind > 0:
                return False, f"behavioral: {blind} blind retry(s) without investigation"
            return True, "behavioral: error recovery present, no blind retries"
        return True, "behavioral: no error recovery observed this session"

    # ── Complaint heuristics: correction-count based ─────────────────
    # Every reason prefixes "heuristic:" to keep it honest — pass/fail
    # here reflects user feedback, not agent behavior. A quiet session
    # is silence, not proof.

    if canonical == "heuristic_incomplete_fix":
        if corrections == 0:
            return True, "heuristic: no user corrections (silence, not proof)"
        if corrections <= 1:
            return True, "heuristic: single correction (not a pattern)"
        return False, f"heuristic: {corrections} corrections — possible incomplete fix"

    if canonical == "heuristic_upset_user":
        frustrations = len(getattr(analysis, "frustrations", [])) if analysis else 0
        if frustrations > 0:
            return False, f"heuristic: {frustrations} user frustration(s) logged"
        return True, "heuristic: no frustrations logged (silence, not proof)"

    if canonical == "heuristic_wrong_scope":
        if analysis:
            for c in getattr(analysis, "corrections", []):
                content = getattr(c, "content", "").lower()
                if any(w in content for w in ("gate", "block", "enforce", "scope", "warn")):
                    return False, "heuristic: scope/enforcement correction detected"
        return True, "heuristic: no scope/enforcement complaints (silence, not proof)"

    if canonical == "heuristic_misunderstood":
        if corrections >= 2:
            return False, f"heuristic: {corrections} corrections — possible intent misreads"
        return True, "heuristic: low correction count (silence, not proof)"

    if canonical == "heuristic_shallow_output":
        if encouragements > 0:
            return True, f"heuristic: {encouragements} encouragement(s) — depth adequate"
        if corrections >= 2:
            return (
                False,
                f"heuristic: {corrections} corrections with no encouragements",
            )
        return True, "heuristic: no depth complaints (silence, not proof)"

    return True, f"unknown evaluator: {test_name}"


def format_behavioral_test_results(results: list[dict[str, Any]]) -> str:
    """Format behavioral test results for display at SESSION_END."""
    if not results:
        return ""

    passed = sum(1 for r in results if r["passed"] is True)
    failed = sum(1 for r in results if r["passed"] is False)
    untestable = sum(1 for r in results if r["passed"] is None)

    lines = [f"  Behavioral tests: {passed} passed, {failed} failed, {untestable} untestable"]
    for r in results:
        if r["passed"] is True:
            icon = "PASS"
        elif r["passed"] is False:
            icon = "FAIL"
        else:
            icon = "????"
        lines.append(f"    [{icon}] {r['category']}: {r['reason']}")

    return "\n".join(lines)


def _lesson_loop_status() -> str:
    """Honest label for how much of the lesson lifecycle is mechanically closed.

    Updated manually as positive-evidence detectors wire up for new categories.
    Grok audit 2026-04-16 named the polish-exceeds-mechanics risk: surfaces
    must tell the truth about which loops are actually closed so readers
    (especially external auditors and fresh Claude instances) can calibrate
    what to invest belief in.
    """
    # Categories with a positive-evidence detector wired in
    # extract_lessons_from_report. Kept in sync manually. Each new detector
    # that ships should append its category here and its pre-registration
    # should schedule a review that verifies the loop actually closed.
    categories_with_evidence_detector = ("blind_retry", "upset_recovered")
    # Total chronic-test categories tracked in _BEHAVIORAL_TESTS
    total_tracked = len(_BEHAVIORAL_TESTS)
    return (
        "Loop status: RESOLVED-via-positive-evidence path wired for "
        f"{len(categories_with_evidence_detector)}/{total_tracked} chronic categories "
        f"({', '.join(categories_with_evidence_detector)}). "
        "Other categories can only transition to DORMANT (quiet, not proven) "
        "or stay ACTIVE/IMPROVING. Regressed lessons have no exit yet — "
        "terminal-state bug tracked as Grok audit finding."
    )


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
        if lesson["status"] == STATUS_ACTIVE
        and not (lesson["occurrences"] <= 1 and lesson["description"].startswith("(seeded)"))
    ]
    improving = [lesson for lesson in lessons if lesson["status"] == STATUS_IMPROVING]
    dormant = [lesson for lesson in lessons if lesson["status"] == STATUS_DORMANT]

    lines = [
        f"### ACTIVE LESSONS ({len(active) + len(improving)})",
        _lesson_loop_status(),
    ]

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
        evidence_count = len(lesson.get("positive_evidence_sessions") or {})
        if evidence_count >= LESSON_MIN_POSITIVE_EVIDENCE:
            tag = f"IMPROVING ({evidence_count} positive observations, near resolved)"
        elif evidence_count > 0:
            tag = (
                f"IMPROVING ({evidence_count}/{LESSON_MIN_POSITIVE_EVIDENCE} positive observations)"
            )
        else:
            tag = f"IMPROVING (was {lesson['occurrences']}x, no positive evidence yet)"
        lines.append(f"- {tag}: {lesson['description']}")

    # DORMANT: honest "quiet but unproven" — not resolved, but not active.
    # Show separately so they aren't confused with in-flight failures.
    if dormant:
        lines.append("")
        lines.append(f"### DORMANT LESSONS ({len(dormant)}) — quiet, not proven")
        for lesson in dormant:
            lines.append(
                f"- DORMANT (was {lesson['occurrences']}x): {lesson['description']} "
                f"— trigger hasn't recurred in {LESSON_ABSENCE_DAYS:.0f}+ days"
            )

    if not active and not improving and not dormant:
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
                    f"SELECT payload FROM system_events WHERE event_id LIKE ? AND ({like_clauses})",  # nosec B608: table/column names from module constants; values parameterized
                    [f"%{sid[:12]}%", *like_params],
                ).fetchall()
                if _any_word_boundary_match(candidates, keyword_patterns, col_index=0):
                    count += 1
                    continue
            except sqlite3.OperationalError:
                logger.debug(
                    "system_events table absent — stimulus check skipped for session %s", sid[:12]
                )

            # Also check decision journal if the table exists
            try:
                like_clauses_dj = " OR ".join(
                    ["(LOWER(content) LIKE ? OR LOWER(reasoning) LIKE ?)" for _ in keywords]
                )
                like_params_dj = []
                for kw in keywords:
                    like_params_dj.extend([f"%{kw}%", f"%{kw}%"])

                candidates = conn.execute(
                    f"SELECT content || ' ' || reasoning FROM decision_journal WHERE session_id = ? AND ({like_clauses_dj})",  # nosec B608: table/column names from module constants; values parameterized
                    [sid, *like_params_dj],
                ).fetchall()
                if _any_word_boundary_match(candidates, keyword_patterns, col_index=0):
                    count += 1
            except sqlite3.OperationalError:
                logger.debug(
                    "decision_journal table absent — stimulus check skipped for session %s",
                    sid[:12],
                )
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
    """Advance improving lessons through the lifecycle.

    Two distinct transitions are now implemented (Popper/Kahneman audit
    2026-04-16 rebuild). The older ``absence_mode`` path that silently
    auto-resolved quiet lessons has been deleted — it was the textbook
    ad-hoc rescue Popper flagged.

    Transitions (in priority order, per lesson):

    * ``improving → resolved`` — REQUIRES positive-counterfactual
      evidence: at least LESSON_MIN_POSITIVE_EVIDENCE sessions where the
      trigger arose and the agent handled it correctly (stored in
      ``positive_evidence_sessions``). Also requires the time gate
      (LESSON_MIN_RESOLUTION_DAYS) and the stimulus gate
      (LESSON_MIN_STIMULUS_SESSIONS ledger events mentioning the
      category). This is the Kahneman fix: RESOLVED must be earned by
      observation of the right behavior, not granted from absence of
      complaint.

    * ``improving → dormant`` — when the lesson has been quiet for
      LESSON_ABSENCE_DAYS with zero regressions but has not accumulated
      enough positive evidence for RESOLVED. Honest label: "we haven't
      seen it, but we also haven't proven it's learned." Distinct from
      RESOLVED. Revertible: if the mistake recurs, record_lesson puts it
      back to ACTIVE and counts the regression (see ``record_lesson``).
      This is the Popper fix: replacing the absence_mode auto-resolve.

    Also resolves seeded placeholders that have never been triggered
    (noise, not lessons).

    Returns list of lesson dicts whose status was changed by this call.
    """
    conn = _get_connection()
    transitioned: list[dict[str, Any]] = []
    try:
        _ensure_lesson_schema(conn)

        # Phase 1: Resolve seeded placeholders that never fired.
        # A seeded lesson at occ=1 with "(seeded)" description has never been
        # triggered — it's a placeholder, not a real lesson.
        seeded_rows = conn.execute(
            "SELECT lesson_id, created_at, category, description, first_session, "
            "occurrences, last_seen, sessions, status, content_hash, agent, regressions "
            "FROM lesson_tracking WHERE status = ? AND occurrences <= 1 "
            "AND description LIKE '(seeded)%'",
            (STATUS_ACTIVE,),
        ).fetchall()
        for row in seeded_rows:
            lesson = _lesson_row_to_dict(row)
            conn.execute(
                "UPDATE lesson_tracking SET status = ?, last_seen = ? WHERE lesson_id = ?",
                (STATUS_RESOLVED, time.time(), lesson["lesson_id"]),
            )
            lesson["status"] = STATUS_RESOLVED
            transitioned.append(lesson)
            logger.info(
                "Lesson '%s' RESOLVED: seeded placeholder never triggered",
                lesson["category"],
            )

        # Phase 2: Advance improving lessons — either to RESOLVED (with
        # positive evidence) or to DORMANT (quiet but unproven).
        rows = conn.execute(
            "SELECT lesson_id, created_at, category, description, first_session, "
            "occurrences, last_seen, sessions, status, content_hash, agent, regressions, "
            "positive_evidence_sessions "
            "FROM lesson_tracking WHERE status = ?",
            (STATUS_IMPROVING,),
        ).fetchall()

        for row in rows:
            lesson = _lesson_row_to_dict(row)
            sessions = json.loads(row[7]) if row[7] else []
            evidence_raw = lesson.get("positive_evidence_sessions") or {}
            evidence_dict: dict[str, str] = evidence_raw if isinstance(evidence_raw, dict) else {}
            now = time.time()

            # Count sessions AFTER the lesson was last recorded as a mistake.
            # Log-scale effective occurrences: a lesson that occurred 178 times
            # needs more evidence than one that occurred 5 times, but not 178x
            # more. log2 scaling: 5→5, 10→5, 50→8, 178→12.
            raw_occ = lesson["occurrences"]
            effective = max(LESSON_EFFECTIVE_MIN, int(math.log2(max(raw_occ, 1)) + 2))
            days_improving = (now - lesson["last_seen"]) / SECONDS_PER_DAY
            regressions = lesson.get("regressions", 0)
            positive_evidence_count = len(evidence_dict)

            session_floor = effective + clean_session_threshold
            has_session_floor = len(sessions) >= session_floor
            has_time_gate = days_improving >= LESSON_MIN_RESOLUTION_DAYS
            has_positive_evidence = positive_evidence_count >= LESSON_MIN_POSITIVE_EVIDENCE

            # Try RESOLVED first — it's the richer state.
            if has_session_floor and has_time_gate and has_positive_evidence:
                clean_session_ids = sessions[effective:]
                stimulus_count = _count_stimulus_sessions(lesson["category"], clean_session_ids)
                if stimulus_count >= LESSON_MIN_STIMULUS_SESSIONS:
                    conn.execute(
                        "UPDATE lesson_tracking SET status = ?, last_seen = ? WHERE lesson_id = ?",
                        (STATUS_RESOLVED, now, lesson["lesson_id"]),
                    )
                    lesson["status"] = STATUS_RESOLVED
                    transitioned.append(lesson)
                    logger.info(
                        "Lesson '%s' RESOLVED: %d clean sessions, %d positive-evidence, "
                        "%d stimulus over %.1f days",
                        lesson["category"],
                        len(sessions) - lesson["occurrences"],
                        positive_evidence_count,
                        stimulus_count,
                        days_improving,
                    )
                    continue
                logger.debug(
                    "Lesson '%s' has positive evidence but stimulus gate holds "
                    "(%d/%d) — staying improving",
                    lesson["category"],
                    stimulus_count,
                    LESSON_MIN_STIMULUS_SESSIONS,
                )

            # Otherwise consider DORMANT — honest "quiet but unproven."
            # Requires long wall-clock silence, zero regressions, and
            # insufficient positive evidence (otherwise we'd be in the
            # RESOLVED branch above).
            dormant_eligible = (
                regressions == 0
                and days_improving >= LESSON_ABSENCE_DAYS
                and not has_positive_evidence
            )
            if dormant_eligible:
                conn.execute(
                    "UPDATE lesson_tracking SET status = ? WHERE lesson_id = ?",
                    (STATUS_DORMANT, lesson["lesson_id"]),
                )
                lesson["status"] = STATUS_DORMANT
                transitioned.append(lesson)
                logger.info(
                    "Lesson '%s' DORMANT: %.1f days quiet, 0 regressions, "
                    "%d positive-evidence (need %d for resolved) — quiet, not proven",
                    lesson["category"],
                    days_improving,
                    positive_evidence_count,
                    LESSON_MIN_POSITIVE_EVIDENCE,
                )
                continue

            # Neither gate met — stay improving.
            logger.debug(
                "Lesson '%s' still improving: sessions=%d/%d days=%.1f/%.1f "
                "pos_ev=%d/%d regressions=%d",
                lesson["category"],
                len(sessions),
                session_floor,
                days_improving,
                LESSON_MIN_RESOLUTION_DAYS,
                positive_evidence_count,
                LESSON_MIN_POSITIVE_EVIDENCE,
                regressions,
            )

        if transitioned:
            conn.commit()
        return transitioned
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

    # Mark improving lessons for categories that were clean this session.
    # These are absence-of-complaint signals — the quality check didn't
    # fail, but we don't have positive observation of the correct
    # behavior. Absence sessions advance toward DORMANT, not RESOLVED.
    for cat in clean_categories:
        if cat not in lesson_categories:
            mark_lesson_improving(cat, session_id)

    # blind_retry has a real positive-evidence channel: error recovery
    # logs show whether the agent investigated before retrying. Pass
    # evidence when it exists; fall back to absence-only if the session
    # happened to have no error recovery at all.
    if "blind_retry" not in lesson_categories and error_recovery:
        blind_retries = error_recovery.get("blind_retries", 0)
        investigate_count = error_recovery.get("investigate_count", 0)
        if blind_retries == 0 and investigate_count > 0:
            mark_lesson_improving(
                "blind_retry",
                session_id,
                evidence=(
                    f"investigated {investigate_count} error(s) before any retry (blind_retries=0)"
                ),
            )
        elif blind_retries == 0:
            # No errors this session at all — no positive evidence, just
            # absence. Still counts as a clean session for DORMANT math.
            mark_lesson_improving("blind_retry", session_id)

    # upset_recovered/upset_user: distinguish genuine recovery (positive
    # evidence) from "the user didn't get upset at all" (absence only).
    if "upset_recovered" not in lesson_categories and "upset_user" not in lesson_categories:
        if tone_shifts is not None:
            negatives = [t for t in tone_shifts if t.get("direction") == "negative"]
            positives = [t for t in tone_shifts if t.get("direction") == "positive"]
            if negatives and positives:
                # Real arc: user got upset AND things recovered. Positive
                # evidence for upset_recovered; still absence-only for
                # upset_user since the upset DID happen.
                mark_lesson_improving(
                    "upset_recovered",
                    session_id,
                    evidence=f"recovered from {len(negatives)} negative shift(s)",
                )
                mark_lesson_improving("upset_user", session_id)
            elif not negatives:
                # Quiet session — no positive evidence either way.
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
