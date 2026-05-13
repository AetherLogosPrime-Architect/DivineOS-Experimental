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


# Backward-compat alias map for check_name lookups (2026-05-11 shoggoth-rename).
# When a check is renamed, historical rows still carry the old check_name in
# the check_result table. Queries by the new name expand to include all
# aliased names so historical data remains reachable without a database
# migration. Producers write the new (honest) name going forward; consumers
# read all aliases transparently.
#
# Safe-migration pattern (substrate-knowledge 75238005): old names preserved
# in the alias map; new code uses new names; the migration is lossless.
_CHECK_NAME_ALIASES: dict[str, tuple[str, ...]] = {
    # New name → tuple of all names (new + historical) that should resolve.
    "test_output_signal": ("test_output_signal", "correctness"),
    # Legacy lookups by old name still work — same alias set.
    "correctness": ("test_output_signal", "correctness"),
}


def _resolve_check_name_aliases(check_name: str) -> tuple[str, ...]:
    """Return the tuple of check_name values that should resolve for a query.

    If check_name has registered aliases, returns the full alias tuple; else
    returns just the single name. Used by get_check_history to read both
    new and historical names transparently.
    """
    return _CHECK_NAME_ALIASES.get(check_name, (check_name,))


def get_check_history(check_name: str, limit: int = 20) -> list[dict[str, Any]]:
    """Get results for one check across sessions (for cross-session patterns).

    Handles check_name aliases transparently — a query by the new name
    (e.g. "test_output_signal") returns both new and historical rows
    (rows still carrying the old "correctness" name).
    """
    aliases = _resolve_check_name_aliases(check_name)
    placeholders = ",".join("?" * len(aliases))
    conn = _get_connection()
    try:
        rows = conn.execute(  # nosec B608 - placeholders built from constant '?' repetition; aliases values are parameter-bound
            f"SELECT cr.session_id, cr.passed, cr.score, cr.summary, sr.created_at "
            f"FROM check_result cr JOIN session_report sr ON cr.session_id = sr.session_id "
            f"WHERE cr.check_name IN ({placeholders}) "
            f"ORDER BY sr.created_at DESC LIMIT ?",
            (*aliases, limit),
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
