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
            for did in deep_ids:
                if did:
                    conn.execute(
                        "UPDATE knowledge SET maturity = ? WHERE knowledge_id = ? AND maturity = 'RAW'",
                        (maturity_override, did),
                    )
            conn.commit()
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
        from divineos.core.semantic_integrity import assess_and_translate
        from divineos.core.knowledge import _get_connection

        valid_ids = [did for did in deep_ids if did]
        if valid_ids:
            conn = _get_connection()
            translated_count = 0
            quarantined_count = 0
            for kid in valid_ids:
                row = conn.execute(
                    "SELECT content, tags FROM knowledge WHERE knowledge_id = ?", (kid,)
                ).fetchone()
                if not row:
                    continue
                content, tags_json = row[0], row[1]
                sis = assess_and_translate(content)
                if sis["verdict"] == "TRANSLATE" and sis["changed"]:
                    import json as _json

                    tags = _json.loads(tags_json) if tags_json else []
                    tags.append("sis-translated")
                    conn.execute(
                        "UPDATE knowledge SET content = ?, tags = ? WHERE knowledge_id = ?",
                        (sis["translated"], _json.dumps(tags), kid),
                    )
                    translated_count += 1
                elif sis["verdict"] == "QUARANTINE":
                    import json as _json

                    tags = _json.loads(tags_json) if tags_json else []
                    tags.append("sis-quarantined")
                    conn.execute(
                        "UPDATE knowledge SET tags = ?, confidence = MIN(confidence, 0.4) "
                        "WHERE knowledge_id = ?",
                        (_json.dumps(tags), kid),
                    )
                    quarantined_count += 1
            conn.commit()
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
                    confidence=0.8,
                    tags=["clarity-pipeline", "deviation", session_tag],
                )
                extra_stored += 1

        for lesson in lessons:
            if lesson.confidence >= 0.8 and not has_session:
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
        if hc.get("stale_decayed"):
            hc_parts.append(f"{hc['stale_decayed']} stale decayed")
        if hc.get("temporal_decayed"):
            hc_parts.append(f"{hc['temporal_decayed']} temporal decayed")
        if hc.get("contradiction_flagged"):
            hc_parts.append(f"{hc['contradiction_flagged']} contradiction flagged")
        if hc_parts:
            click.secho(f"[~] Health: {', '.join(hc_parts)}", fg="cyan")
    except _PHASE_ERRORS as e:
        logger.warning(f"Health check failed: {e}")

    # 5b. Maturity cycle
    promoted_ids: list[str] = []
    try:
        from divineos.core.knowledge_maturity import run_maturity_cycle

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

    # 5c. Logic pass
    try:
        from divineos.core.logic.session_logic import format_logic_summary, run_session_logic_pass

        valid_deep_ids = [did for did in deep_ids if did]
        logic_result = run_session_logic_pass(
            new_knowledge_ids=valid_deep_ids,
            promoted_ids=promoted_ids or None,
            session_id=analysis.session_id,
        )
        logic_line = format_logic_summary(logic_result)
        click.secho(f"[~] {logic_line}", fg="cyan")
        for detail in logic_result.details[:5]:
            click.secho(f"     {detail}", fg="bright_black")
    except _PHASE_ERRORS as e:
        logger.warning(f"Logic pass failed: {e}")

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

    # 7b. Refresh core memory
    try:
        from divineos.core.core_memory_refresh import refresh_core_memory

        core_updates = refresh_core_memory(analysis)
        updated_slots = [s for s, changed in core_updates.items() if changed]
        if updated_slots:
            click.secho(f"[~] Core memory refreshed: {', '.join(updated_slots)}", fg="cyan")
    except _PHASE_ERRORS as e:
        logger.warning(f"Core memory refresh failed: {e}")

    return promoted, demoted


# ─── Phase 8-9: Session scoring and finalization ─────────────────────


def run_session_scoring(analysis: Any, access_snapshot: dict[str, int]) -> dict[str, Any] | None:
    """Score session health, cleanup briefing, run corroboration sweep.

    Returns health dict or None.
    """
    health: dict[str, Any] | None = None

    # 8. Session health score
    try:
        from divineos.agent_integration.outcome_measurement import measure_session_health
        from divineos.core.hud_handoff import was_briefing_loaded

        health = measure_session_health(
            corrections=len(analysis.corrections),
            encouragements=len(analysis.encouragements),
            context_overflows=len(analysis.context_overflows),
            tool_calls=analysis.tool_calls_total,
            user_messages=analysis.user_messages,
            briefing_loaded=was_briefing_loaded(),
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

    # 8b2. Clear briefing marker
    try:
        from divineos.core.hud_handoff import clear_briefing_marker

        clear_briefing_marker()
    except _PHASE_ERRORS as e:
        logger.warning(f"Briefing marker cleanup failed: {e}")

    # 8c. Corroboration sweep
    try:
        from divineos.core.knowledge import _get_connection as _get_conn
        from divineos.core.knowledge_maturity import increment_corroboration, promote_maturity

        corroborated = 0
        conn = _get_conn()
        current_rows = conn.execute(
            "SELECT knowledge_id, access_count FROM knowledge "
            "WHERE superseded_by IS NULL AND confidence >= 0.3"
        ).fetchall()
        conn.close()
        for kid, current_access in current_rows:
            start_access = access_snapshot.get(kid, 0)
            delta = current_access - start_access
            if delta >= 2:
                increment_corroboration(kid)
                promote_maturity(kid)
                corroborated += 1
        if corroborated:
            click.secho(
                f"[~] Corroborated {corroborated} knowledge entries (accessed 2+ times).",
                fg="cyan",
            )
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

    # 9. Save HUD + clear plan
    try:
        from divineos.core.hud import save_hud_snapshot
        from divineos.core.hud_handoff import clear_engagement
        from divineos.core.hud_state import clear_session_plan

        save_hud_snapshot()
        clear_session_plan()
        clear_engagement()
        click.secho("[~] HUD snapshot saved.", fg="cyan")

        # Auto-clean stale and duplicate goals
        from divineos.core.hud_state import auto_clean_goals

        goal_result = auto_clean_goals()
        if goal_result["stale_archived"] or goal_result["deduped"]:
            click.secho(
                f"[~] Goals cleaned: {goal_result['stale_archived']} stale archived, "
                f"{goal_result['deduped']} duplicates removed.",
                fg="cyan",
            )
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

    # 9c. Tone texture
    try:
        from divineos.analysis.tone_tracking import classify_all_user_tones
        from divineos.core.tone_texture import compute_emotional_arc, record_session_tone

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
    click.secho(
        "  Next session: run 'divineos hud' for full dashboard, or 'divineos briefing' for knowledge.",
        fg="bright_black",
    )
    click.echo()
