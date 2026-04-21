"""Watchmen Summary — analytics, HUD integration, unresolved tracking."""

import sqlite3
from typing import Any

from divineos.core.knowledge import _get_connection
from divineos.core.watchmen._schema import init_watchmen_tables


def get_watchmen_stats() -> dict[str, Any]:
    """Aggregate statistics across all audit findings.

    Returns counts by severity, category, status, and overall totals.
    """
    init_watchmen_tables()
    conn = _get_connection()
    try:
        total = conn.execute("SELECT COUNT(*) FROM audit_findings").fetchone()[0]
        rounds = conn.execute("SELECT COUNT(*) FROM audit_rounds").fetchone()[0]

        by_severity: dict[str, int] = {}
        for row in conn.execute(
            "SELECT severity, COUNT(*) FROM audit_findings GROUP BY severity"
        ).fetchall():
            by_severity[row[0]] = row[1]

        by_category: dict[str, int] = {}
        for row in conn.execute(
            "SELECT category, COUNT(*) FROM audit_findings GROUP BY category"
        ).fetchall():
            by_category[row[0]] = row[1]

        by_status: dict[str, int] = {}
        for row in conn.execute(
            "SELECT status, COUNT(*) FROM audit_findings GROUP BY status"
        ).fetchall():
            by_status[row[0]] = row[1]

        return {
            "total_rounds": rounds,
            "total_findings": total,
            "by_severity": by_severity,
            "by_category": by_category,
            "by_status": by_status,
            "open_count": by_status.get("OPEN", 0),
            "resolved_count": by_status.get("RESOLVED", 0),
        }
    except sqlite3.OperationalError:
        return {
            "total_rounds": 0,
            "total_findings": 0,
            "by_severity": {},
            "by_category": {},
            "by_status": {},
            "open_count": 0,
            "resolved_count": 0,
        }
    finally:
        conn.close()


def unresolved_findings(limit: int = 10) -> list[dict[str, Any]]:
    """Get unresolved findings ordered by severity (CRITICAL first).

    Used by the briefing and HUD to surface what still needs attention.
    """
    init_watchmen_tables()
    severity_order = (
        "CASE severity "
        "WHEN 'CRITICAL' THEN 1 "
        "WHEN 'HIGH' THEN 2 "
        "WHEN 'MEDIUM' THEN 3 "
        "WHEN 'LOW' THEN 4 "
        "WHEN 'INFO' THEN 5 END"
    )

    conn = _get_connection()
    try:
        rows = conn.execute(
            f"SELECT finding_id, round_id, severity, category, title, description, status "  # nosec B608
            f"FROM audit_findings "
            f"WHERE status IN ('OPEN', 'ROUTED', 'IN_PROGRESS') "
            f"ORDER BY {severity_order}, created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()

        return [
            {
                "finding_id": r[0],
                "round_id": r[1],
                "severity": r[2],
                "category": r[3],
                "title": r[4],
                "description": r[5],
                "status": r[6],
            }
            for r in rows
        ]
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()


def watchmen_loop_status() -> str:
    """Honest label for how much of the external-audit loop is mechanically closed.

    Updated manually as loop-closing features ship. Grok audit 2026-04-16
    named the polish-exceeds-mechanics risk; this label keeps the Watchmen
    surface honest about which parts of external validation are automatic
    vs. which still depend on a human remembering to request an audit.

    2026-04-21: the wall-clock cadence gate was replaced with the
    drift-state briefing block. Data as metric, not threshold as metric.
    """
    return (
        "Loop status: external-actor filing works; routing to "
        "knowledge/claims/lessons works; drift-state briefing surfaces "
        "operation counts since last MEDIUM+ audit (turns, code actions, "
        "rounds, open findings) so the operator decides when an audit is "
        "warranted. Blocking gate removed — data-as-metric replaces "
        "threshold-as-metric. The remaining aspirational piece: whether "
        "external audits actually alter behavior — which we're still measuring."
    )


def format_watchmen_summary() -> str:
    """One-line summary for HUD display.

    Shows count of unresolved findings by severity.
    Returns empty string if no audit data exists.
    """
    stats = get_watchmen_stats()
    if stats["total_findings"] == 0:
        return ""

    open_count = stats["open_count"]
    resolved = stats["resolved_count"]
    total = stats["total_findings"]

    if open_count == 0:
        return f"Watchmen: {total} findings, all resolved"

    # Show open findings by severity
    parts = []
    # Only count unresolved for severity breakdown
    unresolved = unresolved_findings(limit=100)
    sev_counts: dict[str, int] = {}
    for f in unresolved:
        sev_counts[f["severity"]] = sev_counts.get(f["severity"], 0) + 1

    for s in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
        count = sev_counts.get(s, 0)
        if count > 0:
            parts.append(f"{count} {s.lower()}")

    detail = ", ".join(parts) if parts else f"{open_count} open"
    return f"Watchmen: {detail} ({resolved}/{total} resolved)"
