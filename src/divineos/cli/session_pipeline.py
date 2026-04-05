"""SESSION_END pipeline — the full extract-consolidate-refresh cycle.

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
    run_session_finalization,
    run_session_scoring,
)


def _run_session_end_pipeline() -> None:
    """Post-SESSION_END learning pipeline — analyze, extract, consolidate, refresh."""
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
        _snap_rows = _snap_conn.execute(
            "SELECT knowledge_id, access_count FROM knowledge WHERE superseded_by IS NULL"
        ).fetchall()
        access_snapshot = {r[0]: r[1] for r in _snap_rows}
        _snap_conn.close()
    except (ImportError, sqlite3.OperationalError) as e:
        logger.debug("Access snapshot unavailable (corroboration sweep will skip delta): %s", e)

    try:
        # ── Phase 1: Analysis and enforcement gates ──────────────
        # Scope analysis to current session to avoid re-counting signals
        # from previous sessions in accumulated JSONL transcripts.
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

        quality_verdict, maturity_override, extract_allowed = run_quality_gate(latest)
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
            return

        # ── Phase 1b: Structured self-assessment ────────────────
        records = _analyzer_mod._load_records(latest)
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
                    confidence=0.8,
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
        deep_ids = _wrapped_deep_extract_knowledge(analysis, records)
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
                c if isinstance(c, str) else c.get("content", "")
                for c in analysis.corrections
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
                curation_parts.append(f"{curation['promoted_stable']} → stable")
            if curation["promoted_urgent"]:
                curation_parts.append(f"{curation['promoted_urgent']} → urgent")
            if curation["text_cleaned"]:
                curation_parts.append(f"{curation['text_cleaned']} text cleaned")
            if curation_parts:
                click.secho(f"[~] Curation: {', '.join(curation_parts)}", fg="cyan")
        except (ImportError, sqlite3.OperationalError, OSError) as e:
            logger.warning(f"Knowledge curation failed: {e}")

        # ── Phase 8e: Lesson escalation ────────────────────────
        try:
            from divineos.core.knowledge.lessons import auto_resolve_lessons

            resolved = auto_resolve_lessons()
            if resolved:
                names = ", ".join(r["category"] for r in resolved)
                click.secho(f"[+] Lessons resolved: {names}", fg="green")
        except (ImportError, sqlite3.OperationalError, OSError) as e:
            logger.debug(f"Lesson escalation failed: {e}")

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

            craft = assess_session_craft(analysis.session_id)
            if craft and craft.scores:
                low = [name for name, score in craft.scores.items() if score < 0.4]
                if low:
                    click.secho(f"[~] Self-critique: low on {', '.join(low)}", fg="yellow")
                else:
                    click.secho(f"[~] Self-critique: avg craft {craft.overall:.0%}", fg="cyan")
        except (ImportError, sqlite3.OperationalError, OSError, AttributeError) as e:
            logger.debug(f"Self-critique failed: {e}")

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
                click.secho(f"[!] Circuit 3: convergent concerns — {names}", fg="yellow")
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

        # ── Phase 8j: Communication calibration — detect preference signals ──
        try:
            from divineos.core.communication_calibration import detect_calibration_signals
            from divineos.core.user_model import record_signal

            # Scan user messages for communication preference signals
            user_text = " ".join(
                getattr(analysis, "user_messages_text", [])
                or [c.get("content", "") for c in getattr(analysis, "corrections", [])]
            )
            if user_text:
                signals = detect_calibration_signals(user_text)
                for sig in signals[:5]:  # cap at 5 per session
                    record_signal(sig["type"], sig.get("evidence", sig["type"]))
                if signals:
                    click.secho(
                        f"[~] Calibration: detected {len(signals)} communication preference signal"
                        f"{'s' if len(signals) != 1 else ''}",
                        fg="cyan",
                    )
        except (ImportError, sqlite3.OperationalError, OSError, AttributeError) as e:
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
            scan_id = record_scan(alarm_result)
            click.secho(
                f"[~] Dead architecture: {format_alarm_summary(alarm_result)}",
                fg="yellow" if alarm_result.dormant_count > 0 else "cyan",
            )
        except (ImportError, sqlite3.OperationalError, OSError) as e:
            logger.debug(f"Dead architecture alarm failed: {e}")

        # ── Phase 8o: Session features storage ────────────────────
        # Run deep feature analysis (tone shifts, timeline, files,
        # activity, error recovery) and store results. Previously
        # only available via manual `divineos analyze` command.
        try:
            from pathlib import Path

            from divineos.analysis.feature_storage import init_feature_tables, store_features
            from divineos.analysis.session_features import run_all_features

            init_feature_tables()
            features = run_all_features(Path(latest))
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
