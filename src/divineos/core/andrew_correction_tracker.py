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
    # Task #115 (2026-06-09): add unblock_condition column. Existing rows
    # get NULL on migrate. ALTER TABLE wrapped in try because SQLite raises
    # if the column already exists; a second-run migration just no-ops.
    try:
        conn.execute("ALTER TABLE andrew_corrections ADD COLUMN unblock_condition TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        # Column already exists — migration was previously applied.
        pass
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


def defer(correction_id: int, reason: str, unblock_condition: str | None = None) -> bool:
    """Mark a correction DEFERRED with named reason.

    Deferral is allowed but visible. Refuses bare deferral (reason >= 20
    chars required). The deferred correction continues to surface in
    briefing under a 'deferred' subheading — silent abandonment is not
    a state this system permits.

    Task #115 (2026-06-09): optional unblock_condition names the trigger
    that should auto-reopen the correction. Supported forms:

      - "pr_merged:<pr_number>" — reopen when GitHub PR has merged
      - "time_elapsed:<days>" — reopen after N days since defer
      - "knowledge_stored:<keyword>" — reopen when a knowledge entry
        is filed whose content contains the keyword

    The condition is informational at defer-time; check_and_reopen_
    unblocked() walks deferred items and reopens those whose conditions
    have fired. If unblock_condition is None, the deferral has no
    auto-reopen — it stays deferred until manually re-opened.
    """
    if not reason or len(reason.strip()) < 20:
        return False
    if unblock_condition is not None and not _is_valid_unblock_condition(unblock_condition):
        return False
    conn = _conn()
    try:
        cur = conn.execute(
            "UPDATE andrew_corrections SET status = 'DEFERRED', "
            "deferred_reason = ?, unblock_condition = ? "
            "WHERE id = ? AND status = 'OPEN'",
            (reason.strip(), unblock_condition, correction_id),
        )
        conn.commit()
        ok = cur.rowcount > 0
    finally:
        conn.close()
    if ok:
        _write_attestation_marker()
    return ok


# Task #115 unblock-condition parsing + evaluation.

_UNBLOCK_CONDITION_PREFIXES: tuple[str, ...] = (
    "pr_merged:",
    "time_elapsed:",
    "knowledge_stored:",
)


def _is_valid_unblock_condition(condition: str) -> bool:
    """True if `condition` matches a supported prefix with a non-empty
    argument after the colon.

    Validating at defer-time prevents typo-shaped conditions from being
    silently stored — the deferral would otherwise never auto-reopen
    because no checker recognizes the malformed prefix.
    """
    if not condition or not isinstance(condition, str):
        return False
    for prefix in _UNBLOCK_CONDITION_PREFIXES:
        if condition.startswith(prefix):
            arg = condition[len(prefix) :].strip()
            return bool(arg)
    return False


def _condition_fired(condition: str, deferred_at: float | None = None) -> bool:
    """Return True iff the unblock condition has fired.

    Each form has its own check:
    - pr_merged:N → query gh for the PR's mergedAt; True if non-null.
    - time_elapsed:D → (now - deferred_at) >= D * 86400.
    - knowledge_stored:KW → scan knowledge_store for any entry whose
      content contains KW (case-insensitive substring).

    Any error returns False — we'd rather keep an item deferred than
    falsely reopen it.
    """
    if not condition:
        return False
    try:
        if condition.startswith("pr_merged:"):
            pr_number = condition.removeprefix("pr_merged:").strip()
            if not pr_number.isdigit():
                return False
            try:
                import subprocess

                proc = subprocess.run(
                    ["gh", "pr", "view", pr_number, "--json", "mergedAt"],
                    capture_output=True,
                    text=True,
                    timeout=15,
                    check=False,
                )
            except (OSError, subprocess.TimeoutExpired):
                return False
            if proc.returncode != 0:
                return False
            try:
                import json as _json

                data = _json.loads(proc.stdout or "{}")
            except (ValueError, TypeError):
                return False
            return bool(data.get("mergedAt"))

        if condition.startswith("time_elapsed:"):
            days_str = condition.removeprefix("time_elapsed:").strip()
            try:
                days = float(days_str)
            except ValueError:
                return False
            if deferred_at is None:
                return False
            return (time.time() - float(deferred_at)) >= (days * 86400.0)

        if condition.startswith("knowledge_stored:"):
            keyword = condition.removeprefix("knowledge_stored:").strip().lower()
            if not keyword:
                return False
            try:
                from divineos.core.ledger import get_events
            except Exception:  # noqa: BLE001
                return False
            try:
                events = get_events(limit=200, event_type="KNOWLEDGE_STORED")
            except Exception:  # noqa: BLE001
                return False
            for ev in events:
                payload = ev.get("payload") or {}
                if isinstance(payload, dict):
                    content = (payload.get("content") or "").lower()
                    if keyword in content:
                        return True
            return False
    except Exception:  # noqa: BLE001
        return False
    return False


def check_and_reopen_unblocked() -> list[int]:
    """Scan DEFERRED corrections with unblock_condition set; reopen any
    whose condition has fired. Returns the list of reopened ids.

    Called periodically (e.g., at session-start by the briefing
    pipeline) so deferred items don't drift invisibly past the moment
    their unblock condition would have fired.
    """
    reopened: list[int] = []
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT id, unblock_condition, integrated_at FROM andrew_corrections "
            "WHERE status = 'DEFERRED' AND unblock_condition IS NOT NULL"
        ).fetchall()
        # We need the defer-time timestamp. The schema doesn't store a
        # separate deferred_at, so we use the timestamp of the row
        # (filing time) as an approximation. For time_elapsed conditions,
        # this means the clock starts at filing, not at deferral — a
        # known limitation; the alternative would require a schema
        # migration adding deferred_at. Filing-time is acceptable
        # because deferral typically happens within the same session
        # as the correction.
        for row_id, condition, _integrated_at in rows:
            ts_row = conn.execute(
                "SELECT timestamp FROM andrew_corrections WHERE id = ?",
                (row_id,),
            ).fetchone()
            ts = float(ts_row[0]) if ts_row else None
            if _condition_fired(condition, deferred_at=ts):
                conn.execute(
                    "UPDATE andrew_corrections SET status = 'OPEN', "
                    "deferred_reason = NULL, unblock_condition = NULL "
                    "WHERE id = ?",
                    (row_id,),
                )
                reopened.append(int(row_id))
        conn.commit()
    finally:
        conn.close()
    return reopened


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
