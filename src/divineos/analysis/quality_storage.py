"""Quality Storage — Persistence layer for session quality reports.

Stores and retrieves SessionReport and CheckResult data from SQLite.
"""

import json
from typing import Any

from divineos.analysis.record_extraction import (
    CheckResult,
    SessionReport,
    _get_connection,
)


def store_report(report: SessionReport) -> None:
    """Store a complete report and its check results."""
    conn = _get_connection()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO session_report (session_id, created_at, report_text, evidence_hash) VALUES (?, ?, ?, ?)",
            (report.session_id, report.created_at, report.report_text, report.evidence_hash),
        )
        # Remove old check results for this session (re-run scenario)
        conn.execute("DELETE FROM check_result WHERE session_id = ?", (report.session_id,))
        for check in report.checks:
            evidence_json = json.dumps(check.evidence, sort_keys=True, default=str)
            conn.execute(
                "INSERT INTO check_result (session_id, check_name, passed, score, evidence_hash, summary, raw_evidence) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    report.session_id,
                    check.check_name,
                    check.passed,
                    check.score,
                    check.evidence_hash,
                    check.summary,
                    evidence_json,
                ),
            )
        conn.commit()
    finally:
        conn.close()


def get_report(session_id: str) -> SessionReport | None:
    """Retrieve a stored report."""
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT session_id, created_at, report_text, evidence_hash FROM session_report WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        if not row:
            return None

        report = SessionReport(
            session_id=row[0],
            created_at=row[1],
            report_text=row[2],
            evidence_hash=row[3],
        )

        check_rows = conn.execute(
            "SELECT check_name, passed, score, evidence_hash, summary, raw_evidence FROM check_result WHERE session_id = ? ORDER BY id",
            (session_id,),
        ).fetchall()

        for cr in check_rows:
            report.checks.append(
                CheckResult(
                    check_name=cr[0],
                    passed=cr[1],
                    score=cr[2],
                    evidence_hash=cr[3],
                    summary=cr[4],
                    evidence=json.loads(cr[5]),
                ),
            )

        return report
    finally:
        conn.close()


def get_check_history(check_name: str, limit: int = 20) -> list[dict[str, Any]]:
    """Get results for one check across sessions (for cross-session patterns)."""
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT cr.session_id, cr.passed, cr.score, cr.summary, sr.created_at "
            "FROM check_result cr JOIN session_report sr ON cr.session_id = sr.session_id "
            "WHERE cr.check_name = ? ORDER BY sr.created_at DESC LIMIT ?",
            (check_name, limit),
        ).fetchall()
        return [
            {
                "session_id": r[0],
                "passed": r[1],
                "score": r[2],
                "summary": r[3],
                "created_at": r[4],
            }
            for r in rows
        ]
    finally:
        conn.close()
