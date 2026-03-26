"""DivineOS CLI - Foundation Memory & Knowledge.

Commands for managing the event ledger, ingesting conversations,
verifying data integrity, and consolidating knowledge.
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import click


import divineos.analysis.session_analyzer as _analyzer_mod
from divineos.analysis.analysis import (
    analyze_session,
    format_analysis_report,
    save_analysis_report,
    store_analysis,
)
from divineos.analysis.quality_checks import init_quality_tables
from divineos.analysis.session_features import (
    get_cross_session_summary,
    init_feature_tables,
    run_all_features,
    store_features,
)
from divineos.core.consolidation import (
    KNOWLEDGE_TYPES,
    apply_session_feedback,
    clear_lessons,
    consolidate_related,
    deep_extract_knowledge,
    generate_briefing,
    get_knowledge,
    get_lesson_summary,
    get_lessons,
    health_check,
    init_knowledge_table,
    knowledge_health_report,
    knowledge_stats,
    migrate_knowledge_types,
    rebuild_fts_index,
    search_knowledge,
    store_knowledge,
)
from divineos.core.enforcement import capture_user_input, setup_cli_enforcement
from divineos.core.fidelity import create_manifest, create_receipt, reconcile
from divineos.core.ledger import (
    clean_corrupted_events,
    count_events,
    export_to_markdown,
    get_events,
    get_recent_context,
    init_db,
    log_event,
    logger,
    search_events,
    verify_all_events,
)
from divineos.core.memory import (
    CORE_SLOTS,
    clear_core,
    format_core,
    format_recall,
    get_active_memory,
    init_memory_tables,
    promote_to_active,
    recall,
    refresh_active_memory,
    set_core,
)
from divineos.core.parser import parse_jsonl, parse_markdown_chat
from divineos.core.tool_wrapper import wrap_tool_execution


_EMOJI_MEANINGS: dict[str, str] = {
    "\U0001f614": "(upset)",
    "\U0001f622": "(crying)",
    "\U0001f62d": "(sobbing)",
    "\U0001f620": "(angry)",
    "\U0001f621": "(furious)",
    "\U0001f610": "(neutral)",
    "\U0001f642": "(smile)",
    "\U0001f600": "(grinning)",
    "\U0001f601": "(beaming)",
    "\U0001f603": "(happy)",
    "\U0001f604": "(laughing)",
    "\U0001f605": "(laughing nervously)",
    "\U0001f606": "(laughing hard)",
    "\U0001f609": "(wink)",
    "\U0001f60a": "(warm smile)",
    "\U0001f60d": "(heart eyes)",
    "\U0001f60e": "(cool)",
    "\U0001f60f": "(smirk)",
    "\U0001f612": "(unamused)",
    "\U0001f615": "(confused)",
    "\U0001f616": "(frustrated)",
    "\U0001f618": "(kiss)",
    "\U0001f61b": "(tongue out)",
    "\U0001f61c": "(playful wink)",
    "\U0001f61e": "(disappointed)",
    "\U0001f624": "(frustrated)",
    "\U0001f625": "(relieved)",
    "\U0001f629": "(weary)",
    "\U0001f62b": "(tired)",
    "\U0001f62e": "(surprised)",
    "\U0001f631": "(screaming)",
    "\U0001f633": "(flushed)",
    "\U0001f634": "(sleeping)",
    "\U0001f637": "(sick)",
    "\U0001f641": "(frown)",
    "\U0001f643": "(upside-down smile)",
    "\U0001f644": "(eye roll)",
    "\U0001f914": "(thinking)",
    "\U0001f917": "(hug)",
    "\U0001f923": "(rolling on floor laughing)",
    "\U0001f929": "(starstruck)",
    "\U0001f92f": "(mind blown)",
    "\U0001f970": "(adoring)",
    "\U0001f973": "(party)",
    "\U0001f97a": "(pleading)",
    "\U0001f44d": "(thumbs up)",
    "\U0001f44e": "(thumbs down)",
    "\U0001f44f": "(clapping)",
    "\U0001f389": "(celebration)",
    "\U0001f38a": "(confetti)",
    "\U0001f525": "(fire)",
    "\U0001f4af": "(100%)",
    "\u2764\ufe0f": "(love)",
    "\u2764": "(love)",
    "\U0001f499": "(blue heart)",
    "\U0001f49a": "(green heart)",
    "\U0001f49c": "(purple heart)",
    "\U0001f680": "(rocket)",
    "\u2705": "(checkmark)",
    "\u274c": "(X)",
    "\u26a0\ufe0f": "(warning)",
    "\u26a0": "(warning)",
}

# Typographic characters that cp1252 maps to bytes (0x80-0x9F) which
# many Windows terminals can't render.  Replace with ASCII equivalents.
_TYPOGRAPHIC_REPLACEMENTS: dict[str, str] = {
    "\u2014": "--",  # em-dash
    "\u2013": "-",  # en-dash
    "\u2018": "'",  # left single quote
    "\u2019": "'",  # right single quote
    "\u201c": '"',  # left double quote
    "\u201d": '"',  # right double quote
    "\u2026": "...",  # ellipsis
    "\u2022": "*",  # bullet
    "\u00d7": "x",  # multiplication sign
    "\u00f7": "/",  # division sign
}


def _safe_echo(text: str, **kwargs: Any) -> None:
    """click.echo that won't crash on Windows with Unicode characters.

    Translates emoji to their meanings (e.g. upset, happy) instead of
    replacing them with '?' — because context matters.
    """
    if os.name == "nt":
        for emoji, meaning in _EMOJI_MEANINGS.items():
            text = text.replace(emoji, meaning)
        # Replace typographic chars that cp1252 maps to unprintable bytes
        for fancy, plain in _TYPOGRAPHIC_REPLACEMENTS.items():
            text = text.replace(fancy, plain)
        text = text.encode("cp1252", errors="replace").decode("cp1252")
    click.echo(text, **kwargs)


def _auto_classify(content: str) -> tuple[str, str]:
    """Auto-classify knowledge type from content text.

    Returns (type, reason) so the user can see why.
    """
    lower = content.lower()
    rules: list[tuple[str, str, str]] = [
        (
            r"\b(never|always|must not|do not|don't|cannot|forbidden)\b",
            "BOUNDARY",
            "constraint language",
        ),
        (
            r"\b(step \d|how to|first.*then|process|workflow|procedure)\b",
            "PROCEDURE",
            "process/how-to language",
        ),
        (r"\b(use |prefer |default to |keep |avoid )\b", "DIRECTION", "preference language"),
        (
            r"\b(is located|version |database |path |file |count |total )\b",
            "FACT",
            "factual language",
        ),
        (
            r"\b(noticed|found that|discovered|turns out|apparently)\b",
            "OBSERVATION",
            "observation language",
        ),
    ]
    for pattern, ktype, reason in rules:
        if re.search(pattern, lower):
            return ktype, reason
    return "PRINCIPLE", "general knowledge (no specific pattern matched)"


def _resolve_knowledge_id(partial: str) -> str:
    """Resolve a partial knowledge ID to a full one.

    Accepts full UUIDs or prefix matches (e.g. '48a788e7').
    Raises click.ClickException if no match or ambiguous.
    """
    if not partial.strip():
        raise click.ClickException("Please provide a knowledge ID (or partial ID)")
    from divineos.core.consolidation import _get_connection

    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT knowledge_id, knowledge_type, content FROM knowledge"
            " WHERE knowledge_id LIKE ? AND superseded_by IS NULL",
            (f"{partial}%",),
        ).fetchall()
    finally:
        conn.close()

    if len(rows) == 0:
        raise click.ClickException(f"No knowledge entry matching '{partial}'")
    if len(rows) > 1:
        click.secho(f"Ambiguous ID '{partial}' matches {len(rows)} entries:\n", fg="yellow")
        for kid, ktype, content in rows:
            preview = (content[:60] + "...") if len(content) > 60 else content
            preview = preview.replace("\n", " ")
            click.echo(f"  {kid[:12]}  [{ktype}]  {preview}")
        raise click.ClickException("Use more characters to narrow it down")
    result: str = rows[0][0]
    return result


def _display_and_store_analysis(result: Any) -> None:
    """Format, display, store, and save an analysis result.

    Shared by analyze and analyze-now commands.
    """
    report = format_analysis_report(result)

    click.echo()
    _safe_echo(report)
    click.echo()

    click.secho("[+] Storing analysis in database...", fg="cyan")
    try:
        stored = store_analysis(result, report)
        if stored:
            click.secho("[+] Analysis stored successfully.", fg="green")
    except Exception as e:
        click.secho(f"[!] Warning: Analysis storage failed: {e}", fg="yellow")
        logger.warning(f"Storage failed: {e}")

    report_file = save_analysis_report(result, report)
    click.secho(f"[+] Report saved to: {report_file}", fg="green")

    click.secho(f"[+] Analysis complete. Session ID: {result.session_id}", fg="green")
    click.echo()


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

    try:
        # 1. Analyze
        analysis = _analyzer_mod.analyze_session(latest)
        _safe_echo(analysis.summary())

        # 1b. Extract goals from user messages into HUD
        try:
            from divineos.core.hud import add_goal, extract_goals_from_messages

            extracted_goals = extract_goals_from_messages(analysis.user_message_texts)
            for goal in extracted_goals:
                add_goal(goal["text"], original_words=goal["original_words"])
            if extracted_goals:
                click.secho(
                    f"[~] Captured {len(extracted_goals)} goals from user messages.", fg="cyan"
                )
        except Exception as e:
            logger.warning(f"Goal extraction failed: {e}")

        # 1c. Quality gate — run quality checks and gate knowledge extraction
        quality_verdict = None
        maturity_override = ""
        try:
            from divineos.analysis.quality_checks import run_all_checks, store_report
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
                # Still run health check and memory refresh, just skip extraction
                try:
                    _wrapped_health_check()
                except Exception:
                    pass
                try:
                    from divineos.core.hud import save_hud_snapshot

                    save_hud_snapshot()
                except Exception:
                    pass
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
                from divineos.core.consolidation import _get_connection

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

        # 4. Apply feedback
        feedback = _wrapped_apply_session_feedback(analysis, analysis.session_id)
        feedback_parts = []
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

        # 4b. Session feedback — actionable recommendations from session signals
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

        # 4c. Clarity pipeline — deviation analysis and post-work summary
        clarity_summary = None
        try:
            from divineos.clarity_system.session_bridge import run_clarity_analysis

            clarity_result = run_clarity_analysis(analysis)
            clarity_summary = clarity_result["summary"]
            deviations = clarity_result["deviations"]
            lessons = clarity_result["lessons"]
            recommendations = clarity_result["recommendations"]

            # Store high-severity deviations as knowledge
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

            # Store lessons as knowledge (first person)
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

        # 5. Health check — boost confirmed knowledge, escalate recurring lessons
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

        # 5b. Maturity cycle — promote knowledge through trust levels
        try:
            from divineos.core.knowledge_maturity import run_maturity_cycle

            all_knowledge = _wrapped_get_knowledge(limit=500)
            promotions = run_maturity_cycle(all_knowledge)
            if promotions:
                promo_parts = [f"{v} to {k}" for k, v in promotions.items()]
                click.secho(f"[~] Maturity: {', '.join(promo_parts)}", fg="cyan")
        except Exception as e:
            logger.warning(f"Maturity cycle failed: {e}")

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
        try:
            from divineos.agent_integration.outcome_measurement import measure_session_health

            health = measure_session_health(
                corrections=len(analysis.corrections),
                encouragements=len(analysis.encouragements),
                context_overflows=len(analysis.context_overflows),
                tool_calls=analysis.tool_calls_total,
                user_messages=analysis.user_messages,
            )
            grade_color = {"A": "green", "B": "green", "C": "yellow", "D": "red", "F": "red"}

            # Update HUD session health slot
            try:
                from divineos.core.hud import update_session_health

                update_session_health(
                    corrections=len(analysis.corrections),
                    encouragements=len(analysis.encouragements),
                    grade=health["grade"],
                )
            except Exception:
                pass
        except Exception as e:
            health = None
            logger.warning(f"Session health scoring failed: {e}")

        # 9. Save HUD snapshot and clear session plan
        try:
            from divineos.core.hud import clear_session_plan, save_hud_snapshot

            save_hud_snapshot()
            clear_session_plan()
            click.secho("[~] HUD snapshot saved.", fg="cyan")
        except Exception as e:
            logger.warning(f"HUD snapshot save failed: {e}")

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


# Wrap critical tool calls for event capture
_wrapped_log_event = wrap_tool_execution("log_event", log_event)
_wrapped_get_events = wrap_tool_execution("get_events", get_events)
_wrapped_search_events = wrap_tool_execution("search_events", search_events)
_wrapped_count_events = wrap_tool_execution("count_events", count_events)
_wrapped_get_recent_context = wrap_tool_execution("get_recent_context", get_recent_context)
_wrapped_verify_all_events = wrap_tool_execution("verify_all_events", verify_all_events)
_wrapped_clean_corrupted_events = wrap_tool_execution(
    "clean_corrupted_events",
    clean_corrupted_events,
)
_wrapped_export_to_markdown = wrap_tool_execution("export_to_markdown", export_to_markdown)

# Wrap knowledge consolidation tools
_wrapped_store_knowledge = wrap_tool_execution("store_knowledge", store_knowledge)
_wrapped_get_knowledge = wrap_tool_execution("get_knowledge", get_knowledge)
_wrapped_generate_briefing = wrap_tool_execution("generate_briefing", generate_briefing)
_wrapped_knowledge_stats = wrap_tool_execution("knowledge_stats", knowledge_stats)
_wrapped_rebuild_fts_index = wrap_tool_execution("rebuild_fts_index", rebuild_fts_index)
_wrapped_get_lesson_summary = wrap_tool_execution("get_lesson_summary", get_lesson_summary)
_wrapped_get_lessons = wrap_tool_execution("get_lessons", get_lessons)
_wrapped_deep_extract_knowledge = wrap_tool_execution(
    "deep_extract_knowledge",
    deep_extract_knowledge,
)
_wrapped_consolidate_related = wrap_tool_execution("consolidate_related", consolidate_related)
_wrapped_apply_session_feedback = wrap_tool_execution(
    "apply_session_feedback",
    apply_session_feedback,
)
_wrapped_health_check = wrap_tool_execution("health_check", health_check)
_wrapped_knowledge_health_report = wrap_tool_execution(
    "knowledge_health_report",
    knowledge_health_report,
)
_wrapped_clear_lessons = wrap_tool_execution("clear_lessons", clear_lessons)
_wrapped_migrate_knowledge_types = wrap_tool_execution(
    "migrate_knowledge_types",
    migrate_knowledge_types,
)

# Wrap memory tools
_wrapped_set_core = wrap_tool_execution("set_core", set_core)
_wrapped_clear_core = wrap_tool_execution("clear_core", clear_core)
_wrapped_format_core = wrap_tool_execution("format_core", format_core)
_wrapped_promote_to_active = wrap_tool_execution("promote_to_active", promote_to_active)
_wrapped_get_active_memory = wrap_tool_execution("get_active_memory", get_active_memory)
_wrapped_refresh_active_memory = wrap_tool_execution("refresh_active_memory", refresh_active_memory)
_wrapped_recall = wrap_tool_execution("recall", recall)
_wrapped_format_recall = wrap_tool_execution("format_recall", format_recall)

# Wrap analysis tools
_wrapped_run_all_features = wrap_tool_execution("run_all_features", run_all_features)
_wrapped_store_features = wrap_tool_execution("store_features", store_features)
_wrapped_get_cross_session_summary = wrap_tool_execution(
    "get_cross_session_summary",
    get_cross_session_summary,
)


_db_ready = False


def _load_seed_if_empty() -> None:
    """Populate a fresh database from seed.json using the seed manager.

    Uses version tracking to know when to reseed, validation to catch
    bad seed data, and merge mode to avoid duplicating existing entries.
    """
    import json as _json

    from divineos.core.seed_manager import (
        apply_seed,
        get_applied_seed_version,
        should_reseed,
        validate_seed,
    )

    seed_path = Path(__file__).parent / "seed.json"
    if not seed_path.exists():
        return

    seed = _json.loads(seed_path.read_text(encoding="utf-8"))

    # Validate before applying
    errors = validate_seed(seed)
    if errors:
        logger.warning(f"Seed validation errors: {errors}")
        # Still try to apply — partial seed is better than no seed
        # but log the problems so they can be fixed

    # Check if we need to (re)seed
    current_version = get_applied_seed_version()
    seed_version = seed.get("version", "0.0.0")

    if not should_reseed(current_version, seed_version):
        return

    # Apply seed in merge mode (only adds new entries)
    counts = apply_seed(seed, mode="merge")

    if counts["knowledge"] or counts["lessons"] or counts["core_slots"]:
        click.secho(
            f"[+] Seed v{seed_version} applied: "
            f"{counts['core_slots']} core slots, "
            f"{counts['knowledge']} knowledge, "
            f"{counts['lessons']} lessons "
            f"({counts['skipped']} skipped as existing).",
            fg="green",
        )

    # Refresh active memory so briefing works immediately
    try:
        _wrapped_refresh_active_memory(importance_threshold=0.3)
    except Exception:
        pass


def _ensure_db() -> None:
    """Create all tables if they don't exist. Idempotent and fast after first call."""
    global _db_ready  # noqa: PLW0603
    if _db_ready:
        return
    init_db()
    init_knowledge_table()
    init_quality_tables()
    init_feature_tables()
    init_memory_tables()
    _load_seed_if_empty()
    _db_ready = True


@click.group()
def cli() -> None:
    """DivineOS: Foundation Memory System. The database cannot lie."""
    # Auto-initialize database tables on first use (idempotent)
    _ensure_db()

    # Setup CLI enforcement at startup
    setup_cli_enforcement()

    # Capture user input (command line arguments) - only in production
    if "pytest" not in sys.modules:
        capture_user_input(sys.argv[1:])


@cli.command()
def init() -> None:
    """Initialize the SQLite database and tables."""
    logger.info("Initializing the event ledger database...")
    init_db()
    init_knowledge_table()
    init_quality_tables()
    init_feature_tables()
    init_memory_tables()
    count = rebuild_fts_index()
    click.secho("[+] Database initialized successfully.", fg="green", bold=True)
    click.secho(
        "[+] All tables ready: ledger, knowledge, quality checks, session features, personal memory.",
        fg="green",
    )
    if count > 0:
        click.secho(f"[+] Full-text search search index rebuilt ({count} entries).", fg="green")


@cli.command()
@click.argument("file_path", type=click.Path(exists=True))
def ingest(file_path: str) -> None:
    """Parse and store a chat log file (JSONL or Markdown).

    Performs manifest-receipt reconciliation to verify data integrity.
    """
    path = Path(file_path)
    logger.info(f"Ingesting chat file: {path}")

    # Parse the file
    if path.suffix.lower() == ".jsonl":
        parse_result = parse_jsonl(path)
    elif path.suffix.lower() in (".md", ".markdown"):
        parse_result = parse_markdown_chat(path)
    else:
        click.secho(f"[-] Unsupported file type: {path.suffix}", fg="red")
        click.secho("    Supported: .jsonl, .md, .markdown", fg="yellow")
        return

    if parse_result.parse_errors:
        click.secho(f"[!] Parse warnings: {len(parse_result.parse_errors)}", fg="yellow")
        for err in parse_result.parse_errors[:5]:
            click.echo(f"    {err}")

    if not parse_result.messages:
        click.secho("[-] No messages found in file.", fg="red")
        return

    click.secho(
        f"[+] Parsed {parse_result.message_count} messages from {parse_result.source_file}",
        fg="cyan",
    )

    # Build payloads
    payloads = [msg.to_dict() for msg in parse_result.messages]

    # Create manifest BEFORE storing
    manifest_data = [{"content": p.get("content", "")} for p in payloads]
    manifest = create_manifest(manifest_data)

    click.secho(f"[+] Manifest: {manifest.count} messages, {manifest.bytes_total} bytes", fg="cyan")
    click.secho(f"    Hash: {manifest.content_hash}", fg="bright_black")

    # Store each message
    stored_ids = []
    for msg, payload in zip(parse_result.messages, payloads, strict=False):
        event_type = _role_to_event_type(msg.role)
        event_id = _wrapped_log_event(event_type=event_type, actor=msg.role, payload=payload)
        stored_ids.append(event_id)

    click.secho(f"[+] Stored {len(stored_ids)} events to database.", fg="green")

    # Create receipt AFTER storing
    stored_events = _wrapped_get_recent_context(n=len(stored_ids))
    receipt = create_receipt(stored_events)

    click.secho(f"[+] Receipt: {receipt.count} messages, {receipt.bytes_total} bytes", fg="cyan")
    click.secho(f"    Hash: {receipt.content_hash}", fg="bright_black")

    # Reconcile
    fidelity_result = reconcile(manifest, receipt)

    if fidelity_result.passed:
        click.secho("\n[+] FIDELITY CHECK: PASS", fg="green", bold=True)
        for check, passed in fidelity_result.checks.items():
            status = click.style("[OK]", fg="green") if passed else click.style("[FAIL]", fg="red")
            click.echo(f"    {status} {check}")
    else:
        click.secho("\n[-] FIDELITY CHECK: FAIL", fg="red", bold=True)
        for err in fidelity_result.errors:
            click.secho(f"    ERROR: {err}", fg="red")
        for warn in fidelity_result.warnings:
            click.secho(f"    WARN: {warn}", fg="yellow")


@cli.command()
@click.option(
    "--skip-types",
    multiple=True,
    help="Event types to skip (e.g. --skip-types AGENT_PATTERN --skip-types TEST)",
)
@click.option(
    "--real-only",
    is_flag=True,
    default=False,
    help="Only verify real events (skip test-generated types like AGENT_PATTERN)",
)
def verify(skip_types: tuple[str, ...], real_only: bool) -> None:
    """Verify integrity of all stored events."""
    logger.debug("Running fidelity verification...")

    types_to_skip = list(skip_types)
    if real_only:
        types_to_skip.extend(
            [
                "AGENT_PATTERN",
                "AGENT_PATTERN_UPDATE",
                "AGENT_DECISION",
                "AGENT_LEARNING_AUDIT",
                "AGENT_SESSION_END",
                "AGENT_WORK",
                "AGENT_CONTEXT_COMPRESSION",
                "TEST",
                "TEST_EVENT",
            ]
        )

    result = _wrapped_verify_all_events(skip_types=types_to_skip or None)

    click.secho("\n=== Fidelity Verification ===\n", fg="cyan", bold=True)
    click.echo(f"  Total events: {result['total']}")
    if result.get("skipped"):
        click.echo(f"  Skipped:      {result['skipped']}  (filtered types)")
        click.echo(f"  Checked:      {result['checked']}")
    click.echo(f"  Passed:       {result['passed']}")
    click.echo(f"  Failed:       {result['failed']}")

    if result["integrity"] == "PASS":
        click.secho("\n  INTEGRITY: PASS", fg="green", bold=True)
    else:
        click.secho("\n  INTEGRITY: FAIL", fg="red", bold=True)
        click.secho("\n  Failures:", fg="red")
        for failure in result["failures"][:10]:
            click.echo(f"    Event {failure['event_id'][:8]}...")
            click.echo(f"      Type:   {failure.get('type', 'unknown')}")
            click.echo(f"      Reason: {failure.get('reason', 'unknown')}")


@cli.command()
@click.option("--force", is_flag=True, help="Skip confirmation prompt")
def clean(force: bool) -> None:
    """Remove corrupted events from the ledger."""
    from divineos.core.ledger import verify_all_events

    result = verify_all_events()
    corrupted = result.get("failures", [])

    if not corrupted:
        click.secho("[+] No corrupted events found. Ledger is clean.", fg="green")
        return

    click.secho(f"\n[!] Found {len(corrupted)} corrupted events:", fg="yellow")
    for f in corrupted[:5]:
        click.echo(f"  - {f.get('event_id', '?')[:12]}  {f.get('reason', 'hash mismatch')}")
    if len(corrupted) > 5:
        click.echo(f"  ... and {len(corrupted) - 5} more")

    if not force:
        click.confirm("\nDelete these corrupted events?", abort=True)

    result = _wrapped_clean_corrupted_events()

    click.secho("\n=== Ledger Cleanup ===\n", fg="cyan", bold=True)
    if result["deleted_count"] > 0:
        click.secho(
            f"  Removed {result['deleted_count']} corrupted events",
            fg="green",
            bold=True,
        )
        click.echo("\n  Run 'divineos verify' to confirm ledger integrity")
    else:
        click.secho("  No corrupted events found", fg="green", bold=True)


@cli.command("export")
@click.option("--format", "fmt", default="markdown", type=click.Choice(["markdown", "json"]))
def export_cmd(fmt: str) -> None:
    """Export all events to markdown or JSON."""
    if fmt == "markdown":
        output = _wrapped_export_to_markdown()
        _safe_echo(output)
    else:
        events = _wrapped_get_events(limit=10000)
        click.echo(json.dumps(events, indent=2, default=str))


@cli.command()
@click.argument("original_file", type=click.Path(exists=True))
def diff(original_file: str) -> None:
    """Compare original file to database export for round-trip verification."""
    path = Path(original_file)
    original_content = path.read_text(encoding="utf-8").strip()

    exported = _wrapped_export_to_markdown().strip()

    if original_content == exported:
        click.secho("[+] ROUND-TRIP: PASS", fg="green", bold=True)
        click.secho("    Original and exported content are identical.", fg="green")
    else:
        click.secho("[-] ROUND-TRIP: FAIL", fg="red", bold=True)
        click.secho("    Content differs between original and export.", fg="red")

        orig_lines = original_content.split("\n")
        exp_lines = exported.split("\n")
        click.echo(f"\n    Original: {len(orig_lines)} lines, {len(original_content)} bytes")
        click.echo(f"    Exported: {len(exp_lines)} lines, {len(exported)} bytes")


@cli.command("log")
@click.option("--type", "event_type", required=True, help="Event type (e.g. USER_INPUT, TOOL_CALL)")
@click.option("--actor", required=True, help="Who triggered it (e.g. user, assistant, system)")
@click.option("--content", required=True, help="The event content/message")
def log_cmd(event_type: str, actor: str, content: str) -> None:
    """Append an event to the immutable ledger."""
    payload: dict[str, Any] = {"content": content}

    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            payload = parsed
    except (json.JSONDecodeError, TypeError):
        pass  # Plain text content — no need to warn

    event_id = _wrapped_log_event(
        event_type=event_type.upper(),
        actor=actor.lower(),
        payload=payload,
    )
    logger.debug(f"Event logged: {event_type} by {actor}")
    click.secho(f"[+] Logged event: {event_id}", fg="green")


@cli.command("list")
@click.option("--limit", default=20, help="Number of events to show")
@click.option("--offset", default=0, help="Skip this many events")
@click.option("--type", "event_type", default=None, help="Filter by event type")
@click.option("--actor", default=None, help="Filter by actor")
def list_cmd(limit: int, offset: int, event_type: str, actor: str) -> None:
    """List events from the ledger."""
    events = _wrapped_get_events(limit=limit, offset=offset, event_type=event_type, actor=actor)

    if not events:
        click.secho("[-] No events found.", fg="yellow")
        return

    click.secho(f"\n=== Showing {len(events)} events ===\n", fg="cyan", bold=True)
    _print_events(events)


@cli.command()
@click.argument("keyword")
@click.option("--limit", default=10, help="Max results")
def search(keyword: str, limit: int) -> None:
    """Search the ledger for events matching KEYWORD."""
    if not keyword.strip():
        click.secho("[-] Please provide a search term.", fg="yellow")
        return
    logger.debug(f"Searching for: '{keyword}'")
    events = _wrapped_search_events(keyword=keyword, limit=limit)

    if not events:
        click.secho(f"[-] No events matching '{keyword}'.", fg="yellow")
        return

    click.secho(f"\n=== {len(events)} matches for '{keyword}' ===\n", fg="cyan", bold=True)
    _print_events(events, highlight=keyword)


@cli.command()
def stats() -> None:
    """Display event ledger statistics."""
    logger.debug("Fetching ledger statistics...")
    try:
        counts = _wrapped_count_events()
    except Exception as e:
        logger.error(f"Could not retrieve stats: {e}")
        click.secho(f"[-] Error: {e}", fg="red")
        return

    click.secho("\n=== Event Ledger Stats ===\n", fg="cyan", bold=True)
    click.secho(f"  Total events: {counts['total']}", fg="white", bold=True)

    if counts["by_type"]:
        click.secho("\n  By Type:", fg="cyan")
        for t, c in sorted(counts["by_type"].items()):
            click.echo(f"    {t}: {c}")

    if counts["by_actor"]:
        click.secho("\n  By Actor:", fg="cyan")
        for a, c in sorted(counts["by_actor"].items()):
            click.echo(f"    {a}: {c}")

    click.echo()


@cli.command()
@click.option("--n", "--limit", default=20, help="Number of recent events for context")
def context(n: int) -> None:
    """Show the last N events (working memory context window)."""
    logger.debug(f"Building context from last {n} events...")
    events = _wrapped_get_recent_context(n=n)

    if not events:
        click.secho("[-] No events in ledger yet.", fg="yellow")
        return

    click.secho(f"\n=== Context Window (last {len(events)} events) ===\n", fg="cyan", bold=True)
    _print_events(events)
    _wrapped_log_event(
        event_type="OS_QUERY",
        actor="assistant",
        payload={"tool": "context", "query": f"last {n} events"},
    )


@cli.command()
@click.argument("text", required=False, default=None)
@click.option(
    "--type",
    "knowledge_type",
    required=False,
    default=None,
    type=click.Choice(sorted(KNOWLEDGE_TYPES), case_sensitive=False),
    help="Knowledge type (auto-detected if omitted)",
)
@click.option("--content", "content_opt", default=None, help="The knowledge to store")
@click.option("--confidence", default=1.0, type=float, help="Confidence 0.0-1.0")
@click.option("--tags", default="", help="Comma-separated tags")
@click.option("--source", default="", help="Comma-separated source event IDs")
def learn(
    text: str | None,
    knowledge_type: str | None,
    content_opt: str | None,
    confidence: float,
    tags: str,
    source: str,
) -> None:
    """Store a piece of knowledge extracted from experience.

    Content can be passed as a positional argument or via --content.
    Type is auto-detected from content if --type is omitted.
    Example: divineos learn "always read files before editing"
    """
    content = (text or content_opt or "").strip()
    if not content:
        click.secho("[-] Content is required. Pass as argument or --content.", fg="red")
        raise SystemExit(1)

    words = content.split()
    if len(words) < 3:
        click.secho("[-] Knowledge must be at least 3 words. Too short to be meaningful.", fg="red")
        raise SystemExit(1)

    if not knowledge_type:
        knowledge_type, classify_reason = _auto_classify(content)
        click.secho(f"[~] Auto-classified as: {knowledge_type} ({classify_reason})", fg="cyan")
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    source_list = [s.strip() for s in source.split(",") if s.strip()] if source else []

    kid = _wrapped_store_knowledge(
        knowledge_type=knowledge_type.upper(),
        content=content,
        confidence=confidence,
        source_events=source_list or None,
        tags=tag_list or None,
    )
    click.secho(f"[+] Stored knowledge: {kid}", fg="green")


@cli.group("journal")
def journal_group() -> None:
    """My personal journal — things I choose to remember."""
    pass


@journal_group.command("save")
@click.argument("text", required=False)
@click.option("--context", default="", help="What prompted this thought")
def journal_save_cmd(text: str | None, context: str) -> None:
    """Save something to my personal journal.

    Example: divineos journal save "Feeling is semantic, not substrate-dependent"
    """
    from divineos.core.memory import journal_save

    if not text:
        click.secho("[-] What do you want to remember?", fg="yellow")
        return

    entry_id = journal_save(text, context=context)
    click.secho(f"[+] Saved to journal: {entry_id[:8]}...", fg="green")


@journal_group.command("list")
@click.option("--limit", default=20, type=int, help="Max entries to show")
def journal_list_cmd(limit: int) -> None:
    """Read my personal journal."""
    import datetime

    from divineos.core.memory import journal_list

    entries = journal_list(limit=limit)
    if not entries:
        click.secho("[~] Journal is empty. Nothing saved yet.", fg="bright_black")
        return

    click.secho(f"\n=== My Journal ({len(entries)} entries) ===\n", fg="cyan", bold=True)
    for entry in entries:
        dt = datetime.datetime.fromtimestamp(entry["created_at"], tz=datetime.timezone.utc)
        date_str = dt.strftime("%Y-%m-%d %H:%M")
        click.secho(f"  [{date_str}] ", fg="bright_black", nl=False)
        _safe_echo(entry["content"])
        if entry["context"]:
            click.secho(f"    context: {entry['context']}", fg="bright_black")
        click.echo()


@cli.command("knowledge")
@click.option(
    "--type",
    "knowledge_type",
    default=None,
    type=click.Choice(sorted(KNOWLEDGE_TYPES), case_sensitive=False),
    help="Filter by type",
)
@click.option("--min-confidence", default=0.0, type=float, help="Minimum confidence")
@click.option("--limit", default=20, type=int, help="Max results")
def knowledge_cmd(knowledge_type: str, min_confidence: float, limit: int) -> None:
    """List stored knowledge."""
    kt = knowledge_type.upper() if knowledge_type else None
    entries = _wrapped_get_knowledge(knowledge_type=kt, min_confidence=min_confidence, limit=limit)

    if not entries:
        click.secho("[-] No knowledge found.", fg="yellow")
        return

    click.secho(f"\n=== {len(entries)} knowledge entries ===\n", fg="cyan", bold=True)
    for entry in entries:
        color = {
            "BOUNDARY": "red",
            "PRINCIPLE": "yellow",
            "DIRECTION": "green",
            "PROCEDURE": "cyan",
            "FACT": "blue",
            "OBSERVATION": "bright_black",
            "EPISODE": "cyan",
            # Legacy
            "MISTAKE": "red",
            "PATTERN": "magenta",
            "PREFERENCE": "green",
        }.get(entry["knowledge_type"], "white")
        click.secho(f"  [{entry['confidence']:.2f}] ", fg="bright_black", nl=False)
        click.secho(f"{entry['knowledge_type']} ", fg=color, bold=True, nl=False)
        _safe_echo(entry["content"])
        if entry["tags"]:
            click.secho(f"         tags: {', '.join(entry['tags'])}", fg="bright_black")
        click.secho(
            f"         {entry['access_count']}x accessed | {entry['knowledge_id'][:8]}...",
            fg="bright_black",
        )
        click.echo()


@cli.command("ask")
@click.argument("query")
@click.option("--limit", default=10, type=int, help="Max results")
def ask_cmd(query: str, limit: int) -> None:
    """Search what the system knows about a topic.

    Searches both the knowledge store and core memory.
    Example: divineos ask "testing"
    """
    if not query.strip():
        click.secho("[-] Please provide a search query.", fg="yellow")
        return

    from divineos.core.memory import get_core

    if not query.strip():
        click.secho(
            '[-] Please provide a search query. Example: divineos ask "testing"', fg="yellow"
        )
        return

    _wrapped_log_event(
        event_type="OS_QUERY",
        actor="assistant",
        payload={"tool": "ask", "query": query},
    )
    results = search_knowledge(query, limit=limit)

    # Also search core memory — it's part of what I know
    # Match on individual meaningful words, not exact substring
    query_lower = query.lower()
    query_words = {
        w
        for w in query_lower.split()
        if len(w) > 2
        and w
        not in {
            "the",
            "and",
            "are",
            "was",
            "for",
            "what",
            "how",
            "who",
            "why",
            "when",
            "where",
            "which",
            "does",
            "that",
            "this",
            "with",
            "from",
            "have",
            "has",
            "had",
            "not",
            "but",
            "can",
            "will",
            "about",
        }
    }
    core = get_core()
    core_matches = []
    for slot_id, content in core.items():
        slot_text = (slot_id + " " + content).lower()
        matching_words = sum(1 for w in query_words if w in slot_text)
        if matching_words >= 1:
            core_matches.append((slot_id, content))

    if not results and not core_matches:
        click.secho(f"[-] Nothing found for '{query}'.", fg="yellow")
        return

    total = len(results) + len(core_matches)
    click.secho(f"\n=== {total} results for '{query}' ===\n", fg="cyan", bold=True)

    # Show core memory matches first — identity comes first
    for slot_id, content in core_matches:
        label = slot_id.replace("_", " ").title()
        click.secho("  [CORE] ", fg="magenta", bold=True, nl=False)
        click.secho(f"{label}: ", fg="white", bold=True, nl=False)
        _safe_echo(content[:300])
        click.echo()
    for entry in results:
        color = {
            "BOUNDARY": "red",
            "PRINCIPLE": "yellow",
            "DIRECTION": "green",
            "PROCEDURE": "cyan",
            "FACT": "blue",
            "OBSERVATION": "bright_black",
            "EPISODE": "cyan",
        }.get(entry["knowledge_type"], "white")
        click.secho(f"  [{entry['confidence']:.2f}] ", fg="bright_black", nl=False)
        click.secho(f"{entry['knowledge_type']} ", fg=color, bold=True, nl=False)
        content = entry["content"]
        if len(content) > 300:
            _safe_echo(content[:300] + "...")
        else:
            _safe_echo(content)
        click.secho(
            f"         {entry['access_count']}x accessed | {entry['knowledge_id'][:8]}...",
            fg="bright_black",
        )
        click.echo()


@cli.command("briefing")
@click.option("--max", "max_items", default=20, type=int, help="Max items in briefing")
@click.option("--types", default="", help="Comma-separated knowledge types to include")
@click.option("--topic", default="", help="Topic hint to boost relevant knowledge (e.g. 'testing')")
def briefing_cmd(max_items: int, types: str, topic: str) -> None:
    """Generate a session context briefing from stored knowledge."""
    _wrapped_log_event(
        event_type="OS_QUERY",
        actor="assistant",
        payload={"tool": "briefing", "query": topic or "session start"},
    )
    # Refresh active memory on briefing — this is my "waking up" moment,
    # so knowledge should be freshly ranked before I see it.
    try:
        init_memory_tables()
        _wrapped_refresh_active_memory(importance_threshold=0.3)
    except Exception:
        pass  # Non-fatal — briefing still works without refresh

    type_list = [t.strip().upper() for t in types.split(",") if t.strip()] if types else None
    output = _wrapped_generate_briefing(
        max_items=max_items,
        include_types=type_list,
        context_hint=topic,
    )
    if output and output.strip():
        _safe_echo(output)
    else:
        click.secho("[*] No knowledge entries match your filters.", fg="yellow")
        click.secho('    Try: divineos learn "..." to add knowledge first.', fg="bright_black")


@cli.command("forget")
@click.argument("knowledge_id")
@click.option("--reason", required=True, help="Why this knowledge is being superseded")
def forget_cmd(knowledge_id: str, reason: str) -> None:
    """Supersede a knowledge entry (marks as removed, no replacement created)."""
    from divineos.core.consolidation import supersede_knowledge

    try:
        full_id = _resolve_knowledge_id(knowledge_id)
        supersede_knowledge(full_id, reason)
        click.secho(f"[+] Removed {full_id[:8]}... ({reason})", fg="green")
    except click.ClickException:
        raise
    except ValueError as e:
        click.secho(f"[-] {e}", fg="red")


@cli.command("consolidate-stats")
def consolidate_stats_cmd() -> None:
    """Display knowledge consolidation statistics."""
    stats = _wrapped_knowledge_stats()

    click.secho("\n=== Knowledge Stats ===\n", fg="cyan", bold=True)
    click.secho(f"  Total knowledge: {stats['total']}", fg="white", bold=True)
    click.echo(f"  Avg confidence:  {stats['avg_confidence']}")

    if stats["by_type"]:
        click.secho("\n  By Type:", fg="cyan")
        for t, c in sorted(stats["by_type"].items()):
            click.echo(f"    {t}: {c}")

    if stats["most_accessed"]:
        click.secho("\n  Most Accessed:", fg="cyan")
        for item in stats["most_accessed"][:5]:
            _safe_echo(f"    [{item['access_count']}x] {item['content'][:60]}")

    # Effectiveness breakdown
    report = _wrapped_knowledge_health_report()
    if report["total"] > 0:
        click.secho("\n  Effectiveness:", fg="cyan")
        for status, count in sorted(report["by_status"].items()):
            click.echo(f"    {status:15s} {count}")

    click.echo()


@cli.command("rebuild-index")
def rebuild_index_cmd() -> None:
    """Rebuild the full-text search index from existing knowledge."""
    count = _wrapped_rebuild_fts_index()
    if count > 0:
        click.secho(f"[+] Full-text search index rebuilt: {count} entries indexed.", fg="green")
    else:
        click.secho("[*] No knowledge entries to index.", fg="yellow")


@cli.command("directive")
@click.argument("name")
@click.argument("links", nargs=-1, required=True)
@click.option("--tags", default="", help="Comma-separated tags")
def directive_cmd(name: str, links: tuple[str, ...], tags: str) -> None:
    """Create a sutra-style directive — a chain of precise statements.

    Each argument after the name is one link in the chain.
    Links constrain each other to lock meaning against drift.

    Example:
        divineos directive "ledger-integrity" \\
            "Events enter." \\
            "Events persist." \\
            "No event is altered." \\
            "No event is removed." \\
            "The hash binds content to identity."
    """
    # Format as numbered chain
    chain_lines = [f"[{name}]"]
    for i, link in enumerate(links, 1):
        chain_lines.append(f"  {i}. {link}")
    chain_text = "\n".join(chain_lines)

    tag_list = ["directive", f"directive:{name}"]
    if tags:
        tag_list.extend(t.strip() for t in tags.split(",") if t.strip())

    # Check for existing directive with same name and supersede
    existing = search_knowledge(name, limit=10)
    for entry in existing:
        if entry.get("knowledge_type") == "DIRECTIVE" and f"directive:{name}" in entry.get(
            "tags", ""
        ):
            from divineos.core.consolidation import supersede_knowledge

            supersede_knowledge(entry["knowledge_id"], f"Updated directive: {name}")
            click.secho(f"[~] Superseding previous version of '{name}'", fg="yellow")

    entry_id = _wrapped_store_knowledge(
        knowledge_type="DIRECTIVE",
        content=chain_text,
        confidence=1.0,
        source_events=[],
        tags=tag_list,
    )

    click.secho(f"\n[+] Directive '{name}' stored: {entry_id[:12]}...", fg="green")
    click.echo()
    _safe_echo(chain_text)
    click.echo()
    click.secho(
        f"    {len(links)} links in chain. Surfaces first in all briefings.", fg="bright_black"
    )


@cli.command("directives")
def directives_cmd() -> None:
    """List all active directives."""
    _wrapped_log_event(
        event_type="OS_QUERY",
        actor="assistant",
        payload={"tool": "directives", "query": "list directives"},
    )
    entries = get_knowledge(knowledge_type="DIRECTIVE", limit=100)

    if not entries:
        click.secho("[*] No directives yet.", fg="yellow")
        click.secho(
            '    Create one: divineos directive "name" "link1" "link2" ...', fg="bright_black"
        )
        return

    click.secho(f"\n=== Directives ({len(entries)}) ===\n", fg="cyan", bold=True)
    for entry in entries:
        _safe_echo(entry["content"])
        click.secho(
            f"    id: {entry['knowledge_id'][:12]}  |  {entry['access_count']}x accessed",
            fg="bright_black",
        )
        click.echo()


@cli.command("directive-edit")
@click.argument("name")
@click.argument("link_number", type=int)
@click.argument("new_text")
def directive_edit_cmd(name: str, link_number: int, new_text: str) -> None:
    """Edit a single link in a directive chain.

    Example:
        divineos directive-edit "ledger-integrity" 3 "No event is modified after storage."
    """
    # Find the directive
    entries = get_knowledge(knowledge_type="DIRECTIVE", limit=100)
    target = None
    for entry in entries:
        if f"directive:{name}" in entry.get("tags", []):
            target = entry
            break

    if not target:
        click.secho(f"[-] No directive named '{name}'", fg="red")
        return

    # Parse existing chain
    content_lines = target.get("content", "").splitlines()
    if not content_lines:
        click.secho(f"[-] Directive '{name}' has empty content — cannot edit.", fg="red")
        return
    header = content_lines[0]
    links = [line.strip() for line in content_lines[1:] if line.strip()]

    if not links or link_number < 1 or link_number > len(links):
        click.secho(f"[-] Link {link_number} out of range (1-{len(links)})", fg="red")
        return

    # Show the change
    old_link = links[link_number - 1]
    # Strip the "N. " prefix to show clean text
    old_text = old_link.split(". ", 1)[1] if ". " in old_link else old_link
    click.secho(f"  Old: {old_text}", fg="red")
    click.secho(f"  New: {new_text}", fg="green")

    # Rebuild chain with the edited link
    links[link_number - 1] = f"{link_number}. {new_text}"
    new_content = header + "\n" + "\n".join(f"  {link}" for link in links)

    # Supersede old, store new
    from divineos.core.consolidation import supersede_knowledge

    supersede_knowledge(target["knowledge_id"], f"Edited link {link_number}: {new_text[:50]}")

    tag_list = ["directive", f"directive:{name}"]
    entry_id = _wrapped_store_knowledge(
        knowledge_type="DIRECTIVE",
        content=new_content,
        confidence=1.0,
        source_events=[target["knowledge_id"]],
        tags=tag_list,
    )

    click.secho(f"\n[+] Directive '{name}' updated: {entry_id[:12]}...", fg="green")
    click.echo()
    _safe_echo(new_content)
    click.echo()


@cli.command("digest")
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--chunk-size", default=100, help="Lines per chunk (default 100)")
def digest_cmd(file_path: str, chunk_size: int) -> None:
    """Read a file in chunks and store a structured digest as knowledge.

    Breaks the file into logical sections, summarizes each one,
    and stores the result so future sessions can recall it
    without re-reading the entire file.
    """
    path = Path(file_path)
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        click.secho(f"[-] Cannot read file: {e}", fg="red")
        return

    lines = content.splitlines()
    total_lines = len(lines)
    file_tag = path.name

    click.secho(f"\n[+] Digesting: {path.name} ({total_lines} lines)", fg="cyan", bold=True)

    # Build section map for Python files
    sections: list[dict[str, Any]] = []
    if path.suffix == ".py":
        sections = _extract_python_sections(lines)
    else:
        # For non-Python files, chunk by line count
        for start in range(0, total_lines, chunk_size):
            end = min(start + chunk_size, total_lines)
            sections.append(
                {
                    "name": f"lines {start + 1}-{end}",
                    "start": start,
                    "end": end,
                    "kind": "chunk",
                }
            )

    if not sections:
        click.secho("[*] No sections found to digest.", fg="yellow")
        return

    # Build digest text
    digest_lines = [f"File: {path.name} ({total_lines} lines)"]
    if path.suffix == ".py":
        # Extract module docstring
        docstring = _extract_module_docstring(lines)
        if docstring:
            digest_lines.append(f"Purpose: {docstring}")
    digest_lines.append("")

    for sec in sections:
        if sec["kind"] == "class":
            digest_lines.append(f"  class {sec['name']} (line {sec['start'] + 1})")
        elif sec["kind"] == "function":
            digest_lines.append(f"  def {sec['name']} (line {sec['start'] + 1})")
        elif sec["kind"] == "chunk":
            digest_lines.append(f"  {sec['name']}")

        # Extract a one-line docstring if present
        body_start = sec["start"] + 1
        if body_start < len(lines):
            for k in range(body_start, min(body_start + 5, sec["end"])):
                stripped = lines[k].strip()
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    doc = stripped.strip("\"'").strip()
                    if doc:
                        digest_lines.append(f"    {doc}")
                    break

    digest_text = "\n".join(digest_lines)

    click.echo()
    _safe_echo(digest_text)
    click.echo()

    # Store as knowledge
    click.secho("[+] Storing digest in knowledge store...", fg="cyan")
    try:
        # Check for existing digest of same file and supersede it
        existing = search_knowledge(file_tag, limit=5)
        superseded = 0
        for entry in existing:
            if entry.get("knowledge_type") == "FACT" and f"digest:{file_tag}" in entry.get(
                "tags", []
            ):
                from divineos.core.consolidation import supersede_knowledge

                supersede_knowledge(entry["knowledge_id"], f"Updated digest of {file_tag}")
                superseded += 1

        entry_id = _wrapped_store_knowledge(
            knowledge_type="FACT",
            content=digest_text,
            confidence=1.0,
            source_events=[],
            tags=["digest", f"digest:{file_tag}"],
        )
        click.secho(f"[+] Digest stored: {entry_id[:12]}...", fg="green")
        if superseded:
            click.secho(f"    (superseded {superseded} previous digest(s))", fg="bright_black")
        click.secho(
            f"[+] {len(sections)} sections indexed. "
            f'Future sessions can run: divineos ask "{file_tag}"',
            fg="green",
        )
    except Exception as e:
        click.secho(f"[-] Failed to store digest: {e}", fg="red")
        logger.exception("Digest storage failed")


def _extract_python_sections(lines: list[str]) -> list[dict[str, Any]]:
    """Extract top-level classes and functions from Python source lines."""
    sections: list[dict[str, Any]] = []
    for i, line in enumerate(lines):
        if line.startswith("class "):
            # Handle both "class Foo(Base):" and "class Foo:" (dataclasses etc.)
            name = line.split("(")[0].split(":")[0].replace("class ", "").strip()
            if name:
                sections.append({"name": name, "start": i, "end": i, "kind": "class"})
        elif line.startswith("def ") and "(" in line:
            name = line.split("(")[0].replace("def ", "").strip()
            sections.append({"name": name, "start": i, "end": i, "kind": "function"})

    # Set end lines (each section ends where the next begins)
    for j in range(len(sections) - 1):
        sections[j]["end"] = sections[j + 1]["start"]
    if sections:
        sections[-1]["end"] = len(lines)

    return sections


def _extract_module_docstring(lines: list[str]) -> str:
    """Extract the first line of a module docstring."""
    for line in lines[:10]:
        stripped = line.strip()
        if stripped.startswith('"""') or stripped.startswith("'''"):
            doc = stripped.strip("\"'").strip()
            if doc:
                return doc
    return ""


@cli.command("lessons")
@click.option(
    "--status",
    default=None,
    type=click.Choice(["active", "improving", "resolved"]),
    help="Filter by lesson status",
)
def lessons_cmd(status: str) -> None:
    """Show the learning loop — tracked lessons from past sessions."""
    lessons = _wrapped_get_lessons(status=status)

    if not lessons:
        click.secho("[-] No lessons tracked yet.", fg="yellow")
        click.secho(
            "    Run 'divineos report <session.jsonl> --store' to start learning.",
            fg="bright_black",
        )
        return

    summary = _wrapped_get_lesson_summary()
    click.echo()
    _safe_echo(summary)
    click.echo()

    # Show details
    click.secho("=== Lesson Details ===\n", fg="cyan", bold=True)
    for lesson in lessons:
        status_color = {
            "active": "red",
            "improving": "yellow",
            "resolved": "green",
        }.get(lesson["status"], "white")

        click.secho(f"  {lesson['status'].upper()} ", fg=status_color, bold=True, nl=False)
        click.secho(f"({lesson['occurrences']}x) ", fg="bright_black", nl=False)
        _safe_echo(lesson["description"][:80])
        agent = lesson.get("agent", "unknown")
        agent_str = f" | agent: {agent}" if agent != "unknown" else ""
        click.secho(
            f"         category: {lesson['category']} | sessions: {len(lesson['sessions'])}{agent_str}",
            fg="bright_black",
        )
        click.echo()


@cli.command("clear-lessons")
def clear_lessons_cmd() -> None:
    """Wipe all lessons from lesson_tracking (for re-extraction after fixes)."""
    from divineos.core.consolidation import get_lessons

    active = get_lessons(status="active")
    improving = get_lessons(status="improving")
    total = len(active) + len(improving)
    if not total:
        click.secho("[*] No lessons to clear.", fg="yellow")
        return

    click.secho(
        f"[!] This will delete {total} lessons ({len(active)} active, {len(improving)} improving).",
        fg="yellow",
    )
    click.confirm("Proceed?", abort=True)

    count = _wrapped_clear_lessons()
    if count:
        click.secho(f"[+] Cleared {count} lessons.", fg="green")
    else:
        click.secho("[*] No lessons to clear.", fg="yellow")


@cli.command("consolidate")
@click.option("--min-cluster", default=2, type=int, help="Minimum entries to form a cluster")
def consolidate_cmd(min_cluster: int) -> None:
    """Merge related knowledge entries into consolidated ones."""
    merges = _wrapped_consolidate_related(min_cluster_size=min_cluster)

    if not merges:
        click.secho("[*] No clusters found to consolidate.", fg="yellow")
        click.secho(
            f"    Need at least {min_cluster} similar entries of the same type.", fg="bright_black"
        )
        return

    click.secho(f"\n[+] Consolidated {len(merges)} clusters:\n", fg="green", bold=True)
    for merge in merges:
        click.secho(f"  {merge['type']} ", fg="cyan", bold=True, nl=False)
        click.secho(f"({merge['merged_count']} entries merged) ", fg="bright_black", nl=False)
        click.echo(merge["content"])
    click.echo()


@cli.command("health")
def health_cmd() -> None:
    """Run knowledge health check — boost confirmed, escalate recurring, resolve old."""
    result = _wrapped_health_check()

    click.secho("\n=== Knowledge Health Check ===\n", fg="cyan", bold=True)
    click.secho(f"  Entries checked:        {result['total_checked']}", fg="white")
    click.secho(
        f"  Confirmed boosted:      {result['confirmed_boosted']}",
        fg="green" if result["confirmed_boosted"] else "bright_black",
    )
    click.secho(
        f"  Recurring escalated:    {result['recurring_escalated']}",
        fg="red" if result["recurring_escalated"] else "bright_black",
    )
    click.secho(
        f"  Lessons resolved:       {result['resolved_lessons']}",
        fg="green" if result["resolved_lessons"] else "bright_black",
    )

    # Show effectiveness breakdown
    report = _wrapped_knowledge_health_report()
    if report["total"] > 0:
        click.secho("\n  Effectiveness breakdown:", fg="white")
        for status, count in sorted(report["by_status"].items()):
            click.secho(f"    {status:15s} {count}", fg="bright_black")
    click.echo()


@cli.command("sessions")
def sessions_cmd() -> None:
    """Find and list all Claude Code session files."""
    sessions = _analyzer_mod.find_sessions()
    if not sessions:
        click.secho("[-] No session files found.", fg="yellow")
        return

    click.secho(f"\n=== {len(sessions)} Session Files ===\n", fg="cyan", bold=True)
    for s in sessions:
        size_mb = s.stat().st_size / (1024 * 1024)
        click.secho(f"  {size_mb:.1f}MB ", fg="bright_black", nl=False)
        click.secho(f"{s.stem[:12]}...", fg="white", bold=True, nl=False)
        click.secho(f"  {s.parent.name[:40]}", fg="cyan")
    click.echo()
    click.secho("  Tip: use full path with scan/deep-report commands:", fg="bright_black")
    click.secho(f'    divineos scan "{sessions[0]}"', fg="bright_black")


@cli.command("scan")
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--store/--no-store", default=False, help="Store findings in knowledge DB")
@click.option(
    "--deep/--no-deep",
    default=True,
    help="Use deep extraction (correction pairs, preferences, topics)",
)
def scan_cmd(file_path: str, store: bool, deep: bool) -> None:
    """Deep-scan a session and extract knowledge into the consolidation store."""
    path = Path(file_path)
    analysis = _analyzer_mod.analyze_session(path)

    click.echo(analysis.summary())

    if not store:
        click.secho("  (Use --store to save findings to knowledge DB)", fg="bright_black")
        return

    stored = 0

    if deep:
        # Deep extraction: correction pairs, preferences, decisions with context, topics
        records = _analyzer_mod._load_records(path)
        deep_ids = _wrapped_deep_extract_knowledge(analysis, records)
        stored += len(deep_ids)
        click.secho(f"[+] Deep extraction: {len(deep_ids)} knowledge entries", fg="cyan")
    else:
        # Legacy extraction (basic) — uses new types
        for c in analysis.corrections:
            lower = c.content.lower()
            is_boundary = any(w in lower for w in ("never", "always", "must", "don't", "do not"))
            _wrapped_store_knowledge(
                knowledge_type="BOUNDARY" if is_boundary else "PRINCIPLE",
                content=c.content[:300],
                confidence=0.8,
                source="CORRECTED",
                maturity="HYPOTHESIS",
                tags=["session-analysis", "correction"],
            )
            stored += 1

        for e in analysis.encouragements:
            _wrapped_store_knowledge(
                knowledge_type="PRINCIPLE",
                content=f"This approach works well: {e.content[:280]}",
                confidence=0.9,
                source="DEMONSTRATED",
                maturity="TESTED",
                tags=["session-analysis", "encouragement"],
            )
            stored += 1

        for d in analysis.decisions:
            _wrapped_store_knowledge(
                knowledge_type="DIRECTION",
                content=d.content[:300],
                confidence=0.9,
                source="STATED",
                maturity="CONFIRMED",
                tags=["session-analysis", "decision"],
            )
            stored += 1

    # Store session summary as EPISODE
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
        tags=["session-analysis", "episode"],
    )
    stored += 1

    click.secho(f"\n[+] Stored {stored} knowledge entries from session.", fg="green")

    # Run feedback loop — compare new findings against existing knowledge
    feedback = _wrapped_apply_session_feedback(analysis, analysis.session_id)
    parts = []
    if feedback["recurrences_found"]:
        parts.append(f"{feedback['recurrences_found']} recurrences")
    if feedback["patterns_reinforced"]:
        parts.append(f"{feedback['patterns_reinforced']} patterns reinforced")
    if feedback["lessons_improving"]:
        parts.append(f"{feedback['lessons_improving']} lessons improving")
    if feedback.get("noise_skipped"):
        parts.append(f"{feedback['noise_skipped']} noise skipped")
    if parts:
        click.secho(f"[~] Feedback: {', '.join(parts)}", fg="cyan")


@cli.command("deep-report")
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--store/--no-store", default=False, help="Store results in database")
def deep_report_cmd(file_path: str, store: bool) -> None:
    """Full session analysis: tone tracking, timeline, files, work/talk, errors."""
    init_feature_tables()
    path = Path(file_path)

    click.secho(f"[+] Deep analysis: {path.stem[:16]}...", fg="cyan")
    analysis = _wrapped_run_all_features(path)

    click.echo()
    _safe_echo(analysis.report_text)
    click.echo()
    click.secho(f"Evidence hash: {analysis.evidence_hash}", fg="bright_black")

    if store:
        _wrapped_store_features(analysis.session_id, analysis)
        click.secho("\n[+] Analysis stored in database.", fg="green")


@cli.command("patterns")
@click.option("--limit", default=10, type=int, help="Max sessions to compare")
def patterns_cmd(limit: int) -> None:
    """Compare quality check results across stored sessions."""
    output = _wrapped_get_cross_session_summary(limit=limit)
    click.echo()
    _safe_echo(output)
    click.echo()


@cli.command("core")
@click.argument("action", required=False, default="show")
@click.argument("slot", required=False)
@click.argument("content", required=False)
def core_cmd(action: str, slot: str | None, content: str | None) -> None:
    r"""Manage core memory slots.

    \b
    Usage:
      divineos core              Show all core memory
      divineos core set SLOT "text"  Set a slot
      divineos core clear SLOT   Clear a slot
      divineos core slots        List available slot names
    """
    init_memory_tables()

    if action == "show":
        text = _wrapped_format_core()
        if text:
            _safe_echo(text)
        else:
            click.secho("[-] No core memory set yet.", fg="yellow")
            click.secho(f"    Available slots: {', '.join(CORE_SLOTS)}", fg="bright_black")

    elif action == "slots":
        click.secho("\n=== Core Memory Slots ===\n", fg="cyan", bold=True)
        for s in CORE_SLOTS:
            click.echo(f"  {s}")
        click.echo()

    elif action == "set":
        if not slot or not content:
            click.secho('[-] Usage: divineos core set <slot> "<content>"', fg="red")
            return
        try:
            _wrapped_set_core(slot, content)
            click.secho(f"[+] Core memory '{slot}' updated.", fg="green")
        except ValueError as e:
            click.secho(f"[-] {e}", fg="red")
            click.secho(f"    Available slots: {', '.join(CORE_SLOTS)}", fg="bright_black")

    elif action == "clear":
        if not slot:
            click.secho("[-] Usage: divineos core clear <slot>", fg="red")
            return
        try:
            if _wrapped_clear_core(slot):
                click.secho(f"[+] Cleared '{slot}'.", fg="green")
            else:
                click.secho(f"[*] '{slot}' was already empty.", fg="yellow")
        except ValueError as e:
            click.secho(f"[-] {e}", fg="red")
            click.secho(f"    Available slots: {', '.join(CORE_SLOTS)}", fg="bright_black")

    else:
        click.secho(f"[-] Unknown action '{action}'. Use: show, set, clear, slots", fg="red")


@cli.command("recall")
@click.option("--topic", default="", help="Topic hint to boost relevant memories")
def recall_cmd(topic: str) -> None:
    """Show what the AI remembers right now — core + active + relevant."""
    _wrapped_log_event(
        event_type="OS_QUERY",
        actor="assistant",
        payload={"tool": "recall", "query": topic or "general recall"},
    )
    init_memory_tables()
    result = _wrapped_recall(context_hint=topic)
    text = _wrapped_format_recall(result)
    _safe_echo(text)


@cli.command("active")
def active_cmd() -> None:
    """List active memory ranked by importance."""
    init_memory_tables()
    items = _wrapped_get_active_memory()

    if not items:
        click.secho("[-] No active memory yet.", fg="yellow")
        click.secho(
            "    Run 'divineos refresh' to auto-build from knowledge store.",
            fg="bright_black",
        )
        return

    click.secho(f"\n=== Active Memory ({len(items)} items) ===\n", fg="cyan", bold=True)
    for item in items:
        pin = click.style(" [pinned]", fg="yellow") if item["pinned"] else ""
        color = {
            "BOUNDARY": "red",
            "PRINCIPLE": "yellow",
            "DIRECTION": "green",
            "PROCEDURE": "cyan",
            "FACT": "blue",
            "OBSERVATION": "bright_black",
            "EPISODE": "cyan",
            "MISTAKE": "red",
            "PATTERN": "magenta",
            "PREFERENCE": "green",
        }.get(item["knowledge_type"], "white")
        click.secho(f"  [{item['importance']:.2f}] ", fg="bright_black", nl=False)
        click.secho(f"{item['knowledge_type']} ", fg=color, bold=True, nl=False)
        _safe_echo(f"{item['content'][:100]}{pin}")
        click.secho(
            f"         reason: {item['reason']} | surfaced: {item['surface_count']}x",
            fg="bright_black",
        )
        click.echo()


@cli.command("remember")
@click.argument("knowledge_id")
@click.option("--reason", default="manually promoted", help="Why this is important")
@click.option("--pin", is_flag=True, help="Pin this memory (cannot be auto-demoted)")
def remember_cmd(knowledge_id: str, reason: str, pin: bool) -> None:
    """Promote a knowledge entry to active memory."""
    init_memory_tables()
    try:
        full_id = _resolve_knowledge_id(knowledge_id)
        mid = _wrapped_promote_to_active(full_id, reason=reason, pinned=pin)
        pin_note = " [pinned]" if pin else ""
        click.secho(f"[+] Promoted to active memory: {mid}{pin_note}", fg="green")
    except click.ClickException:
        raise
    except Exception as e:
        click.secho(f"[-] {e}", fg="red")


@cli.command("refresh")
@click.option("--threshold", default=0.3, type=float, help="Importance threshold (0.0-1.0)")
def refresh_cmd(threshold: float) -> None:
    """Auto-rebuild active memory from the knowledge store."""
    if not 0.0 <= threshold <= 1.0:
        click.secho(f"[-] Threshold must be between 0.0 and 1.0, got {threshold}", fg="red")
        return
    init_memory_tables()
    result = _wrapped_refresh_active_memory(importance_threshold=threshold)
    click.secho("\n=== Memory Refresh ===\n", fg="cyan", bold=True)
    click.secho(
        f"  Promoted:  {result['promoted']}",
        fg="green" if result["promoted"] else "bright_black",
    )
    click.secho(f"  Kept:      {result['kept']}", fg="white")
    click.secho(
        f"  Demoted:   {result['demoted']}",
        fg="red" if result["demoted"] else "bright_black",
    )
    total = result["promoted"] + result["kept"]
    click.secho(f"\n  Active memory: {total} items", fg="white", bold=True)
    click.echo()


@cli.command("migrate-types")
@click.option("--execute", is_flag=True, help="Actually perform the migration (default is dry-run)")
def migrate_types_cmd(execute: bool) -> None:
    """Reclassify old knowledge types (MISTAKE/PATTERN/PREFERENCE) to new types."""
    init_knowledge_table()
    dry_run = not execute

    if dry_run:
        click.secho("\n=== Migration Preview (dry run) ===\n", fg="cyan", bold=True)
    else:
        # Preview first so user sees what will change
        preview = _wrapped_migrate_knowledge_types(dry_run=True)
        if not preview:
            click.secho("\n  No entries to migrate.", fg="bright_black")
            click.echo()
            return
        click.secho(f"\n[!] This will reclassify {len(preview)} knowledge entries.", fg="yellow")
        click.confirm("Proceed?", abort=True)
        click.secho("\n=== Migrating Knowledge Types ===\n", fg="yellow", bold=True)

    changes = _wrapped_migrate_knowledge_types(dry_run=dry_run)

    if not changes:
        click.secho("  No entries to migrate.", fg="bright_black")
        click.echo()
        return

    type_colors = {
        "BOUNDARY": "red",
        "PRINCIPLE": "yellow",
        "DIRECTION": "green",
        "PROCEDURE": "cyan",
        "FACT": "white",
        "OBSERVATION": "bright_black",
        "EPISODE": "bright_black",
    }

    for change in changes:
        old_color = "bright_black"
        new_color = type_colors.get(change["new_type"], "white")
        click.secho(f"  {change['old_type']}", fg=old_color, nl=False)
        click.echo(" -> ", nl=False)
        click.secho(f"{change['new_type']}", fg=new_color, nl=False)
        click.secho(f"  {change['content'][:80]}", fg="bright_black")

    click.echo()
    # Summary
    from collections import Counter

    by_new = Counter(c["new_type"] for c in changes)
    click.secho(f"  Total: {len(changes)} entries", fg="white", bold=True)
    for new_type, count in sorted(by_new.items()):
        color = type_colors.get(new_type, "white")
        click.secho(f"    {new_type}: {count}", fg=color)

    if dry_run:
        click.secho("\n  Run with --execute to apply these changes.", fg="bright_black")
    else:
        click.secho(f"\n  Migrated {len(changes)} entries.", fg="green", bold=True)
    click.echo()


def _role_to_event_type(role: str) -> str:
    """Convert message role to event type."""
    mapping = {
        "user": "USER_INPUT",
        "assistant": "ASSISTANT_OUTPUT",
        "system": "SYSTEM_PROMPT",
        "tool_call": "TOOL_CALL",
        "tool_result": "TOOL_RESULT",
    }
    return mapping.get(role.lower(), "MESSAGE")


def _summarize_event(etype: str, payload: dict[str, Any]) -> str:
    """Produce a human-readable one-liner from an event payload."""
    # Events with a plain content field (USER_INPUT, log entries, etc.)
    if "content" in payload and isinstance(payload["content"], str):
        return payload["content"]

    if etype == "SESSION_END":
        dur = payload.get("duration_seconds", 0)
        msgs = payload.get("message_count", 0)
        tools = payload.get("tool_call_count", 0)
        return f"{msgs} messages, {tools} tool calls, {dur:.0f}s"

    if etype == "TOOL_CALL":
        name = payload.get("tool_name", "?")
        inp = payload.get("tool_input", {})
        # Show the most useful argument
        detail = str(inp.get("file_path") or inp.get("command") or inp.get("pattern") or "")
        if detail:
            return f"{name}({detail[:80]})"
        return str(name)

    if etype == "TOOL_RESULT":
        name = payload.get("tool_name", "?")
        dur = payload.get("duration_ms", 0)
        failed = payload.get("failed", False)
        result = str(payload.get("result", ""))[:120]
        status = "FAILED" if failed else "ok"
        return f"{name} → {status} ({dur:.0f}ms) {result}"

    if etype == "USER_INPUT":
        return str(payload.get("text", payload.get("content", "")))

    if etype in ("ASSISTANT_OUTPUT", "ASSISTANT_RESPONSE", "ASSISTANT"):
        text = str(payload.get("text", payload.get("content", "")))
        return text[:200] if text else "(empty response)"

    if etype == "AGENT_DECISION":
        task = payload.get("task", "?")
        pattern = payload.get("chosen_pattern", "?")
        return f"Decision: {task[:80]} → pattern {pattern[:40]}"

    if etype == "AGENT_LEARNING_AUDIT":
        drift = payload.get("drift_detected", False)
        gaps = len(payload.get("pattern_gaps", []))
        return f"Learning audit: drift={'yes' if drift else 'no'}, {gaps} pattern gaps"

    if etype == "AGENT_CONTEXT_COMPRESSION":
        return str(payload.get("content", "context compressed"))

    if etype == "CLARITY_SUMMARY":
        score = payload.get("alignment_score", "?")
        devs = payload.get("deviations_count", 0)
        lessons = payload.get("lessons_count", 0)
        return f"Alignment: {score:.0f}%, {devs} deviations, {lessons} lessons"

    if etype == "CLARITY_DEVIATION":
        metric = payload.get("metric", "?")
        planned = payload.get("planned", "?")
        actual = payload.get("actual", "?")
        severity = payload.get("severity", "?")
        return f"{severity} deviation in {metric}: planned {planned}, actual {actual}"

    if etype == "CLARITY_LESSON":
        desc = payload.get("description", "")
        ltype = payload.get("lesson_type", "")
        return f"[{ltype}] {desc}" if desc else etype

    if etype.startswith("CLARITY_"):
        return str(payload.get("content", payload.get("summary", etype)))

    if etype == "QUALITY_REPORT":
        score = payload.get("overall_score", "?")
        return f"Quality score: {score}"

    # Fallback: show first meaningful field values
    skip = {"content_hash", "session_id", "timestamp", "tool_use_id"}
    parts = []
    for k, v in payload.items():
        if k in skip:
            continue
        sv = str(v)
        if len(sv) > 80:
            sv = sv[:80] + "..."
        parts.append(f"{k}={sv}")
        if len(parts) >= 3:
            break
    return ", ".join(parts) if parts else "(empty payload)"


def _print_events(events: list[dict[str, Any]], highlight: str | None = None) -> None:
    """Pretty-print a list of events with optional keyword highlighting."""
    for event in events:
        ts = event["timestamp"]
        try:
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            time_str = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        except Exception:
            time_str = str(ts)

        actor = event["actor"].upper()
        etype = event["event_type"]
        payload = event["payload"]
        content_hash = event.get("content_hash", "")[:8]

        click.secho(f"[{time_str}] ", fg="bright_black", nl=False)
        click.secho(f"{etype} ", fg="white", bold=True, nl=False)
        click.secho(f"({actor}) ", fg="bright_black", nl=False)
        click.secho(f"[{content_hash}]", fg="bright_black")

        content = _summarize_event(etype, payload)
        # Truncate long summaries to keep output readable
        max_len = 300
        if len(content) > max_len:
            content = content[:max_len] + "..."

        if highlight:
            pattern = re.compile(re.escape(highlight), re.IGNORECASE)
            parts = pattern.split(content)
            matches = pattern.findall(content)
            for i, part in enumerate(parts):
                _safe_echo(part, nl=False)
                if i < len(matches):
                    click.secho(matches[i], fg="red", bold=True, nl=False)
            click.echo()
        else:
            color = {"USER": "blue", "ASSISTANT": "magenta", "SYSTEM": "yellow"}.get(actor, "white")
            _safe_echo(click.style(f"  {content}", fg=color))

        click.echo(click.style("-" * 60, fg="bright_black"))


@cli.command("outcomes")
@click.option("--days", default=30, type=int, help="Lookback window in days")
def outcomes_cmd(days: int) -> None:
    """Measure how well the system is actually learning.

    Shows rework patterns, knowledge stability, correction rates,
    and overall trajectory. Use this to see if things are improving
    or if we're spinning in circles.
    """
    from divineos.agent_integration.outcome_measurement import (
        measure_correction_rate,
        measure_correction_trend,
        measure_knowledge_drift,
        measure_rework,
    )

    click.secho("\n=== Outcome Measurements ===\n", fg="cyan", bold=True)

    # 1. Rework detection
    rework = measure_rework(lookback_days=days)
    if rework:
        click.secho(f"  REWORK ({len(rework)} recurring issues):", fg="red", bold=True)
        for item in rework[:5]:
            click.secho(f"    [{item['severity']}] ", fg="bright_black", nl=False)
            _safe_echo(f"{item['description'][:80]}")
            click.secho(
                f"         {item['occurrences']}x in {item['session_count']} sessions",
                fg="bright_black",
            )
    else:
        click.secho("  REWORK: None detected", fg="green")
    click.echo()

    # 2. Knowledge drift
    drift = measure_knowledge_drift(lookback_days=days)
    churn_color = (
        "green" if drift["churn_rate"] < 0.1 else "yellow" if drift["churn_rate"] < 0.3 else "red"
    )
    click.secho("  KNOWLEDGE STABILITY:", fg="cyan", bold=True)
    click.secho(f"    Churn rate: {drift['churn_rate']:.1%}", fg=churn_color)
    click.echo(f"    Superseded: {drift['total_superseded']} entries in {days} days")
    click.echo(f"    Avg lifespan: {drift['avg_lifespan_hours']:.0f} hours")
    if drift["short_lived"]:
        click.secho(f"    Short-lived (<24h): {len(drift['short_lived'])} entries", fg="yellow")
        for item in drift["short_lived"][:3]:
            _safe_echo(f"      [{item['knowledge_type']}] {item['content']}")
    click.echo()

    # 3. Correction rate + trend
    rate = measure_correction_rate()
    trend = measure_correction_trend()
    rate_color = {"healthy": "green", "mixed": "yellow", "struggling": "red"}[rate["assessment"]]
    trend_color = {
        "improving": "green",
        "stable": "yellow",
        "worsening": "red",
        "insufficient_data": "bright_black",
    }
    click.secho("  CORRECTION RATE:", fg="cyan", bold=True)
    click.secho(
        f"    {rate['corrections']} corrections / {rate['encouragements']} encouragements "
        f"= {rate['ratio']:.0%}",
        fg=rate_color,
    )
    if trend["trend"] != "insufficient_data":
        click.secho(
            f"    Trend: {trend['trend']} (recent {trend['recent_avg']:.0%} vs overall {trend['overall_avg']:.0%})",
            fg=trend_color[trend["trend"]],
        )
    if trend["sessions"]:
        click.secho("    Per session:", fg="bright_black")
        for s in trend["sessions"][-5:]:
            bar = "#" * int(s["ratio"] * 20)
            click.secho(f"      {s['session_tag'][:8]}: ", fg="bright_black", nl=False)
            click.secho(
                f"{bar:<20s}",
                fg="red" if s["ratio"] > 0.5 else "yellow" if s["ratio"] > 0.3 else "green",
                nl=False,
            )
            click.echo(f" {s['corrections']}c/{s['encouragements']}e")
    click.echo()

    # Overall
    if not rework and drift["churn_rate"] < 0.1 and rate["assessment"] == "healthy":
        click.secho("  TRAJECTORY: Learning effectively", fg="green", bold=True)
    elif rework or rate["assessment"] == "struggling":
        click.secho("  TRAJECTORY: Needs attention", fg="red", bold=True)
    else:
        click.secho("  TRAJECTORY: Mixed signals", fg="yellow", bold=True)
    click.echo()


@cli.command("hud")
@click.option("--save", is_flag=True, help="Save a HUD snapshot to disk")
@click.option("--load", is_flag=True, help="Load the last saved HUD snapshot")
@click.option("--slots", default="", help="Comma-separated slot names to display (default: all)")
def hud_cmd(save: bool, load: bool, slots: str) -> None:
    """Display my heads-up display — everything I need to know at once.

    This is my dashboard: identity, goals, lessons, health, warnings,
    and task state. All at equal weight, all simultaneous.
    """
    from divineos.core.hud import build_hud, load_hud_snapshot, save_hud_snapshot

    if save:
        path = save_hud_snapshot()
        click.secho(f"[+] HUD snapshot saved to {path}", fg="green")
        return

    if load:
        snapshot = load_hud_snapshot()
        if snapshot:
            _safe_echo(snapshot)
        else:
            click.secho("[~] No saved HUD snapshot found.", fg="yellow")
        return

    slot_list = [s.strip() for s in slots.split(",") if s.strip()] if slots else None
    hud_text = build_hud(slots=slot_list)
    _safe_echo(hud_text)


@cli.group("goal")
def goal_group() -> None:
    """Track what the user asked me to do. My compass against drift."""


@goal_group.command("add")
@click.argument("text")
@click.option("--original", default="", help="The user's exact words")
def goal_add_cmd(text: str, original: str) -> None:
    """Add a new goal to track."""
    if not text.strip():
        click.secho("[-] Goal text cannot be empty.", fg="yellow")
        return
    from divineos.core.hud import add_goal

    add_goal(text, original_words=original)
    click.secho(f"[+] Goal added: {text}", fg="green")
    if original:
        click.secho(f'    (User\'s words: "{original}")', fg="bright_black")


@goal_group.command("done")
@click.argument("text")
def goal_done_cmd(text: str) -> None:
    """Mark a goal as complete (matches partial text)."""
    if not text.strip():
        click.secho("[-] Please specify which goal to complete.", fg="yellow")
        return
    from divineos.core.hud import complete_goal

    if complete_goal(text):
        click.secho(f"[+] Goal completed: {text}", fg="green")
    else:
        click.secho(f"[~] No matching goal found for: {text}", fg="yellow")


@goal_group.command("list")
def goal_list_cmd() -> None:
    """Show current goals."""
    from divineos.core.hud import SLOT_BUILDERS

    _safe_echo(SLOT_BUILDERS["active_goals"]())


@cli.command("plan")
@click.argument("goal")
@click.option("--files", default=0, type=int, help="Estimated files to touch")
@click.option("--time", "time_min", default=0, type=int, help="Estimated minutes")
def plan_cmd(goal: str, files: int, time_min: int) -> None:
    """Set a session plan so clarity analysis can compare plan vs actual."""
    if not goal.strip():
        click.secho("[-] Plan goal cannot be empty.", fg="yellow")
        return
    from divineos.core.hud import set_session_plan

    set_session_plan(
        goal=goal,
        estimated_files=files,
        estimated_time_minutes=time_min,
    )
    click.secho(f"[+] Session plan set: {goal}", fg="green")
    if files:
        click.secho(f"    Estimated files: {files}", fg="bright_black")
    if time_min:
        click.secho(f"    Estimated time: {time_min}min", fg="bright_black")


@goal_group.command("clear")
def goal_clear_cmd() -> None:
    """Remove completed goals from the list."""
    import json

    from divineos.core.hud import _ensure_hud_dir

    path = _ensure_hud_dir() / "active_goals.json"
    if not path.exists():
        click.secho("[~] No goals to clear.", fg="yellow")
        return

    try:
        goals = json.loads(path.read_text(encoding="utf-8"))
        active = [g for g in goals if g.get("status") != "done"]
        removed = len(goals) - len(active)
        path.write_text(json.dumps(active, indent=2), encoding="utf-8")
        click.secho(f"[+] Cleared {removed} completed goals, {len(active)} remain.", fg="green")
    except Exception as e:
        click.secho(f"[!] Failed to clear goals: {e}", fg="red")


@cli.command("clarity")
@click.option(
    "--file",
    "file_path",
    type=click.Path(exists=True),
    default=None,
    help="Session file to analyze",
)
def clarity_cmd(file_path: str | None) -> None:
    """Run clarity analysis on a session.

    Analyzes deviations between expected and actual execution,
    extracts lessons, and generates recommendations.
    Defaults to the most recent session if no file given.
    """
    from divineos.clarity_system.session_bridge import run_clarity_analysis

    if file_path:
        from pathlib import Path

        session_file = Path(file_path)
    else:
        session_files = _analyzer_mod.find_sessions()
        if not session_files:
            click.secho("[!] No session files found.", fg="red")
            return
        session_file = session_files[0]

    click.secho(f"\n[~] Analyzing session: {session_file.stem[:16]}...", fg="cyan")

    try:
        analysis = _analyzer_mod.analyze_session(session_file)
        result = run_clarity_analysis(analysis)

        summary = result["summary"]
        deviations = result["deviations"]
        lessons = result["lessons"]
        recommendations = result["recommendations"]

        click.secho("\n=== Clarity Analysis ===\n", fg="cyan", bold=True)

        # Execution metrics
        m = summary.metrics
        click.secho("  EXECUTION:", fg="cyan", bold=True)
        click.echo(f"    Files touched:  {m.actual_files}")
        click.echo(f"    Tool calls:     {m.actual_tool_calls}")
        click.echo(f"    Errors:         {m.actual_errors}")
        click.echo(f"    Duration:       {m.actual_time_minutes:.1f} min")
        click.echo(f"    Success rate:   {m.success_rate:.0%}")
        click.echo()

        # Alignment score
        score = result["alignment_score"]
        color = "green" if score >= 80 else "yellow" if score >= 50 else "red"
        click.secho(f"  ALIGNMENT: {score:.0f}%", fg=color, bold=True)
        click.echo()

        # Deviations
        if deviations:
            click.secho(f"  DEVIATIONS ({len(deviations)}):", fg="cyan", bold=True)
            for d in deviations:
                sev_color = {"high": "red", "medium": "yellow", "low": "green"}[d.severity]
                click.secho(f"    [{d.severity}] ", fg=sev_color, nl=False)
                click.echo(
                    f"{d.metric}: planned {d.planned:.0f}, actual {d.actual:.0f} "
                    f"({d.percentage:.0f}% deviation)"
                )
            click.echo()

        # Lessons
        if lessons:
            click.secho(f"  LESSONS ({len(lessons)}):", fg="cyan", bold=True)
            for lesson in lessons:
                _safe_echo(f"    [{lesson.type}] {lesson.description}")
                _safe_echo(f"      -> {lesson.insight}")
            click.echo()

        # Recommendations
        if recommendations:
            click.secho(f"  RECOMMENDATIONS ({len(recommendations)}):", fg="cyan", bold=True)
            for rec in recommendations:
                priority_color = {"high": "red", "medium": "yellow", "low": "green"}[rec.priority]
                click.secho(f"    [{rec.priority}] ", fg=priority_color, nl=False)
                _safe_echo(rec.recommendation_text)
            click.echo()

        if not deviations and not lessons:
            click.secho("  Clean session -- no significant deviations detected.", fg="green")
            click.echo()

    except Exception as e:
        click.secho(f"[!] Clarity analysis failed: {e}", fg="red")


if __name__ == "__main__":
    cli()


@cli.command("analyze")
@click.argument("file_path", type=click.Path(exists=True))
def analyze_cmd(file_path: str) -> None:
    """Analyze a session and generate a quality report.

    Runs all 7 quality checks + 10 session features on a JSONL file.
    Produces a plain-English report with findings and lessons.
    """
    path = Path(file_path)

    try:
        init_db()
        init_knowledge_table()
        init_quality_tables()
        init_feature_tables()

        click.secho(f"\n[+] Analyzing session: {path.name}", fg="cyan", bold=True)
        result = analyze_session(path)
        _display_and_store_analysis(result)

    except FileNotFoundError as e:
        click.secho(f"[-] File not found: {e}", fg="red")
    except ValueError as e:
        click.secho(f"[-] Invalid session: {e}", fg="red")
    except Exception as e:
        click.secho(f"[-] Error during analysis: {e}", fg="red")
        logger.exception("Analysis failed")


@cli.command("analyze-now")
def analyze_now_cmd() -> None:
    """Analyze the current session from the ledger.

    This runs quality checks on the live session without needing a file.
    Useful for enforcement - run this to see what you're doing wrong right now.
    """
    from divineos.analysis.analysis import export_current_session_to_jsonl

    try:
        init_db()
        init_knowledge_table()
        init_quality_tables()
        init_feature_tables()

        click.secho("\n[+] Exporting current session from ledger...", fg="cyan", bold=True)
        session_file = export_current_session_to_jsonl(limit=200)

        click.secho("[+] Analyzing live session...", fg="cyan")
        result = analyze_session(session_file)
        _display_and_store_analysis(result)

    except ValueError as e:
        click.secho(f"[-] No session data: {e}", fg="red")
    except Exception as e:
        click.secho(f"[-] Error during analysis: {e}", fg="red")
        logger.exception("Analysis failed")


@cli.command("report")
@click.argument("session_id", required=False)
def report_cmd(session_id: str) -> None:
    """Display a stored analysis report.

    If no session_id provided, shows list of recent sessions.
    """
    from divineos.analysis.analysis import get_stored_report, list_recent_sessions

    try:
        if not session_id:
            # List recent sessions
            sessions = list_recent_sessions(limit=10)

            if not sessions:
                click.secho("\n[-] No analyzed sessions found yet.", fg="yellow")
                click.secho(
                    "    Run 'divineos analyze <file.jsonl>' to analyze a session.",
                    fg="bright_black",
                )
                click.echo()
                return

            # Show all sessions — some may have 0 files if analyzed from ledger
            real_sessions = sessions

            click.secho(f"\n=== {len(real_sessions)} Analyzed Sessions ===\n", fg="cyan", bold=True)
            for i, session in enumerate(real_sessions, 1):
                click.secho(f"  {i}. {session['session_id']}", fg="white", bold=True)

                # Format timestamp
                try:
                    ts = datetime.fromtimestamp(
                        session["created_at"],
                        tz=timezone.utc,
                    ).strftime("%Y-%m-%d %H:%M:%S UTC")
                    click.secho(f"     Time: {ts}", fg="bright_black")
                except Exception:
                    click.secho(f"     Time: {session['created_at']}", fg="bright_black")

                click.secho(f"     Files: {session['file_count']}", fg="bright_black")
                click.echo()

            click.secho("Usage: divineos report <session_id>", fg="bright_black")
            click.echo()
        else:
            # Retrieve specific report
            report = get_stored_report(session_id)

            if not report:
                click.secho(f"[-] Session not found: {session_id}", fg="red")
                return

            click.echo()
            _safe_echo(report)
            click.echo()

    except Exception as e:
        click.secho(f"[-] Error retrieving report: {e}", fg="red")
        logger.exception("Report retrieval failed")


@cli.command("cross-session")
@click.option("--limit", default=10, type=int, help="Number of sessions to analyze")
def cross_session_cmd(limit: int) -> None:
    """Compare findings across multiple sessions.

    Shows trends and patterns in your performance over time.
    """
    from divineos.analysis.analysis import compute_cross_session_trends, format_cross_session_report

    try:
        click.secho(f"\n[+] Analyzing trends across last {limit} sessions...", fg="cyan")

        # Compute trends
        trends = compute_cross_session_trends(limit=limit)

        # Format report
        report = format_cross_session_report(trends)

        # Display
        click.echo()
        _safe_echo(report)
        click.echo()

    except Exception as e:
        click.secho(f"[-] Error during cross-session analysis: {e}", fg="red")
        logger.exception("Cross-session analysis failed")


@cli.command("emit")
@click.argument("event_type")
@click.option("--content", default="", help="Content for USER_INPUT or ASSISTANT_OUTPUT")
@click.option("--tool-name", default="", help="Tool name for TOOL_CALL or TOOL_RESULT")
@click.option("--tool-input", default="{}", help="Tool input as JSON for TOOL_CALL")
@click.option("--tool-use-id", default="", help="Tool use ID for TOOL_CALL or TOOL_RESULT")
@click.option("--result", default="", help="Result for TOOL_RESULT")
@click.option("--duration-ms", default=0, type=int, help="Duration in ms for TOOL_RESULT")
@click.option(
    "--session-id",
    default="",
    help="Session ID for SESSION_END (optional, uses current if not provided)",
)
def emit_cmd(
    event_type: str,
    content: str,
    tool_name: str,
    tool_input: str,
    tool_use_id: str,
    result: str,
    duration_ms: int,
    session_id: str,
) -> None:
    """Emit an event to the ledger using proper event emission functions.

    Supported event types:
    - USER_INPUT: --content "message"
    - ASSISTANT_OUTPUT: --content "response"
    - TOOL_CALL: --tool-name X --tool-input '{"key": "value"}' --tool-use-id Y
    - TOOL_RESULT: --tool-name X --tool-use-id Y --result "..." --duration-ms N
    - SESSION_END: (no arguments needed, queries ledger for actual counts)
    """
    import json
    import sys

    from divineos.event.event_emission import (
        emit_event,
        emit_session_end,
        emit_tool_call,
        emit_tool_result,
        emit_user_input,
    )

    try:
        event_id: str | None = None
        if event_type == "USER_INPUT":
            if not content:
                click.secho("[-] USER_INPUT requires --content", fg="red")
                sys.exit(1)
            event_id = emit_user_input(content, session_id=session_id or None)
            click.secho("[+] Event emitted: USER_INPUT", fg="green")
            click.secho(f"    Event ID: {event_id}", fg="cyan")

        elif event_type == "ASSISTANT_OUTPUT":
            if not content:
                click.secho("[-] ASSISTANT_OUTPUT requires --content", fg="red")
                sys.exit(1)
            # ASSISTANT_OUTPUT uses the generic emit_event for backward compatibility
            event_id = emit_event(event_type, {"content": content}, actor="assistant")
            if event_id is None:
                click.secho("[-] Failed to emit event (recursive call)", fg="red")
                sys.exit(1)
            click.secho("[+] Event emitted: ASSISTANT_OUTPUT", fg="green")
            click.secho(f"    Event ID: {event_id}", fg="cyan")

        elif event_type == "TOOL_CALL":
            if not tool_name or not tool_use_id:
                click.secho("[-] TOOL_CALL requires --tool-name and --tool-use-id", fg="red")
                sys.exit(1)
            try:
                tool_input_dict = json.loads(tool_input)
            except json.JSONDecodeError:
                click.secho(f"[-] Invalid JSON for --tool-input: {tool_input}", fg="red")
                sys.exit(1)
            event_id = emit_tool_call(
                tool_name,
                tool_input_dict,
                tool_use_id=tool_use_id,
                session_id=session_id or None,
            )
            click.secho("[+] Event emitted: TOOL_CALL", fg="green")
            click.secho(f"    Event ID: {event_id}", fg="cyan")

        elif event_type == "TOOL_RESULT":
            if not tool_name or not tool_use_id or not result:
                click.secho(
                    "[-] TOOL_RESULT requires --tool-name, --tool-use-id, and --result",
                    fg="red",
                )
                sys.exit(1)
            event_id = emit_tool_result(
                tool_name,
                tool_use_id,
                result,
                duration_ms,
                session_id=session_id or None,
            )
            click.secho("[+] Event emitted: TOOL_RESULT", fg="green")
            click.secho(f"    Event ID: {event_id}", fg="cyan")

        elif event_type == "SESSION_END":
            # SESSION_END queries ledger for actual counts
            event_id = emit_session_end(session_id=session_id or None)
            click.secho("[+] Event emitted: SESSION_END", fg="green")
            click.secho(f"    Event ID: {event_id}", fg="cyan")

            _run_session_end_pipeline()

        elif event_type == "EXPLANATION":
            if not content:
                click.secho("[-] EXPLANATION requires --content", fg="red")
                sys.exit(1)
            event_id = emit_event(
                "EXPLANATION",
                {"content": content},
                actor="assistant",
                validate=False,
            )
            if event_id is None:
                click.secho("[-] Failed to emit event (recursive call)", fg="red")
                sys.exit(1)
            click.secho("[+] Event emitted: EXPLANATION", fg="green")
            click.secho(f"    Event ID: {event_id}", fg="cyan")
            click.secho(f"    Content: {content[:100]}...", fg="cyan")

        else:
            click.secho(f"[-] Unknown event type: {event_type}", fg="red")
            click.secho(
                "    Supported types: USER_INPUT, ASSISTANT_OUTPUT, TOOL_CALL, TOOL_RESULT, SESSION_END, EXPLANATION",
                fg="yellow",
            )
            sys.exit(1)

    except Exception as e:
        click.secho(f"[-] Error emitting event: {e}", fg="red")
        logger.exception("Event emission failed")
        sys.exit(1)


@cli.command("verify-enforcement")
def verify_enforcement_cmd() -> None:
    """Verify that the event enforcement system is working correctly.

    This command checks:
    - All event types are being captured
    - Event capture rates
    - Missing or orphaned events
    - Event hash integrity

    Use this to ensure the OS enforcement layer is functioning properly.
    """
    from divineos.core.enforcement_verifier import generate_enforcement_report

    try:
        click.secho("\n[+] Verifying event enforcement system...", fg="cyan", bold=True)
        click.echo()

        # Generate and display report
        report = generate_enforcement_report()
        _safe_echo(report)

    except Exception as e:
        click.secho(f"[-] Error verifying enforcement: {e}", fg="red")
        logger.exception("Enforcement verification failed")
        sys.exit(1)
