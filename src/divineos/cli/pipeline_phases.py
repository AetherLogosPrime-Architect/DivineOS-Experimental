"""Pipeline phases — heavy-lifting steps extracted from session_pipeline.py.

Each function is a self-contained phase of the SESSION_END pipeline.
They handle their own errors (log + continue) so the orchestrator stays clean.
"""

import sqlite3
from typing import Any

import click
from loguru import logger

from divineos.cli._helpers import _safe_echo
from divineos.cli._wrappers import (
    _wrapped_consolidate_related,
    _wrapped_get_knowledge,
    _wrapped_health_check,
    _wrapped_refresh_active_memory,
    _wrapped_store_knowledge,
)
from divineos.core.constants import CONFIDENCE_ACTIVE_MEMORY_FLOOR, CONFIDENCE_RELIABLE
from divineos.core.memory import init_memory_tables

# Pipeline phases catch at integration boundaries — these are the real failure modes.
_PHASE_ERRORS = (ImportError, sqlite3.OperationalError, OSError, KeyError, TypeError)


# ─── Phase 3: Post-extraction processing ─────────────────────────────


def run_knowledge_post_processing(deep_ids: list[str], maturity_override: str) -> tuple[int, list]:
    """Apply maturity overrides, auto-link relationships, scan contradictions.

    Returns (extra_stored_count, auto_rels).
    """
    auto_rels: list = []

    # 3b. Maturity override
    if maturity_override and deep_ids:
        try:
            from divineos.core.knowledge import _get_connection

            conn = _get_connection()
            try:
                for did in deep_ids:
                    if did:
                        conn.execute(
                            "UPDATE knowledge SET maturity = ? WHERE knowledge_id = ? AND maturity = 'RAW'",
                            (maturity_override, did),
                        )
                conn.commit()
            finally:
                conn.close()
            click.secho(
                f"[~] Downgraded {len(deep_ids)} entries to {maturity_override}.", fg="yellow"
            )
        except _PHASE_ERRORS as e:
            logger.warning(f"Maturity override failed: {e}")

    # 3c. Auto-detect relationships
    try:
        from divineos.core.knowledge.relationships import auto_detect_relationships

        valid_ids = [did for did in deep_ids if did]
        auto_rels = auto_detect_relationships(valid_ids)
        if auto_rels:
            click.secho(f"[~] Auto-linked {len(auto_rels)} knowledge relationships.", fg="cyan")
    except _PHASE_ERRORS as e:
        logger.warning(f"Auto-relationship detection failed: {e}")

    # 3d. Contradiction scan
    try:
        from divineos.cli.pipeline_gates import run_contradiction_scan

        resolved = run_contradiction_scan(deep_ids)
        if resolved:
            click.secho(f"[~] Resolved {resolved} contradiction(s) in new knowledge.", fg="yellow")
    except _PHASE_ERRORS as e:
        logger.warning(f"Contradiction scan failed: {e}")

    # 3e. SIS — assess and translate esoteric language in new entries
    try:
        from divineos.core.knowledge import _get_connection
        from divineos.core.semantic_integrity import assess_and_translate

        valid_ids = [did for did in deep_ids if did]
        if valid_ids:
            conn = _get_connection()
            translated_count = 0
            quarantined_count = 0
            # Pass 1: scan and classify — read-only, single connection.
            # Pass 2: apply changes — each TRANSLATE uses update_knowledge()
            # (supersession), each QUARANTINE is a tag/confidence metadata
            # tweak (not a content mutation, so direct UPDATE is fine).
            translate_work: list[tuple[str, str]] = []  # (kid, translated_content)
            quarantine_work: list[str] = []  # kids to quarantine
            try:
                for kid in valid_ids:
                    row = conn.execute(
                        "SELECT content FROM knowledge WHERE knowledge_id = ?", (kid,)
                    ).fetchone()
                    if not row:
                        continue
                    content = row[0]
                    sis = assess_and_translate(content)
                    if sis["verdict"] == "TRANSLATE" and sis["changed"]:
                        translate_work.append((kid, sis["translated"]))
                    elif sis["verdict"] == "QUARANTINE":
                        quarantine_work.append(kid)
            finally:
                conn.close()

            # Pass 2a: supersede TRANSLATE candidates. Each call opens its
            # own connection — serial, fine for the volumes involved
            # (tens of entries per extract run, not thousands).
            if translate_work:
                from divineos.core.knowledge.crud import update_knowledge

                for kid, translated in translate_work:
                    try:
                        update_knowledge(
                            kid,
                            new_content=translated,
                            additional_tags=["sis-translated"],
                        )
                        translated_count += 1
                    except ValueError:
                        # Entry was deleted/superseded between pass 1 and 2 — skip
                        pass

            # Pass 2b: QUARANTINE is metadata-only (tags + confidence cap).
            # Legitimate in-place update, same class as maturity evolution.
            if quarantine_work:
                conn = _get_connection()
                try:
                    import json as _json

                    for kid in quarantine_work:
                        tags_row = conn.execute(
                            "SELECT tags FROM knowledge WHERE knowledge_id = ?", (kid,)
                        ).fetchone()
                        if not tags_row:
                            continue
                        tags = _json.loads(tags_row[0]) if tags_row[0] else []
                        if "sis-quarantined" not in tags:
                            tags.append("sis-quarantined")
                        conn.execute(
                            "UPDATE knowledge SET tags = ?, confidence = MIN(confidence, 0.4) "
                            "WHERE knowledge_id = ?",
                            (_json.dumps(tags), kid),
                        )
                        quarantined_count += 1
                    conn.commit()
                finally:
                    conn.close()

            if translated_count or quarantined_count:
                parts = []
                if translated_count:
                    parts.append(f"{translated_count} translated")
                if quarantined_count:
                    parts.append(f"{quarantined_count} quarantined")
                click.secho(f"[~] SIS: {', '.join(parts)}", fg="cyan")
    except _PHASE_ERRORS as e:
        logger.warning(f"SIS assessment failed: {e}")

    # 3f. Inference cycle — derive new knowledge from existing knowledge
    try:
        from divineos.core.knowledge.inference import run_inference_cycle

        inference = run_inference_cycle()
        total_inferred = sum(len(v) for v in inference.values())
        if total_inferred:
            parts = []
            if inference.get("boundaries"):
                parts.append(f"{len(inference['boundaries'])} boundaries")
            if inference.get("principles"):
                parts.append(f"{len(inference['principles'])} principles")
            if inference.get("insights"):
                parts.append(f"{len(inference['insights'])} insights")
            click.secho(f"[~] Inferred: {', '.join(parts)}", fg="cyan")
    except _PHASE_ERRORS as e:
        logger.warning(f"Inference cycle failed: {e}")

    return 0, auto_rels


# ─── Phase 4: Feedback and clarity ───────────────────────────────────


def run_feedback_cycle(
    analysis: Any, has_session: bool, session_tag: str
) -> tuple[list[str], Any, Any, int]:
    """Apply feedback, session feedback, and clarity analysis.

    Returns (feedback_parts, session_feedback, clarity_summary, extra_stored).
    """
    feedback_parts: list[str] = []
    session_feedback = None
    clarity_summary = None
    extra_stored = 0

    # 4. Apply feedback
    from divineos.cli._wrappers import _wrapped_apply_session_feedback

    feedback = _wrapped_apply_session_feedback(analysis, analysis.session_id)
    if feedback["recurrences_found"]:
        feedback_parts.append(f"{feedback['recurrences_found']} recurrences")
    if feedback["patterns_reinforced"]:
        feedback_parts.append(f"{feedback['patterns_reinforced']} patterns reinforced")
    if feedback["lessons_improving"]:
        feedback_parts.append(f"{feedback['lessons_improving']} lessons improving")
    if feedback.get("noise_skipped"):
        feedback_parts.append(f"{feedback['noise_skipped']} noise skipped")
    if feedback_parts:
        click.secho(f"[~] Feedback: {', '.join(feedback_parts)}", fg="cyan")

    # 4b. Session feedback
    try:
        from divineos.agent_integration.feedback_system import (
            generate_session_feedback,
            store_feedback_as_knowledge,
        )

        session_feedback = generate_session_feedback(analysis)
        if session_feedback.recommendations and not has_session:
            fb_id = store_feedback_as_knowledge(analysis.session_id, session_feedback, session_tag)
            if fb_id:
                extra_stored += 1
    except _PHASE_ERRORS as e:
        logger.warning(f"Session feedback failed: {e}")

    # 4c. Clarity pipeline
    try:
        from divineos.clarity_system.session_bridge import run_clarity_analysis

        clarity_result = run_clarity_analysis(analysis)
        clarity_summary = clarity_result["summary"]
        deviations = clarity_result["deviations"]
        lessons = clarity_result["lessons"]

        for dev in deviations:
            if dev.severity == "high" and not has_session:
                _wrapped_store_knowledge(
                    knowledge_type="OBSERVATION",
                    content=(
                        f"I deviated significantly in {dev.metric}: "
                        f"planned {dev.planned:.0f}, actual {dev.actual:.0f} "
                        f"({dev.percentage:.0f}% off, session {analysis.session_id[:12]})."
                    ),
                    confidence=CONFIDENCE_RELIABLE,
                    tags=["clarity-pipeline", "deviation", session_tag],
                )
                extra_stored += 1

        for lesson in lessons:
            if lesson.confidence >= CONFIDENCE_RELIABLE and not has_session:
                _wrapped_store_knowledge(
                    knowledge_type="OBSERVATION",
                    content=(
                        f"I noticed: {lesson.description}. "
                        f"{lesson.insight} (session {analysis.session_id[:12]})."
                    ),
                    confidence=lesson.confidence,
                    tags=["clarity-pipeline", "lesson", session_tag],
                )
                extra_stored += 1

        if deviations or lessons:
            click.secho(
                f"[~] Clarity: {len(deviations)} deviations, {len(lessons)} lessons, "
                f"{len(clarity_result['recommendations'])} recommendations.",
                fg="cyan",
            )
    except _PHASE_ERRORS as e:
        logger.warning(f"Clarity pipeline failed: {e}")

    # 4d. Auto-file curiosities from corrections (things we got wrong = things worth investigating)
    try:
        # Lite: divineos.core.curiosity_engine stripped — stub the imported symbols.
        def add_curiosity(*_a, **_k):
            return None

        def get_open_curiosities(*_a, **_k):
            return None

        existing = {c["question"][:50] for c in get_open_curiosities()}
        filed = 0
        for correction in analysis.corrections[:5]:
            # Extract the actual text content, not the object repr
            text = getattr(correction, "content", None)
            if text is None:
                text = correction if isinstance(correction, str) else str(correction)
            # Skip if it's still a repr or too short to be useful
            if text.startswith("UserSignal(") or len(text) < 15:
                continue
            # The correction text is the USER's words to me, not my mistake.
            # Frame the question so future-me reads it as "what was I doing
            # that prompted this?" — not "what was wrong about [user text]".
            question = f"What pattern of mine prompted this user correction: {text[:80]}?"
            if question[:50] not in existing:
                add_curiosity(question, category="correction")
                filed += 1
        if filed:
            click.secho(f"[~] Filed {filed} curiosities from corrections.", fg="cyan")
    except _PHASE_ERRORS as e:
        logger.warning(f"Auto-curiosity filing failed: {e}")

    return feedback_parts, session_feedback, clarity_summary, extra_stored


# ─── Phase 5: Knowledge quality cycle ────────────────────────────────


def run_knowledge_quality_cycle(deep_ids: list[str], analysis: Any) -> list[str]:
    """Health check, maturity promotions, logic pass, auto-answer check.

    Returns list of promoted knowledge IDs.
    """
    # 5. Health check
    try:
        hc = _wrapped_health_check()
        hc_parts = []
        if hc["confirmed_boosted"]:
            hc_parts.append(f"{hc['confirmed_boosted']} confirmed")
        if hc["recurring_escalated"]:
            hc_parts.append(f"{hc['recurring_escalated']} escalated")
        if hc["resolved_lessons"]:
            hc_parts.append(f"{hc['resolved_lessons']} resolved")
        if hc.get("needs_review_count"):
            hc_parts.append(f"{hc['needs_review_count']} needs review")
        if hc.get("temporal_decayed"):
            hc_parts.append(f"{hc['temporal_decayed']} temporal decayed")
        if hc.get("contradiction_flagged"):
            hc_parts.append(f"{hc['contradiction_flagged']} contradiction flagged")
        if hc_parts:
            click.secho(f"[~] Health: {', '.join(hc_parts)}", fg="cyan")
    except _PHASE_ERRORS as e:
        logger.warning(f"Health check failed: {e}")

    # 5b-pre. Lite: warrant backfill removed (logic.logic_reasoning stripped).

    # 5b. Maturity cycle
    promoted_ids: list[str] = []
    try:
        from divineos.core.knowledge_maintenance import run_maturity_cycle

        all_knowledge = _wrapped_get_knowledge(limit=500)
        promotions = run_maturity_cycle(all_knowledge)
        if promotions:
            promo_parts = [f"{v} to {k}" for k, v in promotions.items()]
            click.secho(f"[~] Maturity: {', '.join(promo_parts)}", fg="cyan")
            for entry in all_knowledge:
                mat = entry.get("maturity", "RAW")
                if mat in ("TESTED", "CONFIRMED"):
                    promoted_ids.append(entry["knowledge_id"])
    except _PHASE_ERRORS as e:
        logger.warning(f"Maturity cycle failed: {e}")

    # 5c. Lite: logic pass removed (logic.logic_session stripped).

    # 5d. Auto-answer check
    try:
        from divineos.core.questions import check_auto_answers, init_questions_table

        init_questions_table()
        valid_deep_ids = [did for did in deep_ids if did]
        for did in valid_deep_ids:
            from divineos.core.knowledge import _get_connection

            qa_conn = _get_connection()
            try:
                row = qa_conn.execute(
                    "SELECT content FROM knowledge WHERE knowledge_id = ?", (did,)
                ).fetchone()
            finally:
                qa_conn.close()
            if row:
                candidates = check_auto_answers(row[0], did)
                for c in candidates[:3]:
                    click.secho(
                        f"[?] New knowledge may answer: {c['question'][:80]}...", fg="yellow"
                    )
    except _PHASE_ERRORS as e:
        logger.warning(f"Auto-answer check failed: {e}")

    # 5e. Auto-distill raw entries from this session
    try:
        from divineos.core.knowledge import _get_connection
        from divineos.core.knowledge.deep_extraction import _distill_correction

        # Two-pass: scan read-only, then supersede via update_knowledge.
        # Same rationale as the SIS translation above — content changes
        # must supersede, not mutate in place (CLAUDE.md append-only rule).
        conn = _get_connection()
        distilled = 0
        raw_prefixes = ("I was corrected: ", "I should: ", "I decided: ")
        valid_ids = [did for did in deep_ids if did]
        distill_work: list[tuple[str, str]] = []  # (kid, cleaned_content)
        try:
            for kid in valid_ids:
                row = conn.execute(
                    "SELECT content FROM knowledge WHERE knowledge_id = ?", (kid,)
                ).fetchone()
                if not row:
                    continue
                content = row[0]
                for prefix in raw_prefixes:
                    if content.startswith(prefix):
                        stripped = content[len(prefix) :]
                        cleaned = _distill_correction(stripped)
                        if cleaned and cleaned != stripped:
                            distill_work.append((kid, cleaned))
                        break
        finally:
            conn.close()

        if distill_work:
            from divineos.core.knowledge.crud import update_knowledge

            for kid, cleaned in distill_work:
                try:
                    update_knowledge(
                        kid,
                        new_content=cleaned,
                        additional_tags=["auto-distilled"],
                    )
                    distilled += 1
                except ValueError:
                    # Entry was deleted/superseded between pass 1 and 2 — skip
                    pass

        if distilled:
            click.secho(f"[~] Auto-distilled {distilled} raw entries.", fg="cyan")
    except _PHASE_ERRORS as e:
        logger.warning(f"Auto-distill failed: {e}")

    # 5f. (Moved to 5b-pre — warrant backfill now runs before maturity cycle)

    # 5g. Drift detection — catch behavioral backsliding
    try:
        from divineos.core.drift_detection import run_drift_detection

        drift = run_drift_detection()
        severity = drift.get("severity", "none")
        if severity not in ("none", None):
            signal_count = drift.get("drift_signals", 0)
            click.secho(f"[!] Drift detected ({severity}): {signal_count} signal(s)", fg="yellow")
            for reg in drift.get("regressions", [])[:3]:
                click.secho(
                    f"     {reg.get('type', '?')}: {reg.get('detail', '')[:80]}", fg="yellow"
                )
            quality = drift.get("quality_drift", {})
            if quality.get("drifting"):
                click.secho(f"     quality_drift: {quality.get('detail', '')[:80]}", fg="yellow")
    except _PHASE_ERRORS as e:
        logger.warning(f"Drift detection failed: {e}")

    # 5h. Knowledge hygiene — demote noise, decay stale, flag orphans
    try:
        from divineos.core.knowledge_maintenance import run_knowledge_hygiene

        hygiene = run_knowledge_hygiene()
        hygiene_parts = []
        if hygiene["noise_demoted"]:
            hygiene_parts.append(f"{hygiene['noise_demoted']} demoted")
        if hygiene["noise_superseded"]:
            hygiene_parts.append(f"{hygiene['noise_superseded']} superseded")
        if hygiene.get("stale_decayed"):
            hygiene_parts.append(f"{hygiene['stale_decayed']} temporal decayed")
        if hygiene["orphans_flagged"]:
            hygiene_parts.append(f"{hygiene['orphans_flagged']} orphans flagged")
        if hygiene_parts:
            click.secho(f"[~] Hygiene: {', '.join(hygiene_parts)}", fg="cyan")
    except _PHASE_ERRORS as e:
        logger.warning(f"Knowledge hygiene failed: {e}")

    return promoted_ids


# ─── Phase 6-7: Consolidation and memory refresh ─────────────────────


def run_consolidation_and_refresh(analysis: Any) -> tuple[int, int]:
    """Consolidate related knowledge and refresh active memory.

    Returns (promoted, demoted).
    """
    # 6. Consolidate
    try:
        merges = _wrapped_consolidate_related(min_cluster_size=3)
        if merges:
            click.secho(f"[~] Consolidated {len(merges)} clusters of related knowledge.", fg="cyan")
    except _PHASE_ERRORS as e:
        logger.warning(f"Consolidation failed: {e}")

    # 6b. Knowledge compression — merge redundant entries
    try:
        from divineos.core.knowledge.compression import run_compression

        comp_results = run_compression(strategies=["dedup"])
        comp_total = comp_results.get("total_compressed", 0)
        if comp_total:
            click.secho(f"[~] Compressed {comp_total} redundant knowledge entries.", fg="cyan")
    except _PHASE_ERRORS as e:
        logger.warning(f"Knowledge compression failed: {e}")

    # 6c. Clean goals BEFORE refreshing core memory — stale goals pollute priorities
    try:
        from divineos.core.hud_state import auto_clean_goals

        goal_result = auto_clean_goals()
        goal_parts = []
        if goal_result.get("completed_cleared"):
            goal_parts.append(f"{goal_result['completed_cleared']} completed cleared")
        if goal_result["stale_archived"]:
            goal_parts.append(f"{goal_result['stale_archived']} stale archived")
        if goal_result["deduped"]:
            goal_parts.append(f"{goal_result['deduped']} duplicates removed")
        if goal_parts:
            click.secho(f"[~] Goals cleaned: {', '.join(goal_parts)}.", fg="cyan")
    except _PHASE_ERRORS as e:
        logger.warning(f"Goal cleanup failed: {e}")

    # 7. Refresh active memory
    promoted = 0
    demoted = 0
    try:
        init_memory_tables()
        refresh = _wrapped_refresh_active_memory(importance_threshold=0.3)
        promoted = refresh["promoted"]
        demoted = refresh["demoted"]
    except _PHASE_ERRORS as e:
        logger.warning(f"Memory refresh failed: {e}")

    # 7b. Refresh core memory (now reads from cleaned goals)
    try:
        from divineos.core.core_memory_refresh import refresh_core_memory

        core_updates = refresh_core_memory(analysis)
        updated_slots = [s for s, changed in core_updates.items() if changed]
        if updated_slots:
            click.secho(f"[~] Core memory refreshed: {', '.join(updated_slots)}", fg="cyan")
    except _PHASE_ERRORS as e:
        logger.warning(f"Core memory refresh failed: {e}")

    return promoted, demoted


# ─── Phase 8p-q: Lesson detection and escalation ────────────────────
#
# MUST run before corroboration sweep (Phase 8c) — lessons must be
# recorded first so maturity promotions reflect actual learning.


def run_lesson_detection(
    check_results: list,
    session_id: str,
    features: Any,
    analysis: Any = None,
) -> list[str]:
    """Detect and record lessons from quality checks + session features.

    Also runs auto-resolve (escalation) after detection so we don't
    resolve a lesson that just re-occurred this session.

    Returns list of lesson IDs detected.
    """
    lesson_ids: list[str] = []

    # 8p. Lesson detection from quality checks + features
    try:
        from divineos.core.knowledge.lessons import extract_lessons_from_report

        # Convert feature tone shifts to lesson-extraction format
        tone_shifts_for_lessons = None
        if features and hasattr(features, "tone_shifts") and features.tone_shifts:
            tone_shifts_for_lessons = [
                {
                    "direction": ("negative" if ts.new_tone == "negative" else "positive"),
                    "previous_tone": ts.previous_tone,
                    "new_tone": ts.new_tone,
                    "trigger": ts.trigger_action,
                    "user_response": getattr(ts, "after_message", ""),
                    "before_message": getattr(ts, "before_message", ""),
                    "sequence": ts.sequence,
                }
                for ts in features.tone_shifts
                if ts.previous_tone != ts.new_tone
            ]

        # Convert error recovery to aggregate counts
        error_recovery_for_lessons = None
        if features and hasattr(features, "error_recovery") and features.error_recovery:
            blind_retries = sum(1 for e in features.error_recovery if e.recovery_action == "retry")
            investigate_count = sum(
                1 for e in features.error_recovery if e.recovery_action == "investigate"
            )
            error_recovery_for_lessons = {
                "blind_retries": blind_retries,
                "investigate_count": investigate_count,
            }

        lesson_ids = extract_lessons_from_report(
            check_results,
            session_id,
            tone_shifts_for_lessons,
            error_recovery_for_lessons,
        )
        if lesson_ids:
            click.secho(
                f"[+] Lesson detection: {len(lesson_ids)} entries from quality checks",
                fg="green",
            )

        # 8p2. Accountability — did any CHRONIC lessons fire this session?
        try:
            from divineos.core.knowledge.lessons import get_chronic_lessons, get_lessons
            from divineos.core.ledger import log_event

            chronic = get_chronic_lessons()
            if chronic and lesson_ids:
                all_lessons = get_lessons()
                chronic_categories = {c["category"] for c in chronic}
                violated_chronic = [
                    ls
                    for ls in all_lessons
                    if ls["lesson_id"] in lesson_ids and ls["category"] in chronic_categories
                ]
                if violated_chronic:
                    click.secho(
                        f"[!!] ACCOUNTABILITY: {len(violated_chronic)} chronic "
                        f"lesson(s) violated this session.",
                        fg="red",
                        bold=True,
                    )
                    for vl in violated_chronic:
                        click.secho(
                            f"     - {vl['description'][:100]} ({vl['occurrences']}x total)",
                            fg="red",
                        )
                        log_event(
                            "ACCOUNTABILITY_VIOLATION",
                            "system",
                            {
                                "lesson_id": vl["lesson_id"],
                                "category": vl["category"],
                                "description": vl["description"][:200],
                                "occurrences": vl["occurrences"],
                                "session_id": session_id,
                            },
                            validate=False,
                        )
                    click.secho(
                        "     These violations will be reviewed by the council.",
                        fg="red",
                    )
        except _PHASE_ERRORS as e:
            logger.debug(f"Accountability check failed: {e}")
    except (*_PHASE_ERRORS, ValueError) as e:
        logger.debug(f"Lesson detection failed: {e}")

    # 8p3. Binary behavioral tests — pass/fail per chronic lesson
    try:
        from divineos.core.knowledge.lessons import (
            format_behavioral_test_results,
            run_behavioral_tests,
        )

        bt_results = run_behavioral_tests(analysis, features)
        if bt_results:
            bt_text = format_behavioral_test_results(bt_results)
            failed_count = sum(1 for r in bt_results if r["passed"] is False)
            color = "red" if failed_count > 0 else "green"
            click.secho(f"[~] {bt_text}", fg=color)
    except _PHASE_ERRORS as e:
        logger.debug(f"Behavioral testing failed: {e}")

    # 8q. Lesson escalation (auto-resolve)
    # Runs AFTER lesson detection so we don't resolve a lesson
    # that just re-occurred this session.
    try:
        from divineos.core.knowledge.lessons import auto_resolve_lessons

        resolved = auto_resolve_lessons()
        if resolved:
            names = ", ".join(r["category"] for r in resolved)
            click.secho(f"[+] Lessons resolved: {names}", fg="green")
    except _PHASE_ERRORS as e:
        logger.debug(f"Lesson escalation failed: {e}")

    return lesson_ids


# ─── Phase 8-9: Session scoring and finalization ─────────────────────


def run_session_scoring(analysis: Any, access_snapshot: dict[str, int]) -> dict[str, Any] | None:
    """Score session health, cleanup briefing, run corroboration sweep.

    Returns health dict or None.
    """
    health: dict[str, Any] | None = None

    # 8. Session health score
    try:
        from divineos.agent_integration.outcome_measurement import (
            match_corrections_to_resolutions,
            measure_session_health,
        )
        from divineos.core.hud_handoff import was_briefing_loaded

        # Position-based correction-resolution matching:
        # Sort all signals by timestamp to get interleaved sequence numbers,
        # then match encouragements to nearest preceding corrections.
        all_signals = [("c", s.timestamp) for s in analysis.corrections] + [
            ("e", s.timestamp) for s in analysis.encouragements
        ]
        all_signals.sort(key=lambda x: x[1])
        corr_seq = []
        enc_seq = []
        for seq, (kind, _) in enumerate(all_signals):
            if kind == "c":
                corr_seq.append(seq)
            else:
                enc_seq.append(seq)

        matched, unresolved = match_corrections_to_resolutions(corr_seq, enc_seq)
        resolved_count = sum(1 for m in matched if m.encouragement_index is not None)

        health = measure_session_health(
            corrections=len(unresolved),
            encouragements=len(analysis.encouragements),
            context_overflows=len(analysis.context_overflows),
            tool_calls=analysis.tool_calls_total,
            user_messages=analysis.user_messages,
            briefing_loaded=was_briefing_loaded(),
            resolved_corrections=resolved_count,
        )
        try:
            from divineos.core.hud_state import update_session_health

            update_session_health(
                corrections=len(analysis.corrections),
                encouragements=len(analysis.encouragements),
                grade=health["grade"],
            )
        except _PHASE_ERRORS as e:
            logger.debug("HUD session health update failed (best-effort): %s", e)
    except _PHASE_ERRORS as e:
        logger.warning(f"Session health scoring failed: {e}")

    # 8b2. Briefing marker — let it expire via TTL naturally.
    # Previously cleared here, but SESSION_END fires mid-session
    # (auto-emit at 150 tool calls, pre-compact hook) and clearing
    # the marker blocks the next tool call. The 4-hour TTL and
    # 400-tool-call threshold handle staleness without interrupting work.

    # 8c. Corroboration sweep
    try:
        from divineos.core.knowledge import _get_connection as _get_conn
        from divineos.core.knowledge_maintenance import increment_corroboration, promote_maturity

        corroborated = 0
        corroborated_ids: list[str] = []
        conn = _get_conn()
        current_rows = conn.execute(
            "SELECT knowledge_id, access_count FROM knowledge "
            "WHERE superseded_by IS NULL AND confidence >= ?",
            (CONFIDENCE_ACTIVE_MEMORY_FLOOR,),
        ).fetchall()
        conn.close()
        for kid, current_access in current_rows:
            start_access = access_snapshot.get(kid, 0)
            delta = current_access - start_access
            if delta >= 1:
                increment_corroboration(kid, source_context="session:end_sweep")
                promote_maturity(kid)
                corroborated += 1
                corroborated_ids.append(kid)
        if corroborated:
            click.secho(
                f"[~] Corroborated {corroborated} knowledge entries (accessed this session).",
                fg="cyan",
            )
            # Log to ledger — corroboration must be auditable
            try:
                from divineos.core.ledger import log_event

                log_event(
                    "KNOWLEDGE_CORROBORATED",
                    "session:end",
                    {
                        "count": corroborated,
                        "knowledge_ids": corroborated_ids[:20],  # cap payload size
                        "source": "session:end_sweep",
                    },
                    validate=False,
                )
            except (ImportError, sqlite3.OperationalError, OSError):
                pass  # Ledger logging is best-effort
    except _PHASE_ERRORS as e:
        logger.warning(f"Session-end corroboration sweep failed: {e}")

    return health


def run_session_finalization(
    analysis: Any, stored: int, health: dict[str, Any] | None, auto_rels: list, records: list
) -> None:
    """Save HUD, record growth metrics, tone, handoff note, sync memories."""
    # Capture engagement state BEFORE clearing it (step 9b needs this)
    was_engaged = False
    try:
        from divineos.core.hud_handoff import is_engaged

        was_engaged = is_engaged()
    except _PHASE_ERRORS:
        pass

    # 9. Save HUD snapshot
    #
    # Two mid-session state-clearers have been removed from this phase:
    #
    # - clear_engagement() (removed 2026-04-20 in PR #160): the
    #   thinking-gate marker was getting wiped on every consolidation,
    #   blocking legitimate same-session work after mid-session extract.
    # - clear_session_plan() (removed 2026-04-20 in this PR): same
    #   wrong-location pattern. Mid-session consolidation would erase the
    #   user's active session plan, which is annoying and has no valid
    #   reason — a plan set for today should persist across any number
    #   of consolidations today.
    #
    # Both clears now live in .claude/hooks/load-briefing.sh where they
    # semantically belong (actual Claude Code SessionStart = fresh
    # context = legitimately clear these). Mid-session consolidation
    # saves state via save_hud_snapshot() but does not reset anything.
    try:
        from divineos.core.hud import save_hud_snapshot

        save_hud_snapshot()
        click.secho("[~] HUD snapshot saved.", fg="cyan")
    except _PHASE_ERRORS as e:
        logger.warning(f"HUD snapshot save failed: {e}")

    # 9b. Growth metrics
    try:
        from divineos.core.growth import record_session_metrics

        record_session_metrics(
            session_id=analysis.session_id,
            corrections=len(analysis.corrections),
            encouragements=len(analysis.encouragements),
            tool_calls=analysis.tool_calls_total,
            user_messages=analysis.user_messages,
            knowledge_stored=stored,
            relationships_created=len(auto_rels),
            health_grade=health["grade"] if health else "",
            health_score=health["score"] if health else 0.0,
            engaged=was_engaged,
        )
    except _PHASE_ERRORS as e:
        logger.warning(f"Session metrics recording failed: {e}")

    # 9b2. Record skills from real competence signals (not tool counts)
    try:
        # Lite: divineos.core.skill_library stripped — stub the imported symbols.
        def detect_skills_from_events(*_a, **_k):
            return None

        def record_skill_use(*_a, **_k):
            return None

        skills_recorded = 0

        # Detect which skill domains were active this session
        session_events: list[str] = []
        for record in records:
            if isinstance(record, dict):
                for tc in record.get("content", []):
                    if isinstance(tc, dict):
                        name = tc.get("name", "")
                        text = tc.get("text", "")
                        if name:
                            session_events.append(name)
                        if text and len(text) > 10:
                            session_events.append(text[:200])

        active_domains = detect_skills_from_events(session_events)
        correction_count = len(analysis.corrections) if analysis else 0
        encouragement_count = len(analysis.encouragements) if analysis else 0

        # Corrections signal failure in the active domains
        # Encouragements signal success
        # No corrections + domain active = success (clean work)
        for domain in active_domains:
            if correction_count >= 3:
                # Multiple corrections while working in this domain = failure signal
                record_skill_use(domain, success=False, context="session corrections")
            elif encouragement_count >= 2 or correction_count == 0:
                # Encouragements or clean session = success signal
                record_skill_use(domain, success=True, context="clean session")
            skills_recorded += 1

        if skills_recorded:
            click.secho(
                f"[~] Recorded {skills_recorded} skill(s) from session signals "
                f"({correction_count} corrections, {encouragement_count} encouragements).",
                fg="cyan",
            )
    except _PHASE_ERRORS as e:
        logger.warning(f"Skill recording failed: {e}")

    # 9b3. Affect feedback — log how affect influenced this session
    try:
        from divineos.core.affect import get_session_affect_context

        affect_ctx = get_session_affect_context()
        modifiers = affect_ctx.get("modifiers", {})
        praise = affect_ctx.get("praise_chasing", {})
        if modifiers.get("verification_level") == "careful":
            click.secho(
                "[!] Affect: frustration detected — verification level was CAREFUL.", fg="yellow"
            )
        if modifiers.get("confidence_threshold_modifier", 0) > 0:
            click.secho(
                f"[~] Affect: extraction threshold raised by +{modifiers['confidence_threshold_modifier']:.1f}",
                fg="cyan",
            )
        if praise.get("detected"):
            click.secho(
                f"[!] PRAISE-CHASING [{praise['severity'].upper()}]: {praise['detail']}",
                fg="red",
                bold=True,
            )
    except _PHASE_ERRORS as e:
        logger.warning(f"Affect feedback failed: {e}")

    # 9c. Tone texture
    try:
        from divineos.analysis.tone_tracking import classify_all_user_tones

        # Lite: divineos.core.tone_texture stripped — stub the imported symbols.
        def compute_emotional_arc(*_a, **_k):
            return None

        def record_session_tone(*_a, **_k):
            return None

        tone_sequence = classify_all_user_tones(records)
        if tone_sequence:
            arc = compute_emotional_arc(tone_sequence)
            record_session_tone(analysis.session_id, arc)
            if arc.get("narrative"):
                _safe_echo(f"  Tone: {arc['narrative']}")
    except _PHASE_ERRORS as e:
        logger.warning(f"Tone texture recording failed: {e}")

    # 9d. Handoff note
    from divineos.cli.pipeline_gates import write_handoff_note

    write_handoff_note(analysis, stored, health)

    # 9e. Memory sync
    try:
        from divineos.core.memory_sync import sync_auto_memories

        sync_results = sync_auto_memories(analysis)
        synced = [f for f, changed in sync_results.items() if changed]
        if synced:
            click.secho(f"[~] Auto-memories synced: {', '.join(synced)}", fg="cyan")
    except (ImportError, OSError) as e:
        logger.debug(f"Memory sync skipped: {e}")

    # 9f. Ledger size guard — auto-compress if approaching limit
    try:
        from divineos.core.ledger_compressor import auto_compress_if_needed

        compress_result = auto_compress_if_needed()
        if compress_result:
            click.secho(
                f"[~] Ledger auto-compressed: {compress_result['compressed']} events "
                f"({compress_result['trigger']})",
                fg="cyan",
            )
    except _PHASE_ERRORS as e:
        logger.warning(f"Ledger size guard failed: {e}")


# ─── Phase 10: Summary ───────────────────────────────────────────────


def print_session_summary(
    stored: int,
    feedback_parts: list[str],
    promoted: int,
    demoted: int,
    health: dict[str, Any] | None,
    clarity_summary: Any,
    session_feedback: Any,
) -> None:
    """Print the end-of-session summary."""
    click.secho("\n=== Session Complete ===", fg="cyan", bold=True)
    click.secho(f"  Knowledge extracted:  {stored}", fg="white")
    if feedback_parts:
        click.secho(f"  Feedback applied:     {', '.join(feedback_parts)}", fg="white")
    if promoted or demoted:
        click.secho(f"  Active memory:        +{promoted} promoted, -{demoted} demoted", fg="white")
    if health:
        grade_color = {"A": "green", "B": "green", "C": "yellow", "D": "red", "F": "red"}
        click.secho(
            f"  Session grade:        {health['grade']} ({health['score']:.2f})",
            fg=grade_color.get(health["grade"], "white"),
        )
    if clarity_summary:
        score = clarity_summary.plan_vs_actual.alignment_score
        recs = clarity_summary.recommendations
        color = "green" if score >= 80 else "yellow" if score >= 50 else "red"
        click.secho(f"  Alignment score:      {score:.0f}%", fg=color)
        if recs:
            click.secho(f"  Clarity recs:         {len(recs)}", fg="white")
            for rec in recs[:3]:
                _safe_echo(f"    [{rec.priority}] {rec.recommendation_text}")
    if session_feedback and session_feedback.recommendations:
        click.secho(f"  Session recs:         {len(session_feedback.recommendations)}", fg="white")
        for fb_rec in session_feedback.recommendations[:3]:
            _safe_echo(f"    - {fb_rec}")
    # Rating solicitation — the one metric the system cannot game
    click.secho(
        "\n  💬 How was this session? Rate it 1-10:",
        fg="bright_white",
        bold=True,
    )
    click.secho(
        "     divineos rate <1-10> [comment]",
        fg="bright_black",
    )
    click.secho(
        "  Next session: run 'divineos hud' for full dashboard, or 'divineos briefing' for knowledge.",
        fg="bright_black",
    )
    click.echo()
