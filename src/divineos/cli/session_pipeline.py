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
        analysis = _analyzer_mod.analyze_session(latest)
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

        # ── Phase 2: Deep extraction ─────────────────────────────
        records = _analyzer_mod._load_records(latest)
        deep_ids = _wrapped_deep_extract_knowledge(analysis, records)
        stored = len(deep_ids)

        # ── Phase 3: Store episode + post-processing ─────────────
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
