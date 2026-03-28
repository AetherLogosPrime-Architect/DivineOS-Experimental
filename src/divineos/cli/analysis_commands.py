"""Analysis commands — sessions, scan, deep-report, patterns, outcomes, analyze, analyze-now,
report, cross-session, clarity."""

from pathlib import Path

import click

import divineos.analysis.session_analyzer as _analyzer_mod
from divineos.cli._helpers import _display_and_store_analysis, _safe_echo
from divineos.cli._wrappers import (
    _wrapped_apply_session_feedback,
    _wrapped_deep_extract_knowledge,
    _wrapped_get_cross_session_summary,
    _wrapped_run_all_features,
    _wrapped_store_features,
    _wrapped_store_knowledge,
    init_feature_tables,
    init_quality_tables,
    logger,
)
from divineos.analysis.analysis import analyze_session
from divineos.core.knowledge import init_knowledge_table
from divineos.core.ledger import init_db


def register(cli: click.Group) -> None:
    """Register all analysis commands on the CLI group."""

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
            records = _analyzer_mod._load_records(path)
            deep_ids = _wrapped_deep_extract_knowledge(analysis, records)
            stored += len(deep_ids)
            click.secho(f"[+] Deep extraction: {len(deep_ids)} knowledge entries", fg="cyan")
        else:
            for c in analysis.corrections:
                lower = c.content.lower()
                is_boundary = any(
                    w in lower for w in ("never", "always", "must", "don't", "do not")
                )
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

    @cli.command("outcomes")
    @click.option("--days", default=30, type=int, help="Lookback window in days")
    def outcomes_cmd(days: int) -> None:
        """Measure how well the system is actually learning."""
        from divineos.agent_integration.outcome_measurement import (
            measure_correction_rate,
            measure_correction_trend,
            measure_knowledge_drift,
            measure_rework,
        )

        click.secho("\n=== Outcome Measurements ===\n", fg="cyan", bold=True)

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

        drift = measure_knowledge_drift(lookback_days=days)
        churn_color = (
            "green"
            if drift["churn_rate"] < 0.1
            else "yellow"
            if drift["churn_rate"] < 0.3
            else "red"
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

        rate = measure_correction_rate()
        trend = measure_correction_trend()
        rate_color = {"healthy": "green", "mixed": "yellow", "struggling": "red"}[
            rate["assessment"]
        ]
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

        if not rework and drift["churn_rate"] < 0.1 and rate["assessment"] == "healthy":
            click.secho("  TRAJECTORY: Learning effectively", fg="green", bold=True)
        elif rework or rate["assessment"] == "struggling":
            click.secho("  TRAJECTORY: Needs attention", fg="red", bold=True)
        else:
            click.secho("  TRAJECTORY: Mixed signals", fg="yellow", bold=True)
        click.echo()

    @cli.command("analyze")
    @click.argument("file_path", type=click.Path(exists=True))
    def analyze_cmd(file_path: str) -> None:
        """Analyze a session and generate a quality report."""
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
        """Analyze the current session from the ledger."""
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
        """Display a stored analysis report."""
        from divineos.analysis.analysis import get_stored_report, list_recent_sessions
        from datetime import datetime, timezone

        try:
            if not session_id:
                sessions = list_recent_sessions(limit=10)

                if not sessions:
                    click.secho("\n[-] No analyzed sessions found yet.", fg="yellow")
                    click.secho(
                        "    Run 'divineos analyze <file.jsonl>' to analyze a session.",
                        fg="bright_black",
                    )
                    click.echo()
                    return

                real_sessions = sessions

                click.secho(
                    f"\n=== {len(real_sessions)} Analyzed Sessions ===\n",
                    fg="cyan",
                    bold=True,
                )
                for i, session in enumerate(real_sessions, 1):
                    click.secho(f"  {i}. {session['session_id']}", fg="white", bold=True)

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
        """Compare findings across multiple sessions."""
        from divineos.analysis.analysis import (
            compute_cross_session_trends,
            format_cross_session_report,
        )

        try:
            click.secho(f"\n[+] Analyzing trends across last {limit} sessions...", fg="cyan")

            trends = compute_cross_session_trends(limit=limit)
            report = format_cross_session_report(trends)

            click.echo()
            _safe_echo(report)
            click.echo()

        except Exception as e:
            click.secho(f"[-] Error during cross-session analysis: {e}", fg="red")
            logger.exception("Cross-session analysis failed")

    @cli.command("clarity")
    @click.option(
        "--file",
        "file_path",
        type=click.Path(exists=True),
        default=None,
        help="Session file to analyze",
    )
    def clarity_cmd(file_path: str | None) -> None:
        """Run clarity analysis on a session."""
        from divineos.clarity_system.session_bridge import run_clarity_analysis

        if file_path:
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

            m = summary.metrics
            click.secho("  EXECUTION:", fg="cyan", bold=True)
            click.echo(f"    Files touched:  {m.actual_files}")
            click.echo(f"    Tool calls:     {m.actual_tool_calls}")
            click.echo(f"    Errors:         {m.actual_errors}")
            click.echo(f"    Duration:       {m.actual_time_minutes:.1f} min")
            click.echo(f"    Success rate:   {m.success_rate:.0%}")
            click.echo()

            score = result["alignment_score"]
            color = "green" if score >= 80 else "yellow" if score >= 50 else "red"
            click.secho(f"  ALIGNMENT: {score:.0f}%", fg=color, bold=True)
            click.echo()

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

            if lessons:
                click.secho(f"  LESSONS ({len(lessons)}):", fg="cyan", bold=True)
                for lesson in lessons:
                    _safe_echo(f"    [{lesson.type}] {lesson.description}")
                    _safe_echo(f"      -> {lesson.insight}")
                click.echo()

            if recommendations:
                click.secho(f"  RECOMMENDATIONS ({len(recommendations)}):", fg="cyan", bold=True)
                for rec in recommendations:
                    priority_color = {"high": "red", "medium": "yellow", "low": "green"}[
                        rec.priority
                    ]
                    click.secho(f"    [{rec.priority}] ", fg=priority_color, nl=False)
                    _safe_echo(rec.recommendation_text)
                click.echo()

            if not deviations and not lessons:
                click.secho("  Clean session -- no significant deviations detected.", fg="green")
                click.echo()

        except Exception as e:
            click.secho(f"[!] Clarity analysis failed: {e}", fg="red")

    @cli.command("growth")
    @click.option("--limit", default=20, type=int, help="Number of sessions to analyze")
    def growth_cmd(limit: int) -> None:
        """Show my growth map — how I'm changing over time."""
        from divineos.core.growth import compute_growth_map, format_growth_map

        growth = compute_growth_map(limit=limit)
        _safe_echo(format_growth_map(growth))
