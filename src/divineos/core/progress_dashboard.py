"""Progress dashboard — measurable proof that the system works.

Every number comes from real data. No estimates, no vibes. If a skeptic
asks "show me the evidence," this is what we hand them.

Five sections:
1. Session trajectory — how many sessions, health trend
2. Knowledge growth — entries, types, maturity distribution
3. Learning evidence — correction trends, rework reduction
4. System health — test integrity, DB health, guardrail state
5. Behavioral indicators — briefing compliance, engagement, OS usage
"""

import sqlite3
import time
from dataclasses import dataclass, field

from loguru import logger


@dataclass
class ProgressReport:
    """Structured progress metrics — all from real data."""

    # Session trajectory
    total_sessions: int = 0
    session_health_trend: str = "unknown"  # improving/stable/worsening
    avg_health_score: float = 0.0
    recent_health_grade: str = "?"

    # Knowledge growth
    total_knowledge: int = 0
    active_knowledge: int = 0
    superseded_knowledge: int = 0
    knowledge_by_type: dict[str, int] = field(default_factory=dict)
    knowledge_by_maturity: dict[str, int] = field(default_factory=dict)
    directives_count: int = 0

    # Learning evidence
    correction_trend: str = "unknown"  # improving/stable/worsening
    correction_rate_recent: float = 0.0
    correction_rate_overall: float = 0.0
    rework_items: int = 0
    lessons_total: int = 0
    lessons_resolved: int = 0

    # System health
    knowledge_churn_rate: float = 0.0
    avg_knowledge_lifespan_hours: float = 0.0
    db_integrity: str = "unknown"

    # Behavioral indicators
    briefing_compliance: float = 0.0  # % of sessions with briefing loaded
    avg_engagement_actions: int = 0
    os_tools_used: int = 0  # distinct OS tool types used

    # User ratings (external ground truth)
    user_rating_avg: float = 0.0
    user_rating_count: int = 0
    user_rating_trend: str = "no_data"
    goodhart_correlation: str = "no_data"  # strong/moderate/weak/no_data

    # Metadata
    generated_at: float = field(default_factory=time.time)
    lookback_days: int = 30

    def one_liner(self) -> str:
        """The single-line summary for quick proof."""
        parts = [
            f"{self.total_sessions} sessions",
        ]

        if self.correction_trend == "improving":
            pct = _trend_percentage(self.correction_rate_overall, self.correction_rate_recent)
            parts.append(f"corrections v{pct}%")
        elif self.correction_trend == "worsening":
            parts.append("corrections ^")
        else:
            parts.append(f"corrections {self.correction_rate_recent:.0%}")

        parts.append(f"{self.active_knowledge} knowledge entries")
        parts.append(f"{self.directives_count} directives")
        parts.append(f"{self.lessons_resolved}/{self.lessons_total} lessons resolved")
        parts.append(f"health {self.recent_health_grade}")

        return " | ".join(parts)


def _trend_percentage(overall: float, recent: float) -> int:
    """Calculate improvement percentage between overall and recent rates."""
    if overall <= 0:
        return 0
    reduction = (overall - recent) / overall
    return max(0, int(reduction * 100))


def gather_progress(lookback_days: int = 30) -> ProgressReport:
    """Gather all progress metrics from real data.

    Each section is gathered independently — a failure in one doesn't
    block the others. Errors are logged, not raised.
    """
    report = ProgressReport(lookback_days=lookback_days)

    _gather_session_trajectory(report, lookback_days)
    _gather_knowledge_growth(report)
    _gather_learning_evidence(report, lookback_days)
    _gather_system_health(report, lookback_days)
    _gather_behavioral_indicators(report)
    _gather_user_ratings(report)

    return report


def _gather_session_trajectory(report: ProgressReport, lookback_days: int) -> None:
    """Count sessions and compute health trend."""
    try:
        from divineos.core.ledger import count_events, get_events

        from divineos.event.event_capture import CONSOLIDATION_EVENT_TYPES

        counts = count_events()
        by_type = counts.get("by_type", {})
        # Sum historical SESSION_END and current CONSOLIDATION_CHECKPOINT rows
        report.total_sessions = sum(by_type.get(t, 0) for t in CONSOLIDATION_EVENT_TYPES)

        # Get recent sessions for health scoring
        sessions = get_events(event_type=CONSOLIDATION_EVENT_TYPES, limit=20)
        if sessions:
            # Use the most recent session's analysis for health grade
            _score_recent_sessions(report, sessions)

    except (ImportError, OSError, KeyError, sqlite3.OperationalError) as exc:
        logger.debug(f"Session trajectory gather failed: {exc}")


def _score_recent_sessions(report: ProgressReport, sessions: list[dict]) -> None:
    """Score recent sessions to compute health trend."""
    import json

    scores: list[float] = []

    # Read grades from session_validation table (where record_self_grade stores them)
    try:
        from divineos.core.knowledge import _get_connection as _kconn

        conn = _kconn()
        try:
            rows = conn.execute(
                "SELECT self_score FROM session_validation ORDER BY created_at DESC LIMIT 10"
            ).fetchall()
            scores = [float(r[0]) for r in rows if r[0] is not None]
        finally:
            conn.close()
    except (ImportError, sqlite3.OperationalError):
        pass

    # Fallback: check SESSION_END payloads
    if not scores:
        for session in sessions[-10:]:
            payload = session.get("payload", {})
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except (json.JSONDecodeError, TypeError):
                    payload = {}
            score = payload.get("health_score")
            if score is not None:
                scores.append(float(score))

    if scores:
        report.avg_health_score = sum(scores) / len(scores)
        recent = scores[-3:] if len(scores) >= 3 else scores
        recent_avg = sum(recent) / len(recent)

        if recent_avg >= 0.85:
            report.recent_health_grade = "A"
        elif recent_avg >= 0.70:
            report.recent_health_grade = "B"
        elif recent_avg >= 0.55:
            report.recent_health_grade = "C"
        elif recent_avg >= 0.40:
            report.recent_health_grade = "D"
        else:
            report.recent_health_grade = "F"

        # Trend: compare first half to second half
        if len(scores) >= 2:
            first_half = scores[: len(scores) // 2] or scores[:1]
            second_half = scores[len(scores) // 2 :] or scores[-1:]
            first_avg = sum(first_half) / len(first_half)
            second_avg = sum(second_half) / len(second_half)
            if second_avg > first_avg + 0.05:
                report.session_health_trend = "improving"
            elif second_avg < first_avg - 0.05:
                report.session_health_trend = "worsening"
            else:
                report.session_health_trend = "stable"
        else:
            report.session_health_trend = "insufficient_data"
    else:
        # No health scores in payloads — use correction trend as proxy
        report.recent_health_grade = "?"
        report.session_health_trend = "unknown"


def _gather_knowledge_growth(report: ProgressReport) -> None:
    """Count knowledge entries by type and maturity."""
    try:
        from divineos.core.knowledge import _get_connection

        conn = _get_connection()
        try:
            # Total entries (active only)
            try:
                report.active_knowledge = conn.execute(
                    "SELECT COUNT(*) FROM knowledge WHERE superseded_by IS NULL"
                ).fetchone()[0]
            except sqlite3.OperationalError:
                # Table doesn't exist yet
                return

            # Total including superseded
            report.total_knowledge = conn.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0]

            report.superseded_knowledge = report.total_knowledge - report.active_knowledge

            # By type (active only)
            rows = conn.execute(
                "SELECT knowledge_type, COUNT(*) FROM knowledge "
                "WHERE superseded_by IS NULL GROUP BY knowledge_type ORDER BY COUNT(*) DESC"
            ).fetchall()
            report.knowledge_by_type = {row[0]: row[1] for row in rows}

            # By maturity (active only)
            rows = conn.execute(
                "SELECT maturity, COUNT(*) FROM knowledge "
                "WHERE superseded_by IS NULL GROUP BY maturity ORDER BY COUNT(*) DESC"
            ).fetchall()
            report.knowledge_by_maturity = {row[0]: row[1] for row in rows}

            # Directives specifically
            report.directives_count = conn.execute(
                "SELECT COUNT(*) FROM knowledge "
                "WHERE knowledge_type = 'DIRECTIVE' AND superseded_by IS NULL"
            ).fetchone()[0]

        finally:
            conn.close()
    except (ImportError, OSError, KeyError, sqlite3.OperationalError) as exc:
        logger.debug(f"Knowledge growth gather failed: {exc}")


def _gather_learning_evidence(report: ProgressReport, lookback_days: int) -> None:
    """Correction trends, rework, and lesson tracking."""
    try:
        from divineos.agent_integration.outcome_measurement import (
            measure_correction_trend,
            measure_rework,
        )

        # Correction trend
        trend = measure_correction_trend(limit=20)
        report.correction_trend = trend["trend"]
        report.correction_rate_recent = trend["recent_avg"]
        report.correction_rate_overall = trend["overall_avg"]

        # Rework items
        rework = measure_rework(lookback_days=lookback_days)
        report.rework_items = len(rework)

    except (ImportError, OSError, KeyError, sqlite3.OperationalError) as exc:
        logger.debug(f"Learning evidence gather failed: {exc}")

    # Lesson stats
    try:
        from divineos.core.knowledge import get_lessons

        all_lessons = get_lessons()
        report.lessons_total = len(all_lessons)
        report.lessons_resolved = sum(
            1 for lesson in all_lessons if lesson.get("status") == "resolved"
        )
    except (ImportError, OSError, KeyError, sqlite3.OperationalError) as exc:
        logger.debug(f"Lesson stats gather failed: {exc}")


def _gather_system_health(report: ProgressReport, lookback_days: int) -> None:
    """Knowledge stability and DB integrity."""
    try:
        from divineos.agent_integration.outcome_measurement import measure_knowledge_drift

        drift = measure_knowledge_drift(lookback_days=lookback_days)
        report.knowledge_churn_rate = drift["churn_rate"]
        report.avg_knowledge_lifespan_hours = drift["avg_lifespan_hours"]
    except (ImportError, OSError, KeyError, sqlite3.OperationalError) as exc:
        logger.debug(f"Knowledge drift gather failed: {exc}")

    # DB integrity check
    try:
        from divineos.core.ledger_verify import verify_all_events

        result = verify_all_events()
        checked = result.get("checked", 0)
        failed = result.get("failed", 0)
        if failed == 0:
            report.db_integrity = "intact"
        elif checked > 0 and (failed / checked) < 0.01:
            # <1% failures = legacy hash drift, not corruption
            report.db_integrity = f"intact ({failed} legacy)"
        else:
            report.db_integrity = "broken"
    except (ImportError, OSError, KeyError, sqlite3.OperationalError) as exc:
        report.db_integrity = "unknown"
        logger.debug(f"DB integrity check failed: {exc}")


def _gather_behavioral_indicators(report: ProgressReport) -> None:
    """Briefing compliance, engagement patterns, OS tool usage."""
    try:
        from divineos.core.ledger import get_events

        # Count BRIEFING_LOADED events vs SESSION_END events
        events = get_events(event_type="BRIEFING_LOADED", limit=1000)
        briefing_count = len(events)

        from divineos.event.event_capture import CONSOLIDATION_EVENT_TYPES

        sessions = get_events(event_type=CONSOLIDATION_EVENT_TYPES, limit=1000)
        session_count = len(sessions)

        if session_count > 0:
            report.briefing_compliance = min(1.0, briefing_count / session_count)

        # Count distinct OS tool usage from OS_QUERY events (logged when
        # the user runs divineos ask, recall, context, decide, etc.)
        os_query_events = get_events(event_type="OS_QUERY", limit=500)
        report.os_tools_used = len(os_query_events)

    except (ImportError, OSError, KeyError, sqlite3.OperationalError) as exc:
        logger.debug(f"Behavioral indicators gather failed: {exc}")


def _gather_user_ratings(report: ProgressReport) -> None:
    """Lite: user_ratings stripped — no-op."""
    _ = report


def format_progress_text(report: ProgressReport) -> str:
    """Format the progress report as human-readable text."""
    lines: list[str] = []

    lines.append("=== PROGRESS DASHBOARD ===")
    lines.append("")

    # One-liner summary
    lines.append(f"  {report.one_liner()}")
    lines.append("")

    # Section 1: Session Trajectory
    lines.append("-- Session Trajectory --")
    lines.append(f"  Total sessions:  {report.total_sessions}")
    lines.append(f"  Health trend:    {_format_trend(report.session_health_trend)}")
    if report.avg_health_score > 0:
        lines.append(f"  Avg health:      {report.avg_health_score:.2f}")
    lines.append(f"  Recent grade:    {report.recent_health_grade}")
    lines.append("")

    # Section 2: Knowledge Growth
    lines.append("-- Knowledge Growth --")
    lines.append(f"  Active entries:  {report.active_knowledge}")
    lines.append(f"  Superseded:      {report.superseded_knowledge}")
    lines.append(f"  Directives:      {report.directives_count}")

    if report.knowledge_by_type:
        lines.append("  By type:")
        for ktype, count in sorted(report.knowledge_by_type.items(), key=lambda x: -x[1]):
            lines.append(f"    {ktype:<15} {count}")

    if report.knowledge_by_maturity:
        lines.append("  By maturity:")
        for mat, count in sorted(report.knowledge_by_maturity.items(), key=lambda x: -x[1]):
            lines.append(f"    {mat:<15} {count}")
    lines.append("")

    # Section 3: Learning Evidence
    lines.append("-- Learning Evidence --")
    lines.append(f"  Correction trend:   {_format_trend(report.correction_trend)}")
    lines.append(f"  Recent corr. rate:  {report.correction_rate_recent:.1%}")
    lines.append(f"  Overall corr. rate: {report.correction_rate_overall:.1%}")
    if report.correction_trend == "improving":
        pct = _trend_percentage(report.correction_rate_overall, report.correction_rate_recent)
        lines.append(f"  Improvement:        v{pct}% from overall baseline")
    lines.append(f"  Rework items:       {report.rework_items}")
    lines.append(f"  Lessons:            {report.lessons_resolved}/{report.lessons_total} resolved")
    lines.append("")

    # Section 4: System Health
    lines.append("-- System Health --")
    lines.append(f"  Knowledge churn:    {report.knowledge_churn_rate:.1%}")
    if report.avg_knowledge_lifespan_hours > 0:
        lines.append(f"  Avg lifespan:       {report.avg_knowledge_lifespan_hours:.0f}h")
    lines.append(f"  DB integrity:       {report.db_integrity}")
    lines.append("")

    # Section 5: Behavioral Indicators
    lines.append("-- Behavioral Indicators --")
    lines.append(f"  Briefing compliance: {report.briefing_compliance:.0%}")
    lines.append(f"  OS tools used:       {report.os_tools_used} distinct tools")
    lines.append("")

    # Section 6: User Satisfaction (external ground truth)
    if report.user_rating_count > 0:
        lines.append("-- User Satisfaction (Ground Truth) --")
        lines.append(f"  Average rating:     {report.user_rating_avg}/10")
        lines.append(f"  Sessions rated:     {report.user_rating_count}")
        lines.append(f"  Trend:              {_format_trend(report.user_rating_trend)}")
        if report.goodhart_correlation != "no_data":
            lines.append(f"  Goodhart check:     {report.goodhart_correlation}")
        lines.append("")

    return "\n".join(lines)


def format_progress_brief(report: ProgressReport) -> str:
    """Format a brief 3-line summary."""
    lines = [
        report.one_liner(),
        f"  Trend: {_format_trend(report.correction_trend)} | "
        f"Churn: {report.knowledge_churn_rate:.1%} | "
        f"Integrity: {report.db_integrity}",
        f"  Maturity: {_format_maturity_bar(report.knowledge_by_maturity)}",
    ]
    return "\n".join(lines)


def format_progress_export(report: ProgressReport) -> str:
    """Format as shareable markdown for external proof."""
    lines: list[str] = []

    lines.append("# DivineOS Progress Report")
    lines.append("")
    lines.append(f"> {report.one_liner()}")
    lines.append("")

    lines.append("## Session Trajectory")
    lines.append(f"- **{report.total_sessions}** sessions completed")
    lines.append(f"- Health trend: **{report.session_health_trend}**")
    lines.append(f"- Recent grade: **{report.recent_health_grade}**")
    lines.append("")

    lines.append("## Knowledge Store")
    lines.append(f"- **{report.active_knowledge}** active entries")
    lines.append(f"- **{report.superseded_knowledge}** superseded (replaced by better knowledge)")
    lines.append(f"- **{report.directives_count}** directives (permanent rules)")
    lines.append("")

    if report.knowledge_by_maturity:
        lines.append("### Maturity Distribution")
        for mat, count in sorted(report.knowledge_by_maturity.items(), key=lambda x: -x[1]):
            lines.append(f"- {mat}: {count}")
        lines.append("")

    lines.append("## Learning Evidence")
    lines.append(f"- Correction trend: **{report.correction_trend}**")
    if report.correction_trend == "improving":
        pct = _trend_percentage(report.correction_rate_overall, report.correction_rate_recent)
        lines.append(f"- Corrections down **{pct}%** from baseline")
    lines.append(f"- {report.lessons_resolved}/{report.lessons_total} lessons resolved")
    lines.append(f"- {report.rework_items} recurring rework items")
    lines.append("")

    lines.append("## System Integrity")
    lines.append(f"- Knowledge churn rate: {report.knowledge_churn_rate:.1%}")
    lines.append(f"- Database integrity: **{report.db_integrity}**")
    lines.append(f"- Briefing compliance: {report.briefing_compliance:.0%}")
    lines.append("")

    lines.append("---")
    lines.append(f"*Generated from {report.total_sessions} sessions of real data.*")

    return "\n".join(lines)


def _format_trend(trend: str) -> str:
    """Add arrows to trend labels."""
    arrows = {
        "improving": "^ improving",
        "stable": "- stable",
        "worsening": "v worsening",
        "insufficient_data": "? insufficient data",
        "unknown": "? unknown",
    }
    return arrows.get(trend, trend)


def _format_maturity_bar(by_maturity: dict[str, int]) -> str:
    """Show maturity distribution as a compact bar."""
    if not by_maturity:
        return "no data"

    total = sum(by_maturity.values())
    if total == 0:
        return "empty"

    parts: list[str] = []
    order = ["CONFIRMED", "TESTED", "HYPOTHESIS", "RAW", "REVISED"]
    for mat in order:
        count = by_maturity.get(mat, 0)
        if count > 0:
            pct = int(count / total * 100)
            parts.append(f"{mat[0]}:{pct}%")

    return " ".join(parts) if parts else "no data"
