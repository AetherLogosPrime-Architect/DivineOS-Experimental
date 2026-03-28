"""SESSION_END pipeline — the full extract-consolidate-refresh cycle."""

from typing import Any

import click

import divineos.analysis.session_analyzer as _analyzer_mod
from divineos.cli._helpers import _safe_echo
from divineos.cli._wrappers import (
    _wrapped_apply_session_feedback,
    _wrapped_consolidate_related,
    _wrapped_deep_extract_knowledge,
    _wrapped_get_knowledge,
    _wrapped_health_check,
    _wrapped_refresh_active_memory,
    _wrapped_store_knowledge,
    logger,
)
from divineos.core.memory import init_memory_tables


def _run_session_end_pipeline() -> None:
    """Post-SESSION_END learning pipeline.

    Runs the full extract-consolidate-refresh cycle:
    1. Analyze latest session file
    2. Deep extract knowledge (corrections, preferences, decisions)
    3. Store session episode + tool usage (with dedup)
    4. Apply feedback (recurrence, reinforcement)
    5. Run health check (boost confirmed, escalate recurring)
    6. Consolidate related knowledge clusters
    7. Refresh active memory for next session
    8. Print session summary
    """
    session_files = _analyzer_mod.find_sessions()
    if not session_files:
        click.secho("[~] No session files found for auto-scan.", fg="bright_black")
        return

    latest = session_files[0]
    click.secho(f"\n[~] Auto-scanning session: {latest.stem[:16]}...", fg="cyan")

    # Snapshot knowledge access counts before the pipeline runs.
    access_snapshot: dict[str, int] = {}
    try:
        from divineos.core.knowledge import _get_connection

        _snap_conn = _get_connection()
        _snap_rows = _snap_conn.execute(
            "SELECT knowledge_id, access_count FROM knowledge WHERE superseded_by IS NULL"
        ).fetchall()
        access_snapshot = {r[0]: r[1] for r in _snap_rows}
        _snap_conn.close()
    except Exception as e:
        logger.debug("Access snapshot unavailable (corroboration sweep will skip delta): %s", e)

    try:
        # 1. Analyze
        analysis = _analyzer_mod.analyze_session(latest)
        _safe_echo(analysis.summary())

        # 1b. Extract goals from user messages into HUD
        try:
            from divineos.core.hud_handoff import extract_goals_from_messages
            from divineos.core.hud_state import add_goal

            extracted_goals = extract_goals_from_messages(analysis.user_message_texts)
            for goal in extracted_goals:
                add_goal(goal["text"], original_words=goal["original_words"])
            if extracted_goals:
                click.secho(
                    f"[~] Captured {len(extracted_goals)} goals from user messages.", fg="cyan"
                )
        except Exception as e:
            logger.warning(f"Goal extraction failed: {e}")

        # 1c. Quality gate
        quality_verdict = None
        maturity_override = ""
        try:
            from divineos.analysis.quality_checks import run_all_checks
            from divineos.analysis.quality_storage import store_report
            from divineos.core.quality_gate import assess_session_quality, should_extract_knowledge

            report = run_all_checks(latest)
            store_report(report)
            check_results = [
                {"check_name": c.check_name, "passed": c.passed, "score": c.score}
                for c in report.checks
            ]
            quality_verdict = assess_session_quality(check_results)
            extract_allowed, maturity_override = should_extract_knowledge(quality_verdict)

            if quality_verdict.action == "BLOCK":
                click.secho(
                    f"[!] Quality gate BLOCKED: {quality_verdict.reason}", fg="red", bold=True
                )
                click.secho("[!] Skipping knowledge extraction for this session.", fg="red")
                try:
                    _wrapped_health_check()
                except Exception as e:
                    logger.warning("Health check failed after quality gate block: %s", e)
                try:
                    from divineos.core.hud import save_hud_snapshot

                    save_hud_snapshot()
                except Exception as e:
                    logger.debug(
                        "HUD snapshot failed after quality gate block (best-effort): %s", e
                    )
                return
            elif quality_verdict.action == "DOWNGRADE":
                click.secho(f"[!] Quality gate DOWNGRADE: {quality_verdict.reason}", fg="yellow")
        except Exception as e:
            logger.warning(f"Quality gate failed (allowing extraction): {e}")

        # 2. Deep extract
        records = _analyzer_mod._load_records(latest)
        deep_ids = _wrapped_deep_extract_knowledge(analysis, records)
        stored = len(deep_ids)

        # 3. Store episode + tool usage (dedup by session tag)
        session_tag = f"session-{analysis.session_id[:12]}"
        existing = _wrapped_get_knowledge(tags=[session_tag], limit=5)
        has_session = len(existing) > 0

        if not has_session:
            corrections = len(analysis.corrections)
            encouragements = len(analysis.encouragements)
            _wrapped_store_knowledge(
                knowledge_type="EPISODE",
                content=(
                    f"I had {analysis.user_messages} exchanges, made "
                    f"{analysis.tool_calls_total} tool calls. "
                    f"I was corrected {corrections} time{'s' if corrections != 1 else ''} "
                    f"and encouraged {encouragements} time{'s' if encouragements != 1 else ''}. "
                    f"{len(getattr(analysis, 'preferences', []))} preferences noted, "
                    f"{len(analysis.context_overflows)} context overflows"
                    f" (session {analysis.session_id[:12]})"
                ),
                confidence=1.0,
                tags=["session-analysis", "episode", session_tag],
            )
            stored += 1
        else:
            click.secho("[~] Session already scanned, skipping episode/fact.", fg="bright_black")

        click.secho(f"[+] Stored {stored} knowledge entries from session.", fg="green")

        # 3b. Apply maturity override if quality was downgraded
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
            except Exception as e:
                logger.warning(f"Maturity override failed: {e}")

        # 3c. Auto-detect relationships between new and existing knowledge
        try:
            from divineos.core.knowledge.relationships import auto_detect_relationships

            valid_ids = [did for did in deep_ids if did]
            auto_rels = auto_detect_relationships(valid_ids)
            if auto_rels:
                click.secho(f"[~] Auto-linked {len(auto_rels)} knowledge relationships.", fg="cyan")
        except Exception as e:
            logger.warning(f"Auto-relationship detection failed: {e}")

        # 4. Apply feedback
        feedback = _wrapped_apply_session_feedback(analysis, analysis.session_id)
        feedback_parts: list[str] = []
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
        session_feedback = None
        try:
            from divineos.agent_integration.feedback_system import (
                generate_session_feedback,
                store_feedback_as_knowledge,
            )

            session_feedback = generate_session_feedback(analysis)
            if session_feedback.recommendations and not has_session:
                fb_id = store_feedback_as_knowledge(
                    analysis.session_id, session_feedback, session_tag
                )
                if fb_id:
                    stored += 1
        except Exception as e:
            logger.warning(f"Session feedback failed: {e}")

        # 4c. Clarity pipeline
        clarity_summary = None
        try:
            from divineos.clarity_system.session_bridge import run_clarity_analysis

            clarity_result = run_clarity_analysis(analysis)
            clarity_summary = clarity_result["summary"]
            deviations = clarity_result["deviations"]
            lessons = clarity_result["lessons"]
            recommendations = clarity_result["recommendations"]

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
                    stored += 1

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
                    stored += 1

            if deviations or lessons:
                click.secho(
                    f"[~] Clarity: {len(deviations)} deviations, {len(lessons)} lessons, "
                    f"{len(recommendations)} recommendations.",
                    fg="cyan",
                )
        except Exception as e:
            logger.warning(f"Clarity pipeline failed: {e}")

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
        except Exception as e:
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
                # Collect promoted IDs for logic pass
                for entry in all_knowledge:
                    mat = entry.get("maturity", "RAW")
                    if mat in ("TESTED", "CONFIRMED"):
                        promoted_ids.append(entry["knowledge_id"])
        except Exception as e:
            logger.warning(f"Maturity cycle failed: {e}")

        # 5c. Logic pass — consistency, inference, defeat scanning
        try:
            from divineos.core.logic.session_logic import (
                format_logic_summary,
                run_session_logic_pass,
            )

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
        except Exception as e:
            logger.warning(f"Logic pass failed: {e}")

        # 5d. Check if new knowledge answers open questions
        try:
            from divineos.core.questions import check_auto_answers, init_questions_table

            init_questions_table()
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
                            f"[?] New knowledge may answer: {c['question'][:80]}...",
                            fg="yellow",
                        )
        except Exception as e:
            logger.warning(f"Auto-answer check failed: {e}")

        # 6. Consolidate related
        try:
            merges = _wrapped_consolidate_related(min_cluster_size=3)
            if merges:
                click.secho(
                    f"[~] Consolidated {len(merges)} clusters of related knowledge.", fg="cyan"
                )
        except Exception as e:
            logger.warning(f"Consolidation failed: {e}")

        # 7. Refresh active memory
        promoted = 0
        demoted = 0
        try:
            init_memory_tables()
            refresh = _wrapped_refresh_active_memory(importance_threshold=0.3)
            promoted = refresh["promoted"]
            demoted = refresh["demoted"]
        except Exception as e:
            logger.warning(f"Memory refresh failed: {e}")

        # 8. Session health score
        health: dict[str, Any] | None = None
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
            grade_color = {"A": "green", "B": "green", "C": "yellow", "D": "red", "F": "red"}

            try:
                from divineos.core.hud_state import update_session_health

                update_session_health(
                    corrections=len(analysis.corrections),
                    encouragements=len(analysis.encouragements),
                    grade=health["grade"],
                )
            except Exception as e:
                logger.debug("HUD session health update failed (best-effort): %s", e)
        except Exception as e:
            health = None
            logger.warning(f"Session health scoring failed: {e}")

        # 8b. Engagement check
        try:
            from divineos.core.hud_handoff import is_engaged

            if not is_engaged():
                from divineos.core.knowledge import record_lesson

                record_lesson(
                    category="blind_coding",
                    description=(
                        "I coded through an entire session without consulting the OS "
                        "(ask, recall, directives, briefing). "
                        f"Session {analysis.session_id[:12]}."
                    ),
                    session_id=analysis.session_id,
                )
                click.secho(
                    "[!] No thinking queries this session — recorded as blind_coding lesson.",
                    fg="red",
                    bold=True,
                )
        except Exception as e:
            logger.warning(f"Engagement check failed: {e}")

        # 8b2. Briefing gate — structural penalty, not just a lesson
        try:
            from divineos.core.hud_handoff import (
                briefing_staleness,
                clear_briefing_marker,
            )

            staleness = briefing_staleness()
            if not staleness["loaded"]:
                click.secho(
                    "[!] Briefing was never loaded. Grade penalized by -0.25.",
                    fg="red",
                    bold=True,
                )
                click.secho(
                    "    This is structural, not a suggestion. Load briefing first next time.",
                    fg="red",
                )
            elif staleness["stale"]:
                click.secho(
                    f"[!] Briefing went stale ({staleness['calls_since']} tool calls since load). "
                    f"Re-load after ~{staleness['threshold']} tool calls to stay oriented.",
                    fg="yellow",
                    bold=True,
                )
            clear_briefing_marker()
        except Exception as e:
            logger.warning(f"Briefing gate check failed: {e}")

        # 8c. Session-end corroboration sweep
        try:
            from divineos.core.knowledge import _get_connection as _get_conn
            from divineos.core.knowledge_maturity import (
                increment_corroboration,
                promote_maturity,
            )

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
        except Exception as e:
            logger.warning(f"Session-end corroboration sweep failed: {e}")

        # 9. Save HUD snapshot and clear session plan
        try:
            from divineos.core.hud import save_hud_snapshot
            from divineos.core.hud_handoff import clear_engagement
            from divineos.core.hud_state import clear_session_plan

            save_hud_snapshot()
            clear_session_plan()
            clear_engagement()
            click.secho("[~] HUD snapshot saved.", fg="cyan")
        except Exception as e:
            logger.warning(f"HUD snapshot save failed: {e}")

        # 9b. Record session metrics for growth tracking
        try:
            from divineos.core.growth import record_session_metrics
            from divineos.core.hud_handoff import is_engaged

            auto_rel_count = len(auto_rels) if "auto_rels" in dir() else 0
            record_session_metrics(
                session_id=analysis.session_id,
                corrections=len(analysis.corrections),
                encouragements=len(analysis.encouragements),
                tool_calls=analysis.tool_calls_total,
                user_messages=analysis.user_messages,
                knowledge_stored=stored,
                relationships_created=auto_rel_count,
                health_grade=health["grade"] if health else "",
                health_score=health["score"] if health else 0.0,
                engaged=is_engaged(),
            )
        except Exception as e:
            logger.warning(f"Session metrics recording failed: {e}")

        # 9c. Record emotional arc for tone texture
        try:
            from divineos.analysis.tone_tracking import classify_all_user_tones
            from divineos.core.tone_texture import (
                compute_emotional_arc,
                record_session_tone,
            )

            tone_sequence = classify_all_user_tones(records)
            if tone_sequence:
                arc = compute_emotional_arc(tone_sequence)
                record_session_tone(analysis.session_id, arc)
                if arc.get("narrative"):
                    _safe_echo(f"  Tone: {arc['narrative']}")
        except Exception as e:
            logger.warning(f"Tone texture recording failed: {e}")

        # 9d. Write handoff note for next session
        try:
            from divineos.core.hud_handoff import save_handoff_note

            # Build summary from what we know
            handoff_summary_parts = []
            handoff_summary_parts.append(
                f"Last session: {analysis.user_messages} exchanges, "
                f"{stored} knowledge entries extracted."
            )
            if len(analysis.corrections) > 0:
                handoff_summary_parts.append(
                    f"I was corrected {len(analysis.corrections)} time(s) — review what went wrong."
                )
            if health:
                handoff_summary_parts.append(f"Session grade: {health['grade']}.")

            # Open threads from corrections and decisions
            open_threads: list[str] = []
            for corr in analysis.corrections[:3]:
                text = corr if isinstance(corr, str) else str(corr)
                open_threads.append(f"Correction: {text[:120]}")
            for d in getattr(analysis, "decisions", [])[:2]:
                text = d if isinstance(d, str) else str(d)
                open_threads.append(f"Decision: {text[:120]}")

            # Mood from health grade
            mood = ""
            if health:
                mood = {
                    "A": "strong session",
                    "B": "solid session",
                    "C": "mixed session",
                    "D": "rough session",
                    "F": "difficult session",
                }.get(health["grade"], "")

            # Goals state
            goals_state = ""
            try:
                import json as _json
                from divineos.core.hud import _ensure_hud_dir

                goals_path = _ensure_hud_dir() / "active_goals.json"
                if goals_path.exists():
                    goals = _json.loads(goals_path.read_text(encoding="utf-8"))
                    active = [g for g in goals if g.get("status") != "done"]
                    done = [g for g in goals if g.get("status") == "done"]
                    goals_state = f"{len(done)} completed, {len(active)} still active"
            except Exception:
                pass

            save_handoff_note(
                summary=" ".join(handoff_summary_parts),
                open_threads=open_threads,
                mood=mood,
                goals_state=goals_state,
                session_id=analysis.session_id,
            )
            click.secho("[~] Handoff note saved for next session.", fg="cyan")
        except Exception as e:
            logger.warning(f"Handoff note failed: {e}")

        # 10. Session summary
        click.secho("\n=== Session Complete ===", fg="cyan", bold=True)
        click.secho(f"  Knowledge extracted:  {stored}", fg="white")
        if feedback_parts:
            click.secho(f"  Feedback applied:     {', '.join(feedback_parts)}", fg="white")
        if promoted or demoted:
            click.secho(
                f"  Active memory:        +{promoted} promoted, -{demoted} demoted", fg="white"
            )
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
            click.secho(
                f"  Session recs:         {len(session_feedback.recommendations)}", fg="white"
            )
            for fb_rec in session_feedback.recommendations[:3]:
                _safe_echo(f"    - {fb_rec}")
        click.secho(
            "  Next session: run 'divineos hud' for full dashboard, or 'divineos briefing' for knowledge.",
            fg="bright_black",
        )
        click.echo()

    except Exception as e:
        click.secho(f"[!] Auto-scan failed: {e}", fg="yellow")
        logger.warning(f"Auto-scan failed: {e}")
