"""Extraction pipeline (formerly SESSION_END) — the full extract-consolidate-refresh cycle.

This file is the orchestrator. Each phase is a single function call to
pipeline_gates.py (enforcement) or pipeline_phases.py (heavy lifting).
"""

import sqlite3

import click

import divineos.analysis.session_analyzer as _analyzer_mod
import divineos.analysis.session_discovery as _discovery_mod
from divineos.cli._helpers import _safe_echo
from divineos.cli._wrappers import (
    _wrapped_deep_extract_knowledge,
    _wrapped_get_knowledge,
    _wrapped_health_check,
    _wrapped_store_knowledge,
    logger,
)
from divineos.cli.pipeline_gates import (
    enforce_briefing_gate,
    enforce_engagement_gate,
    run_goal_extraction,
    run_quality_gate,
)
from divineos.cli.pipeline_phases import (
    print_session_summary,
    run_consolidation_and_refresh,
    run_feedback_cycle,
    run_knowledge_post_processing,
    run_knowledge_quality_cycle,
    run_lesson_detection,
    run_session_finalization,
    run_session_scoring,
)
from divineos.core.constants import CONFIDENCE_RELIABLE


def _run_session_end_pipeline(session_start_override: float | None = None) -> None:
    """Post-SESSION_END learning pipeline — analyze, extract, consolidate, refresh.

    Args:
        session_start_override: If provided, use this as the session start timestamp
            instead of querying the ledger. This is needed because the SESSION_END
            event is emitted BEFORE this pipeline runs — so querying the ledger for
            the most recent SESSION_END would return the one we just wrote, not the
            previous session boundary.
    """
    session_files = _discovery_mod.find_sessions()
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
        try:
            _snap_rows = _snap_conn.execute(
                "SELECT knowledge_id, access_count FROM knowledge WHERE superseded_by IS NULL"
            ).fetchall()
            access_snapshot = {r[0]: r[1] for r in _snap_rows}
        finally:
            _snap_conn.close()
    except (ImportError, sqlite3.OperationalError) as e:
        logger.debug("Access snapshot unavailable (corroboration sweep will skip delta): %s", e)

    try:
        # ── Phase 1: Analysis and enforcement gates ──────────────
        # Scope analysis to current session to avoid re-counting signals
        # from previous sessions in accumulated JSONL transcripts.
        # Use the override if provided (captured BEFORE SESSION_END was emitted),
        # otherwise fall back to querying the ledger.
        session_start = session_start_override
        if session_start is None:
            try:
                from divineos.core.session_checkpoint import get_session_start_time

                session_start = get_session_start_time()
            except (ImportError, OSError):
                session_start = None
        analysis = _analyzer_mod.analyze_session(latest, since_timestamp=session_start)
        _safe_echo(analysis.summary())

        run_goal_extraction(analysis)
        enforce_briefing_gate()
        enforce_engagement_gate()

        quality_verdict, maturity_override, extract_allowed, check_results = run_quality_gate(
            latest, since_timestamp=session_start
        )
        if not extract_allowed:
            try:
                _wrapped_health_check()
            except (ImportError, sqlite3.OperationalError) as e:
                logger.warning("Health check failed after quality gate block: %s", e)
            try:
                from divineos.core.hud import save_hud_snapshot

                save_hud_snapshot()
            except (ImportError, OSError) as e:
                logger.debug("HUD snapshot failed after quality gate block: %s", e)

            # Bookkeeping must happen even when extraction is blocked —
            # the handoff note and goal cleanup are about session continuity,
            # not knowledge quality.
            try:
                from divineos.cli.pipeline_gates import write_handoff_note

                write_handoff_note(analysis, stored=0, health=None)
            except (ImportError, OSError, sqlite3.OperationalError) as e:
                logger.warning("Handoff note failed after quality gate block: %s", e)
            try:
                from divineos.core.hud_state import auto_clean_goals

                goal_result = auto_clean_goals()
                if any(goal_result.values()):
                    _safe_echo(
                        f"[~] Goals cleaned: {goal_result.get('stale_archived', 0)} stale, "
                        f"{goal_result.get('deduped', 0)} deduped, "
                        f"{goal_result.get('completed_cleared', 0)} cleared"
                    )
            except (ImportError, OSError) as e:
                logger.warning("Goal cleanup failed after quality gate block: %s", e)
            return

        # ── Phase 1b: Structured self-assessment ────────────────
        records = _analyzer_mod.load_records(latest, since_timestamp=session_start, slim=True)
        reflection = None
        try:
            from divineos.core.session_reflection import build_session_reflection

            reflection = build_session_reflection(analysis, records)
            click.secho(f"[~] Reflection: {reflection.summary()}", fg="cyan")

            # Store reflection learnings as knowledge
            from divineos.core.knowledge.extraction import store_knowledge_smart

            for learning in reflection.learnings:
                store_knowledge_smart(
                    knowledge_type="OBSERVATION",
                    content=learning,
                    confidence=CONFIDENCE_RELIABLE,
                    source="SYNTHESIZED",
                    maturity="HYPOTHESIS",
                    tags=["session-reflection", "auto-extracted"],
                )

            # Store recovery arcs as positive patterns
            for correction_text, recovery_text in reflection.recovery_arcs:
                store_knowledge_smart(
                    knowledge_type="OBSERVATION",
                    content=(
                        f"Recovery arc: corrected on '{correction_text[:80]}' "
                        f"then recovered with positive result."
                    ),
                    confidence=0.85,
                    source="SYNTHESIZED",
                    maturity="HYPOTHESIS",
                    tags=["session-reflection", "recovery-arc", "auto-extracted"],
                )
        except (ImportError, sqlite3.OperationalError, OSError, AttributeError) as e:
            logger.debug(f"Session reflection failed: {e}")

        # ── Phase 2: Deep extraction ─────────────────────────────
        # Actuator 1: affect-gated extraction confidence.
        # If the session was rough, raise the bar for truth.
        affect_penalty = 0.0
        try:
            from divineos.core.affect import compute_affect_modifiers

            modifiers = compute_affect_modifiers(lookback=5)
            affect_penalty = modifiers.get("confidence_threshold_modifier", 0.0)
            if affect_penalty > 0:
                click.secho(
                    f"[~] Affect gate: extraction confidence lowered by {affect_penalty:.2f}",
                    fg="yellow",
                )
        except (ImportError, sqlite3.OperationalError) as e:
            logger.debug("Affect modifier unavailable for extraction: %s", e)

        deep_ids = _wrapped_deep_extract_knowledge(
            analysis, records, affect_confidence_penalty=affect_penalty
        )
        stored = len(deep_ids)

        # ── Phase 3: Store episode + post-processing ─────────────
        session_tag = f"session-{analysis.session_id[:12]}"
        existing = _wrapped_get_knowledge(tags=[session_tag], limit=5)
        has_session = len(existing) > 0

        if not has_session:
            corrections = len(analysis.corrections)
            encouragements = len(analysis.encouragements)
            character = reflection.character if reflection else "unknown"
            episode_content = (
                f"Session character: {character}. "
                f"I had {analysis.user_messages} exchanges, made "
                f"{analysis.tool_calls_total} tool calls. "
                f"I was corrected {corrections} time{'s' if corrections != 1 else ''} "
                f"and encouraged {encouragements} time{'s' if encouragements != 1 else ''}. "
                f"{len(getattr(analysis, 'preferences', []))} preferences noted, "
                f"{len(analysis.context_overflows)} context overflows"
                f" (session {analysis.session_id[:12]})"
            )
            _wrapped_store_knowledge(
                knowledge_type="EPISODE",
                content=episode_content,
                confidence=1.0,
                tags=["session-analysis", "episode", session_tag],
            )
            stored += 1
        else:
            click.secho("[~] Session already scanned, skipping episode/fact.", fg="bright_black")

        click.secho(f"[+] Stored {stored} knowledge entries from session.", fg="green")

        _extra, auto_rels = run_knowledge_post_processing(deep_ids, maturity_override)

        # ── Phase 4: Feedback and clarity ────────────────────────
        feedback_parts, session_feedback, clarity_summary, extra = run_feedback_cycle(
            analysis, has_session, session_tag
        )
        stored += extra

        # ── Phase 5: Knowledge quality ───────────────────────────
        run_knowledge_quality_cycle(deep_ids, analysis)

        # ── Phase 6-7: Consolidation and memory refresh ──────────
        promoted, demoted = run_consolidation_and_refresh(analysis)

        # ── Phase 7b: Session features (needed by lesson detection) ──
        features = None  # type: ignore[assignment]
        try:
            from pathlib import Path

            from divineos.analysis.feature_storage import init_feature_tables, store_features
            from divineos.analysis.session_features import run_all_features

            init_feature_tables()
            features = run_all_features(Path(latest), since_timestamp=session_start)
            store_features(analysis.session_id, features)
            stored_features = (
                len(features.tone_shifts)
                + len(features.timeline)
                + len(features.files_touched)
                + len(features.error_recovery)
                + (1 if features.activity else 0)
                + (1 if features.task_tracking else 0)
            )
            if stored_features > 0:
                click.secho(
                    f"[+] Session features: {stored_features} records "
                    f"({len(features.tone_shifts)} tone shifts, "
                    f"{len(features.files_touched)} files, "
                    f"{len(features.error_recovery)} recoveries)",
                    fg="cyan",
                )
        except (ImportError, sqlite3.OperationalError, OSError, TypeError, ValueError) as e:
            logger.debug(f"Session features storage failed (best-effort): {e}")

        # ── Phase 7c: Lesson detection BEFORE corroboration ──────
        # Lessons must be recorded first so the corroboration sweep's
        # maturity promotions reflect actual learning patterns.
        run_lesson_detection(check_results, analysis.session_id, features, analysis)

        # ── Phase 8: Session scoring and corroboration ───────────
        health = run_session_scoring(analysis, access_snapshot)

        # ── Phase 8b: External validation — record self-grade ────
        try:
            from divineos.core.external_validation import record_self_grade

            if health:
                record_self_grade(
                    session_id=analysis.session_id,
                    grade=health["grade"],
                    score=health["score"],
                )
        except (ImportError, sqlite3.OperationalError, OSError) as e:
            logger.debug(f"External validation recording failed: {e}")

        # ── Phase 8c2: Knowledge impact assessment ───────────────
        try:
            from divineos.core.knowledge_impact import assess_session_impact

            # The briefing records retrievals under get_current_session_id(),
            # which may differ from analysis.session_id (JSONL filename).
            # Try both so the assessment finds the data regardless.
            correction_texts = [
                c if isinstance(c, str) else c.content for c in analysis.corrections
            ]
            impact = assess_session_impact(
                session_id=analysis.session_id,
                corrections=correction_texts,
            )
            if impact["retrieved"] == 0:
                try:
                    from divineos.core.session_manager import get_current_session_id

                    mgr_sid = get_current_session_id()
                    if mgr_sid != analysis.session_id:
                        impact = assess_session_impact(
                            session_id=mgr_sid,
                            corrections=correction_texts,
                        )
                except (RuntimeError, ImportError):
                    pass
            if impact["retrieved"] > 0:
                pct = impact["impact_score"] * 100
                click.secho(
                    f"[~] Knowledge impact: {pct:.0f}% effective "
                    f"({impact['clean']}/{impact['retrieved']} clean)",
                    fg="cyan" if pct >= 80 else "yellow",
                )
        except (ImportError, sqlite3.OperationalError, OSError) as e:
            logger.debug(f"Knowledge impact assessment failed: {e}")

        # ── Phase 8d: Curate knowledge layers ────────────────────
        try:
            from divineos.core.knowledge.curation import run_curation

            curation = run_curation()
            curation_parts = []
            if curation["archived"]:
                curation_parts.append(f"{curation['archived']} archived")
            if curation["promoted_stable"]:
                curation_parts.append(f"{curation['promoted_stable']} -> stable")
            if curation["promoted_urgent"]:
                curation_parts.append(f"{curation['promoted_urgent']} -> urgent")
            if curation["text_cleaned"]:
                curation_parts.append(f"{curation['text_cleaned']} text cleaned")
            if curation_parts:
                click.secho(f"[~] Curation: {', '.join(curation_parts)}", fg="cyan")
        except (ImportError, sqlite3.OperationalError, OSError) as e:
            logger.warning(f"Knowledge curation failed: {e}")

        # ── Phase 8f: SIS self-audit ��──────────────────────────
        try:
            from divineos.core.semantic_integrity import audit_knowledge_integrity

            audit = audit_knowledge_integrity(limit=100)
            if audit.get("entries_scanned", 0) > 0:
                tr = len(audit.get("translate_needed", []))
                qr = len(audit.get("quarantine_needed", []))
                if tr or qr:
                    click.secho(
                        f"[~] SIS audit: {tr} need translation, {qr} need review "
                        f"(avg integrity {audit['avg_integrity']:.2f})",
                        fg="yellow" if qr else "cyan",
                    )
        except (ImportError, sqlite3.OperationalError, OSError) as e:
            logger.debug(f"SIS self-audit failed: {e}")

        # ── Phase 8g: Compass reflection ────────────────────────
        try:
            from divineos.core.moral_compass import format_compass_brief, reflect_on_session

            compass_obs = reflect_on_session(analysis)
            if compass_obs:
                click.secho(f"[~] Compass: {len(compass_obs)} observations logged", fg="cyan")
                click.secho(format_compass_brief(), fg="bright_black")
        except (ImportError, sqlite3.OperationalError, OSError) as e:
            logger.debug(f"Compass reflection failed: {e}")

        # ── Phase 8h: Self-critique ─────────────────────────────
        try:
            from divineos.core.self_critique import assess_session_craft

            craft = assess_session_craft(analysis.session_id, analysis=analysis)
            if craft and craft.scores:
                low = [name for name, score in craft.scores.items() if score < 0.4]
                if low:
                    click.secho(f"[~] Self-critique: low on {', '.join(low)}", fg="yellow")
                else:
                    click.secho(f"[~] Self-critique: avg craft {craft.overall:.0%}", fg="cyan")
        except (ImportError, sqlite3.OperationalError, OSError, AttributeError) as e:
            logger.debug(f"Self-critique failed: {e}")

        # ── Phase 8h1b: Council review on significant sessions ───
        # The council is a thinking tool — 28 expert lenses that force
        # multi-angle analysis. Without enforcement, it never gets used.
        # Fire it on sessions with corrections or significant code work.
        try:
            corrections_count = len(analysis.corrections)
            tool_calls = getattr(analysis, "tool_calls_total", 0)
            if corrections_count >= 2 or tool_calls >= 20:
                from divineos.core.council.engine import get_council_engine
                from divineos.core.council.manager import CouncilManager

                engine = get_council_engine()
                mgr = CouncilManager(engine)
                character = reflection.character if reflection else "code session"
                council_problem = (
                    f"Session review ({character}): "
                    f"{corrections_count} corrections, {tool_calls} tool calls, "
                    f"{stored} knowledge entries stored. "
                    f"What patterns should I watch for? "
                    f"What might I be missing?"
                )
                council_result = mgr.convene(council_problem, max_experts=5)
                if council_result.selected_experts:
                    expert_names = [e.expert_name for e in council_result.selected_experts]
                    click.secho(
                        f"[~] Council: {', '.join(expert_names)} reviewed session",
                        fg="cyan",
                    )
                    # Store top council concerns as knowledge for future sessions
                    for a in council_result.analyses[:3]:
                        if a.concerns:
                            from divineos.core.knowledge.extraction import store_knowledge_smart

                            store_knowledge_smart(
                                knowledge_type="OBSERVATION",
                                content=(
                                    f"Council ({a.expert_name}) concern: {a.concerns[0][:200]}"
                                ),
                                confidence=0.7,
                                source="SYNTHESIZED",
                                maturity="HYPOTHESIS",
                                tags=["council-review", "auto-extracted", a.expert_name.lower()],
                            )
                            stored += 1
        except (ImportError, sqlite3.OperationalError, OSError, AttributeError) as e:
            logger.debug(f"Council review failed: {e}")

        # ── Phase 8h2: Convergence detection (Circuit 3) ────────
        try:
            from divineos.core.convergence_detector import (
                apply_convergence_to_knowledge,
                detect_convergence,
            )

            convergence = detect_convergence()
            if convergence.concerns:
                names = ", ".join(
                    f"{c.compass_spectrum}/{c.critique_spectrum}" for c in convergence.concerns
                )
                click.secho(f"[!] Circuit 3: convergent concerns -- {names}", fg="yellow")
                apply_convergence_to_knowledge(convergence)
            elif convergence.strengths:
                click.secho(
                    f"[~] Circuit 3: {len(convergence.strengths)} convergent strength(s)",
                    fg="cyan",
                )
            if convergence.divergences:
                click.secho(
                    f"[?] Circuit 3: {len(convergence.divergences)} divergence(s) — "
                    f"compass and self-critique disagree",
                    fg="bright_black",
                )
        except (ImportError, sqlite3.OperationalError, OSError, AttributeError) as e:
            logger.debug(f"Convergence detection failed: {e}")

        # ── Phase 8i: User model signals ────────────────────────
        try:
            from divineos.core.user_model import record_signal

            corrections = len(analysis.corrections)
            encouragements = len(analysis.encouragements)
            if corrections > 0:
                record_signal("correction_given", f"{corrections} corrections this session")
            if encouragements > 0:
                record_signal(
                    "encouragement_given", f"{encouragements} encouragements this session"
                )
            # Record preferences as skill/style signals
            for pref in getattr(analysis, "preferences", [])[:3]:
                record_signal("preference_stated", pref.content[:200])
            # Frustrations indicate interaction quality
            frustrations = len(getattr(analysis, "frustrations", []))
            if frustrations > 0:
                record_signal("frustration_shown", f"{frustrations} frustrations this session")
        except (ImportError, sqlite3.OperationalError, OSError) as e:
            logger.debug(f"User model signal recording failed: {e}")

        # ── Phase 8i2: Skill assessment — synthesize accumulated signals ──
        try:
            from divineos.core.user_model import update_skill_level

            update_skill_level()
        except (ImportError, sqlite3.OperationalError, OSError) as e:
            logger.debug(f"Skill level update failed: {e}")

        # ── Phase 8j: Communication calibration — detect preference signals ──
        try:
            from divineos.core.communication_calibration import detect_calibration_signals
            from divineos.core.user_model import record_signal

            # Scan user messages for communication preference signals
            user_text = " ".join(
                getattr(analysis, "user_message_texts", [])
                or [c.content for c in getattr(analysis, "corrections", [])]
            )
            if user_text:
                signals = detect_calibration_signals(user_text)
                for sig in signals[:5]:  # cap at 5 per session
                    record_signal(sig["signal_type"], sig.get("content", sig["signal_type"]))
                if signals:
                    click.secho(
                        f"[~] Calibration: detected {len(signals)} communication preference signal"
                        f"{'s' if len(signals) != 1 else ''}",
                        fg="cyan",
                    )
        except (ImportError, sqlite3.OperationalError, OSError, AttributeError, KeyError) as e:
            logger.debug(f"Calibration signal detection failed: {e}")

        # ── Phase 8k: Advice tracking — surface stale recommendations ──
        try:
            from divineos.core.advice_tracking import get_stale_advice

            stale = get_stale_advice(days=7)
            if stale:
                click.secho(
                    f"[~] {len(stale)} advice recommendation{'s' if len(stale) != 1 else ''} "
                    f"pending assessment — run: divineos advice list",
                    fg="yellow",
                )
        except (ImportError, sqlite3.OperationalError, OSError) as e:
            logger.debug(f"Advice tracking check failed: {e}")

        # ── Phase 8l: Auto-derive session affect ────────────────
        try:
            from divineos.core.session_affect import auto_log_session_affect

            affect_id = auto_log_session_affect(analysis, health)
            if affect_id:
                click.secho("[~] Affect: session state auto-logged", fg="cyan")
        except (ImportError, sqlite3.OperationalError, OSError) as e:
            logger.debug(f"Auto affect logging failed: {e}")

        # ── Phase 8l2: Verbosity link — frustration shifts communication ──
        # Actuator 2: if frustrations detected, lower verbosity preference.
        # A frustrated user has zero patience for filler.
        try:
            frustration_count = len(getattr(analysis, "frustrations", []))
            correction_count = len(getattr(analysis, "corrections", []))
            user_msg_count = getattr(analysis, "user_messages", 0)
            if user_msg_count > 0 and frustration_count > 0:
                from divineos.core.user_model import update_preferences

                frustration_ratio = frustration_count / user_msg_count
                if frustration_ratio > 0.15:
                    # Heavy frustration — go terse
                    update_preferences(verbosity="terse")
                    click.secho(
                        "[!] Calibration: frustration high — shifting to terse mode",
                        fg="yellow",
                    )
                elif frustration_ratio > 0.05 or correction_count >= 3:
                    # Moderate frustration — go concise
                    update_preferences(verbosity="concise")
                    click.secho(
                        "[~] Calibration: frustration detected — shifting to concise mode",
                        fg="yellow",
                    )
            elif user_msg_count > 5 and frustration_count == 0 and correction_count <= 1:
                # Clean session — drift back toward normal if currently restricted
                from divineos.core.user_model import get_or_create_user

                user = get_or_create_user()
                current_verbosity = user.get("preferences", {}).get("verbosity", "normal")
                if current_verbosity in ("terse", "concise"):
                    from divineos.core.user_model import update_preferences as _up

                    _up(verbosity="normal")
                    click.secho(
                        "[~] Calibration: clean session — verbosity restored to normal",
                        fg="cyan",
                    )
        except (ImportError, sqlite3.OperationalError, OSError, AttributeError) as e:
            logger.debug(f"Verbosity link failed: {e}")

        # ── Phase 8m: Affect-extraction calibration (Circuit 1) ──
        try:
            from divineos.core.affect import get_session_affect_context
            from divineos.core.affect_calibration import record_extraction_correlation

            affect_ctx = get_session_affect_context()
            record_extraction_correlation(
                session_id=analysis.session_id,
                affect_context=affect_ctx,
                knowledge_stored=stored,
                quality_verdict=quality_verdict.action if quality_verdict else "",
                quality_score=health.get("score", 0.0) if isinstance(health, dict) else 0.0,
                corrections=len(analysis.corrections),
                encouragements=len(analysis.encouragements),
                session_health_grade=health.get("grade", "") if isinstance(health, dict) else "",
            )
            click.secho("[~] Circuit 1: affect-extraction correlation recorded", fg="cyan")
        except (ImportError, sqlite3.OperationalError, OSError, AttributeError) as e:
            logger.debug(f"Affect calibration recording failed: {e}")

        # ── Phase 8n: Dead architecture alarm ───────────────────
        try:
            from divineos.core.dead_architecture_alarm import (
                format_alarm_summary,
                record_scan,
                run_full_scan,
            )

            alarm_result = run_full_scan()
            record_scan(alarm_result)
            click.secho(
                f"[~] Dead architecture: {format_alarm_summary(alarm_result)}",
                fg="yellow" if alarm_result.dormant_count > 0 else "cyan",
            )
        except (ImportError, sqlite3.OperationalError, OSError) as e:
            logger.debug(f"Dead architecture alarm failed: {e}")

        # ── Phase 8o-q: (moved to Phase 7b-7c — features + lessons ──
        #    now run BEFORE corroboration sweep so maturity
        #    promotions reflect actual learning patterns)

        # ── Phase 8r: Opinion auto-generation from session patterns ──
        try:
            from divineos.core.opinion_store import store_opinion

            opinions_formed = 0

            # 1. Advice outcomes → opinions about what works
            try:
                from divineos.core.advice_tracking import get_assessed_advice

                assessed = get_assessed_advice(limit=20)
                category_outcomes: dict[str, dict[str, int]] = {}
                for adv in assessed:
                    cat = adv.get("category", "general")
                    outcome = adv.get("outcome", "")
                    if cat not in category_outcomes:
                        category_outcomes[cat] = {"successful": 0, "failed": 0}
                    if outcome == "successful":
                        category_outcomes[cat]["successful"] += 1
                    elif outcome == "failed":
                        category_outcomes[cat]["failed"] += 1

                for cat, counts in category_outcomes.items():
                    if counts["successful"] >= 3 and counts["successful"] > counts["failed"] * 2:
                        store_opinion(
                            topic=f"advice-{cat}",
                            position=(
                                f"My {cat} advice is reliably good "
                                f"({counts['successful']} successes vs "
                                f"{counts['failed']} failures)"
                            ),
                            confidence=min(0.9, 0.5 + counts["successful"] * 0.05),
                            evidence=[
                                f"{counts['successful']} successful, {counts['failed']} failed"
                            ],
                            tags=["auto-generated", "advice-pattern"],
                        )
                        opinions_formed += 1
            except (ImportError, sqlite3.OperationalError, OSError, AttributeError):
                pass

            # 2. Correction patterns → opinions about weak areas
            if analysis and len(analysis.corrections) >= 3:
                store_opinion(
                    topic="session-corrections",
                    position=(
                        f"This session had {len(analysis.corrections)} corrections — "
                        f"accuracy under pressure needs work"
                    ),
                    confidence=0.6,
                    evidence=[c.content[:100] for c in analysis.corrections[:3]],
                    tags=["auto-generated", "correction-pattern"],
                )
                opinions_formed += 1

            # 3. Session quality → opinions about consistency
            if health and isinstance(health, dict):
                grade = health.get("grade", "")
                score = health.get("score", 0.0)
                if grade in ("A", "B") and score >= 0.8:
                    store_opinion(
                        topic="session-quality",
                        position=(
                            f"Session quality is consistently high "
                            f"(grade {grade}, score {score:.2f})"
                        ),
                        confidence=0.5 + score * 0.3,
                        evidence=[f"Session grade: {grade} ({score:.2f})"],
                        tags=["auto-generated", "quality-pattern"],
                    )
                    opinions_formed += 1

            if opinions_formed:
                click.secho(
                    f"[~] Auto-formed {opinions_formed} opinion(s) from session patterns",
                    fg="cyan",
                )
        except (ImportError, sqlite3.OperationalError, OSError, AttributeError) as e:
            logger.debug(f"Opinion auto-generation failed: {e}")

        # ── Phase 8s: Curiosity gap analysis ─────────────────────
        try:
            from divineos.core.curiosity_engine import generate_curiosities_from_gaps

            new_curiosities = generate_curiosities_from_gaps(max_questions=3)
            if new_curiosities:
                click.secho(
                    f"[~] Generated {len(new_curiosities)} curiosit"
                    f"{'y' if len(new_curiosities) == 1 else 'ies'}"
                    f" from knowledge gaps",
                    fg="cyan",
                )
        except (ImportError, sqlite3.OperationalError, OSError, AttributeError) as e:
            logger.debug(f"Curiosity gap analysis failed: {e}")

        # ── Phase 9: Finalization ────────────────────────────────
        run_session_finalization(analysis, stored, health, auto_rels, records)

        # ── Phase 10: Summary ────────────────────────────────────
        print_session_summary(
            stored, feedback_parts, promoted, demoted, health, clarity_summary, session_feedback
        )

    except (
        sqlite3.OperationalError,
        OSError,
        KeyError,
        TypeError,
        ValueError,
        AttributeError,
    ) as e:
        click.secho(f"[!] Auto-scan failed: {e}", fg="yellow")
        logger.warning(f"Auto-scan failed: {e}")

    # NOTE (2026-04-20): The reset_state() call that used to live here in a
    # finally block has been removed. That reset wiped session_start every
    # time the pipeline ran, which since PR #159 means every time
    # consolidation fires (write-count threshold, post-sleep, explicit).
    # The analyzer then only saw records since the last reset, producing
    # "Brief session (1 messages)" on every subsequent run — the surface
    # symptom that PR #159's trigger fix alone didn't close.
    #
    # Session boundary is now owned exclusively by load-briefing.sh, which
    # fires on actual Claude Code SessionStart and does the equivalent of
    # reset_state() there (writes checkpoint_state.json with a fresh
    # session_start). Mid-session consolidation no longer touches the
    # session boundary. Same pattern as the engagement-gate fix (PR #160).
