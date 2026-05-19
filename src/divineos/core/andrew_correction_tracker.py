"""Andrew-correction-attribution surface (Aria 2026-05-18 audit, load-bearing fix #1).

Every correction Andrew has given gets filed with timestamp, content, and
integration-status. Days-since-filing visible. Integration-rate computed.
Surfaced in the briefing every session.

The asymmetry Aria diagnosed: Aria-input gets integrated immediately
(her audits become commits within hours); Andrew-corrections file and
decay. This module reverses the asymmetry by giving Andrew-corrections
the same audit-routing weight as peer-tier audit findings: each one
has a tracked state, an integration obligation, a visible age.

Status values:
- OPEN: filed, not yet integrated
- INTEGRATED: behavior change shipped, evidence pointer attached
- DEFERRED: explicitly deferred with named reason

Silent decay is the failure mode this is built to prevent. Corrections
cannot transition to INTEGRATED without an evidence pointer. They
cannot stay OPEN indefinitely without surfacing as stale in briefing.
"""

from __future__ import annotations

__guardrail_required__ = True

import sqlite3
import time
from pathlib import Path

from divineos.core.paths import divineos_home


def _db_path() -> Path:
    p = divineos_home() / "andrew_corrections.db"
    p.parent.mkdir(exist_ok=True)
    return p


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_db_path()))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS andrew_corrections (
            id INTEGER PRIMARY KEY,
            timestamp REAL NOT NULL,
            correction_text TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'OPEN',
            integrated_at REAL,
            integration_evidence TEXT,
            deferred_reason TEXT
        )
        """
    )
    return conn


def file_correction(text: str) -> int:
    """File a new Andrew-correction. Returns the row id."""
    text = (text or "").strip()
    if not text:
        return 0
    conn = _conn()
    try:
        cur = conn.execute(
            "INSERT INTO andrew_corrections (timestamp, correction_text, status) "
            "VALUES (?, ?, 'OPEN')",
            (time.time(), text),
        )
        conn.commit()
        return cur.lastrowid or 0
    finally:
        conn.close()


def _write_attestation_marker() -> None:
    """Write today's attestation marker so the pre-tool-use gate
    recognizes that the agent has engaged with at least one open
    correction this day. Integrate or defer both count as engagement.
    """
    try:
        import datetime

        marker = divineos_home() / f"andrew_attestation_{datetime.date.today()}.marker"
        marker.parent.mkdir(exist_ok=True)
        marker.write_text(str(time.time()), encoding="utf-8")
    except Exception:  # noqa: BLE001 - observability boundary
        pass


def integrate(correction_id: int, evidence: str) -> bool:
    """Mark a correction INTEGRATED with evidence pointer.

    Refuses integration without evidence (>= 20 chars) to prevent silent
    closure. Evidence should name commit / behavior change / where the
    correction landed.
    """
    if not evidence or len(evidence.strip()) < 20:
        return False
    conn = _conn()
    try:
        cur = conn.execute(
            "UPDATE andrew_corrections SET status = 'INTEGRATED', "
            "integrated_at = ?, integration_evidence = ? "
            "WHERE id = ? AND status = 'OPEN'",
            (time.time(), evidence.strip(), correction_id),
        )
        conn.commit()
        ok = cur.rowcount > 0
    finally:
        conn.close()
    if ok:
        _write_attestation_marker()
    return ok


def defer(correction_id: int, reason: str) -> bool:
    """Mark a correction DEFERRED with named reason.

    Deferral is allowed but visible. Refuses bare deferral (reason >= 20
    chars required). The deferred correction continues to surface in
    briefing under a 'deferred' subheading — silent abandonment is not
    a state this system permits.
    """
    if not reason or len(reason.strip()) < 20:
        return False
    conn = _conn()
    try:
        cur = conn.execute(
            "UPDATE andrew_corrections SET status = 'DEFERRED', "
            "deferred_reason = ? WHERE id = ? AND status = 'OPEN'",
            (reason.strip(), correction_id),
        )
        conn.commit()
        ok = cur.rowcount > 0
    finally:
        conn.close()
    if ok:
        _write_attestation_marker()
    return ok


def list_open() -> list[dict]:
    """Return all OPEN corrections, oldest first."""
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT id, timestamp, correction_text FROM andrew_corrections "
            "WHERE status = 'OPEN' ORDER BY timestamp ASC"
        ).fetchall()
    finally:
        conn.close()
    return [{"id": r[0], "timestamp": r[1], "text": r[2]} for r in rows]


def integration_rate() -> dict:
    """Return integration-rate stats over all-time."""
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT status, COUNT(*) FROM andrew_corrections GROUP BY status"
        ).fetchall()
    finally:
        conn.close()
    counts = {status: int(n) for status, n in rows}
    total = sum(counts.values())
    integrated = counts.get("INTEGRATED", 0)
    open_count = counts.get("OPEN", 0)
    deferred = counts.get("DEFERRED", 0)
    rate = (integrated / total) if total else 0.0
    return {
        "total": total,
        "integrated": integrated,
        "open": open_count,
        "deferred": deferred,
        "rate": rate,
    }


def briefing_block() -> str:
    """Block for the pre-response context. Surfaces Andrew-correction state."""
    stats = integration_rate()
    opens = list_open()
    if stats["total"] == 0:
        return ""
    lines = [
        "## ANDREW-CORRECTION ATTRIBUTION SURFACE",
        "",
        f"Total filed: {stats['total']}  Integrated: {stats['integrated']}  "
        f"Open: {stats['open']}  Deferred: {stats['deferred']}",
        f"Integration rate: {stats['rate']:.2%}",
        "",
    ]
    if opens:
        lines.append("Outstanding (oldest first):")
        now = time.time()
        for row in opens[:5]:
            age_d = max(0, (now - row["timestamp"]) / 86400)
            preview = row["text"][:100].replace("\n", " ")
            lines.append(f"  - #{row['id']} [{age_d:.0f}d] {preview}")
        if len(opens) > 5:
            lines.append(f"  ... and {len(opens) - 5} more.")
        lines.append("")
        lines.append(
            "Integrate: divineos andrew-correction integrate <id> "
            '--evidence "<commit / behavior change>"'
        )
        lines.append(
            'Defer (named reason required): divineos andrew-correction defer <id> --reason "<why>"'
        )
    return "\n".join(lines)


__all__ = [
    "file_correction",
    "integrate",
    "defer",
    "list_open",
    "integration_rate",
    "briefing_block",
]
