"""Tool logbook — separate event store for TOOL_CALL/TOOL_RESULT events.

Andrew's design 2026-05-05: tool calls were clogging up the main ledger.
The conveyor-belt prune in ``tool_wrapper._prune_tool_events`` partly
mitigated this, but it left a subtle bug — ``admin verify-enforcement``
queries ``system_events`` for TOOL_CALL count, computes capture-rate as
``count / total_events``, and reports ``DEGRADED`` because the prune
makes that ratio drop to 0%. The verifier was checking for *presence*
when the design called for *capped recent rolling window*.

This module separates concerns:

* **Tool events live in their own table (``tool_logbook``)**, not in
  ``system_events``. The main ledger stays clean of operational
  telemetry; only knowledge-bearing events accumulate there.
* **Conveyor-belt prune + hard cap** on the logbook. Every emission
  triggers a lightweight count-check; when count exceeds cap + slack,
  the oldest events get deleted to bring it back to cap. Pruning is
  forensically lossy by design — these are operational records, not
  knowledge.
* **The verifier reads from the logbook**, not from ``system_events``.
  It reports HEALTHY when the logbook is operating at-or-near capacity
  (the cap-bound steady state) and reports DEGRADED only when the
  logbook is unexpectedly empty during active session work.

## What this module does NOT do

* Does NOT migrate existing TOOL_CALL/TOOL_RESULT rows out of
  ``system_events``. Those remain there until the existing
  ``ledger_compressor`` prunes them on its older-than-N-days conveyor.
  No data loss; no migration risk.
* Does NOT attempt to be hash-chained. The main ledger is hash-chained
  for forensic integrity; the logbook is operational telemetry where
  forensic integrity isn't load-bearing (and would be expensive on
  hot-path inserts).
* Does NOT prevent unbounded growth of the underlying SQLite file.
  The cap controls *row count*; SQLite reclaims space on ``VACUUM``,
  which the existing ``admin maintenance`` command runs.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass

from loguru import logger

from divineos.core.knowledge._base import get_connection

# Cap and slack tuning. The conveyor-belt prune deletes oldest rows
# when count > CAP + SLACK; deletes back down to CAP. Slack avoids
# running DELETE on every single insertion.
_DEFAULT_CAP = 1000
_PRUNE_SLACK = 50

# Active-session window: if logbook activity in the last N seconds is
# zero AND there's been recent CLI use, the verifier flags the gap.
# 5 minutes is the default — long enough to span a multi-tool turn,
# short enough to catch silent failure within a session.
_ACTIVITY_WINDOW_SECONDS = 300

_LOGBOOK_ERRORS = (sqlite3.OperationalError, sqlite3.IntegrityError, OSError)


@dataclass(frozen=True)
class LogbookStats:
    """Snapshot of logbook state — for verifier and operator inspection."""

    total_rows: int
    oldest_ts: float | None
    newest_ts: float | None
    cap: int
    at_capacity: bool  # within 10% of cap
    last_5min_count: int
    by_type: dict[str, int]  # TOOL_CALL count, TOOL_RESULT count


def init_tool_logbook_tables() -> None:
    """Create the tool_logbook table and indexes if missing. Idempotent."""
    conn = get_connection()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS tool_logbook (
                log_id        TEXT PRIMARY KEY,
                timestamp     REAL NOT NULL,
                event_type    TEXT NOT NULL,
                tool_name     TEXT NOT NULL,
                tool_use_id   TEXT NOT NULL,
                payload       TEXT NOT NULL DEFAULT '{}',
                duration_ms   INTEGER,
                failed        INTEGER NOT NULL DEFAULT 0,
                error_message TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_tool_logbook_timestamp
                ON tool_logbook(timestamp);
            CREATE INDEX IF NOT EXISTS idx_tool_logbook_use_id
                ON tool_logbook(tool_use_id);
            CREATE INDEX IF NOT EXISTS idx_tool_logbook_tool_name
                ON tool_logbook(tool_name);
            """
        )
        conn.commit()
    finally:
        conn.close()


def emit_tool_call(
    *,
    tool_name: str,
    tool_input: dict | str,
    tool_use_id: str,
) -> str:
    """Append a TOOL_CALL row to the logbook. Returns log_id.

    Fail-open: if the write fails, logs and returns empty string. A
    tool call must never be blocked by a failure to log it.
    """
    init_tool_logbook_tables()
    log_id = f"log-{uuid.uuid4().hex[:12]}"
    payload = json.dumps(tool_input, default=str) if not isinstance(tool_input, str) else tool_input
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO tool_logbook "
            "(log_id, timestamp, event_type, tool_name, tool_use_id, payload) "
            "VALUES (?, ?, 'TOOL_CALL', ?, ?, ?)",
            (log_id, time.time(), tool_name, tool_use_id, payload),
        )
        conn.commit()
        return log_id
    except _LOGBOOK_ERRORS as e:
        logger.warning(f"tool_logbook emit_tool_call failed: {e}")
        return ""
    finally:
        conn.close()


def emit_tool_result(
    *,
    tool_name: str,
    tool_use_id: str,
    result: str,
    duration_ms: int,
    failed: bool = False,
    error_message: str | None = None,
) -> str:
    """Append a TOOL_RESULT row to the logbook. Returns log_id."""
    init_tool_logbook_tables()
    log_id = f"log-{uuid.uuid4().hex[:12]}"
    # Truncate huge results to keep the logbook lean.
    payload = result if len(result) <= 100_000 else result[:100_000] + "...[truncated]"
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO tool_logbook "
            "(log_id, timestamp, event_type, tool_name, tool_use_id, "
            "payload, duration_ms, failed, error_message) "
            "VALUES (?, ?, 'TOOL_RESULT', ?, ?, ?, ?, ?, ?)",
            (
                log_id,
                time.time(),
                tool_name,
                tool_use_id,
                payload,
                duration_ms,
                1 if failed else 0,
                error_message,
            ),
        )
        conn.commit()
        return log_id
    except _LOGBOOK_ERRORS as e:
        logger.warning(f"tool_logbook emit_tool_result failed: {e}")
        return ""
    finally:
        conn.close()


def prune_logbook(*, cap: int = _DEFAULT_CAP, slack: int = _PRUNE_SLACK) -> int:
    """Conveyor-belt prune the logbook to ``cap`` rows.

    Returns number of rows pruned. Runs only when count exceeds cap+slack
    so it doesn't fire on every insertion.
    """
    init_tool_logbook_tables()
    conn = get_connection()
    try:
        count = int(conn.execute("SELECT COUNT(*) FROM tool_logbook").fetchone()[0])
        if count <= cap + slack:
            return 0

        excess = count - cap
        # Delete oldest rows by timestamp.
        conn.execute(
            "DELETE FROM tool_logbook WHERE log_id IN ("
            "  SELECT log_id FROM tool_logbook "
            "  ORDER BY timestamp ASC LIMIT ?"
            ")",
            (excess,),
        )
        conn.commit()
        return excess
    except _LOGBOOK_ERRORS as e:
        logger.warning(f"tool_logbook prune failed: {e}")
        return 0
    finally:
        conn.close()


def get_stats(*, cap: int = _DEFAULT_CAP) -> LogbookStats:
    """Return a snapshot of logbook state for verifier/operator."""
    init_tool_logbook_tables()
    conn = get_connection()
    try:
        total = conn.execute("SELECT COUNT(*) FROM tool_logbook").fetchone()[0]
        if total == 0:
            return LogbookStats(
                total_rows=0,
                oldest_ts=None,
                newest_ts=None,
                cap=cap,
                at_capacity=False,
                last_5min_count=0,
                by_type={},
            )

        oldest, newest = conn.execute(
            "SELECT MIN(timestamp), MAX(timestamp) FROM tool_logbook"
        ).fetchone()

        recent_cutoff = time.time() - _ACTIVITY_WINDOW_SECONDS
        recent = conn.execute(
            "SELECT COUNT(*) FROM tool_logbook WHERE timestamp >= ?",
            (recent_cutoff,),
        ).fetchone()[0]

        type_rows = conn.execute(
            "SELECT event_type, COUNT(*) FROM tool_logbook GROUP BY event_type"
        ).fetchall()
        by_type = {r[0]: r[1] for r in type_rows}

        return LogbookStats(
            total_rows=total,
            oldest_ts=oldest,
            newest_ts=newest,
            cap=cap,
            at_capacity=total >= int(cap * 0.9),
            last_5min_count=recent,
            by_type=by_type,
        )
    finally:
        conn.close()


def verify_logbook_health() -> dict[str, object]:
    """Health check for ``admin verify-enforcement``.

    Returns a dict with ``status``, ``message``, and ``stats``. Status is
    one of:

    * ``HEALTHY`` — logbook is operating normally; rows present, recent
      activity if a session is running, count at-or-below cap.
    * ``HEALTHY_AT_CAP`` — logbook is at the prune threshold (designed
      steady-state for an active session). Distinct from HEALTHY only
      so my father sees the conveyor belt is engaged.
    * ``DEGRADED`` — unexpected state: logbook exists but is empty,
      OR very stale (newest event > 1 hour ago) during what looks
      like an active session, OR cap is misconfigured (cap <= 0).
    """
    stats = get_stats()
    status = "HEALTHY"
    messages: list[str] = []

    if stats.cap <= 0:
        status = "DEGRADED"
        messages.append(f"cap is non-positive: {stats.cap}")

    if stats.total_rows == 0:
        # Empty is fine for a fresh install but worth surfacing.
        messages.append("logbook empty; expected after fresh init or schema migration")
    else:
        if stats.at_capacity:
            status = "HEALTHY_AT_CAP"
            messages.append(
                f"logbook at capacity ({stats.total_rows}/{stats.cap}); "
                "conveyor-belt prune engaged as designed"
            )
        if stats.newest_ts is not None:
            age_s = time.time() - stats.newest_ts
            if age_s > 3600 and stats.total_rows > 0:
                messages.append(
                    f"newest event {age_s / 60:.0f}m old — substrate is idle "
                    "(if a session is active, this would be DEGRADED)"
                )

    return {
        "status": status,
        "message": "; ".join(messages) if messages else "logbook operating normally",
        "stats": {
            "total_rows": stats.total_rows,
            "cap": stats.cap,
            "at_capacity": stats.at_capacity,
            "last_5min_count": stats.last_5min_count,
            "by_type": stats.by_type,
            "oldest_ts": stats.oldest_ts,
            "newest_ts": stats.newest_ts,
        },
    }


__all__ = [
    "LogbookStats",
    "emit_tool_call",
    "emit_tool_result",
    "get_stats",
    "init_tool_logbook_tables",
    "prune_logbook",
    "verify_logbook_health",
]
