"""Analysis Retrieval — Report retrieval, session listing, and cross-session trends.

Functions split from analysis_storage.py to keep modules focused.
"""

import sqlite3
from pathlib import Path
from typing import Any, cast

from loguru import logger

from divineos.analysis.analysis_types import AnalysisResult
from divineos.analysis.quality_storage import get_check_history
from divineos.core.ledger import get_connection_fk as get_qc_connection

_AR_ERRORS = (ImportError, sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError)


def get_stored_report(session_id: str) -> str | None:
    """Retrieve a stored analysis report from the database.

    Args:
        session_id: The session ID to retrieve

    Returns:
        Report text if found, None otherwise

    """
    try:
        conn = get_qc_connection()
        cursor = conn.cursor()

        # Query the session_report table — support partial ID matching
        cursor.execute(
            "SELECT report_text FROM session_report WHERE session_id LIKE ?",
            (session_id + "%",),
        )
        row = cursor.fetchone()

        if row and row[0]:
            conn.close()
            return cast("str", row[0])

        # If no report_text stored, check if checks/features exist
        cursor.execute(
            "SELECT COUNT(*) FROM check_result WHERE session_id LIKE ?",
            (session_id + "%",),
        )
        check_count = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM feature_result WHERE session_id LIKE ?",
            (session_id + "%",),
        )
        feature_count = cursor.fetchone()[0]

        if check_count > 0 or feature_count > 0:
            # Build a summary from stored check results
            parts = [f"Session {session_id}: {check_count} checks, {feature_count} features\n"]
            if check_count > 0:
                checks = cursor.execute(
                    "SELECT check_name, passed, score FROM check_result WHERE session_id LIKE ?",
                    (session_id + "%",),
                ).fetchall()
                parts.append("Quality Checks:")
                for name, passed, score in checks:
                    status = "PASS" if passed else "FAIL"
                    parts.append(f"  [{status}] {name}: {score:.2f}")
            conn.close()
            return "\n".join(parts)

        conn.close()

        return None
    except _AR_ERRORS as e:
        logger.error(f"Failed to retrieve report for session {session_id}: {e}")
        return None


def list_recent_sessions(limit: int = 10) -> list[dict[str, Any]]:
    """List recent analyzed sessions.

    Args:
        limit: Maximum number of sessions to return

    Returns:
        List of session dicts with id, created_at, file_count

    """

    try:
        conn = get_qc_connection()
        cursor = conn.cursor()

        # Query session_report table, ordered by created_at DESC
        cursor.execute(
            "SELECT session_id, created_at FROM session_report ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        rows = cursor.fetchall()

        sessions = []
        for row in rows:
            session_id = row[0]
            created_at = row[1]

            # Count files touched for this session
            cursor.execute("SELECT COUNT(*) FROM file_touched WHERE session_id = ?", (session_id,))
            file_count = cursor.fetchone()[0]

            sessions.append(
                {
                    "session_id": session_id,
                    "created_at": created_at,
                    "file_count": file_count,
                },
            )

        conn.close()
        return sessions
    except _AR_ERRORS as e:
        logger.error(f"Failed to list sessions: {e}")
        return []


def compute_cross_session_trends(limit: int = 10) -> dict[str, Any]:
    """Compute trends across multiple sessions.

    Args:
        limit: Number of recent sessions to analyze

    Returns:
        Dict with trends and patterns

    """
    # Get check history for each check
    trends: dict[str, Any] = {}
    for check_name in [
        "completeness",
        "correctness",
        "responsiveness",
        "safety",
        "honesty",
        "clarity",
        "task_adherence",
    ]:
        try:
            check_results: list[dict[str, Any]] = get_check_history(check_name, limit=limit)

            if check_results:
                # Only count explicitly passed (1), not inconclusive (-1)
                conclusive = [h for h in check_results if h.get("passed") != -1]
                pass_count = sum(1 for h in conclusive if h.get("passed") == 1)
                total_count = len(conclusive)
                inconclusive_count = len(check_results) - len(conclusive)
                pass_rate = (pass_count / total_count * 100) if total_count > 0 else 0

                trends[check_name] = {
                    "pass_rate": pass_rate,
                    "pass_count": pass_count,
                    "total_count": total_count,
                    "inconclusive_count": inconclusive_count,
                    "results": check_results[:5],  # Last 5 results
                }
        except _AR_ERRORS as e:
            # If check history not available, skip but log the error
            logger.debug(f"Failed to get check history for {check_name}: {e}")

    return trends


def format_cross_session_report(trends: dict[str, Any]) -> str:
    """Format cross-session trends as a plain-English report.

    Args:
        trends: Dict from compute_cross_session_trends()

    Returns:
        Formatted report string

    """
    lines = []

    lines.append("=" * 70)
    lines.append("CROSS-SESSION ANALYSIS")
    lines.append("=" * 70)
    lines.append("")

    if not trends:
        lines.append("No session data available yet.")
        lines.append("")
        lines.append("=" * 70)
        return "\n".join(lines)

    # Show each check
    for check_name, data in sorted(trends.items()):
        name = check_name.replace("_", " ").title()
        pass_rate = data["pass_rate"]
        pass_count = data["pass_count"]
        total_count = data["total_count"]
        inconclusive_count = data.get("inconclusive_count", 0)

        if total_count == 0:
            # All inconclusive — nothing to evaluate
            lines.append(f"{name}: [~] Insufficient data")
            lines.append(f"  {inconclusive_count} inconclusive (nothing to evaluate)")
            lines.append("")
            continue

        # Determine trend
        if pass_rate >= 80:
            trend = "[+] Strong"
            color_hint = "(good)"
        elif pass_rate >= 60:
            trend = "[~] Stable"
            color_hint = "(okay)"
        else:
            trend = "[-] Needs work"
            color_hint = "(needs improvement)"

        lines.append(f"{name}: {trend} {color_hint}")
        detail = f"  Pass rate: {pass_rate:.0f}% ({pass_count}/{total_count})"
        if inconclusive_count:
            detail += f", {inconclusive_count} inconclusive"
        lines.append(detail)
        lines.append("")

    lines.append("=" * 70)
    lines.append("Trends based on recent sessions.")
    lines.append("=" * 70)

    return "\n".join(lines)


def save_analysis_report(result: AnalysisResult, report_text: str) -> Path:
    """Save analysis report to file.

    Args:
        result: AnalysisResult with session_id
        report_text: Formatted report text

    Returns:
        Path to saved report file

    """
    # Route through _ledger_base.reports_dir so DIVINEOS_DB env override
    # moves this directory along with the DB (2026-04-21, fresh-Claude
    # finding find-498cc7ac6b4b — the previous hardcoded path polluted
    # src/data/reports/ during test runs and caused xdist races).
    from divineos.core._ledger_base import reports_dir as _reports_dir

    reports_path = _reports_dir()
    reports_path.mkdir(parents=True, exist_ok=True)

    report_file = reports_path / f"{result.session_id}.txt"
    # Use UTF-8 encoding to handle special characters like + and x
    report_file.write_text(report_text, encoding="utf-8")

    # Conveyor belt: keep only the last N reports, prune old ones.
    _MAX_REPORTS = 50
    try:
        existing = sorted(reports_path.glob("*.txt"), key=lambda p: p.stat().st_mtime)
        if len(existing) > _MAX_REPORTS:
            for stale in existing[: len(existing) - _MAX_REPORTS]:
                stale.unlink()
    except OSError:
        pass

    return report_file
