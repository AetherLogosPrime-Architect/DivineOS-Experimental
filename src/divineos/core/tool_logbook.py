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


# Databases this process has already initialised, keyed by resolved path.
# KEYED ON THE DATABASE, NOT THE PROCESS (2026-09-01). A bare boolean would
# make a second database -- every test that points DIVINEOS_HOME somewhere new
# -- skip creation and fail far away, as a missing table in somebody else's
# test. The unit here is the database; the process is the wrong one.
_INITIALISED_DBS: set[str] = set()


def init_tool_logbook_tables(*, force: bool = False) -> None:
    """Create the tool_logbook table and indexes if missing. Idempotent.

    ONCE PER DATABASE, NOT ONCE PER WRITE (2026-09-01). This ran on every
    emit_tool_call: a fresh connection, a CREATE TABLE and three CREATE INDEX
    statements, a commit and a close -- before the caller opened a SECOND
    connection to do the actual insert.

    Measured: 4.37 ms per emit on an idle machine, 0.97 ms of it here. Twenty-two
    percent of the cost of every tool call this substrate has logged since July,
    spent re-declaring a table that already exists.

    It surfaced as a CI timeout rather than a failure. A capacity test writes a
    thousand rows through this path and had been sitting a few seconds under its
    own thirty-second limit, passing on quiet runners and dying on a busy one.
    Raising that limit was the cheap repair and would have left the cost in
    place and the test at the edge of a larger number.

    ``force`` re-runs the schema work regardless of the memo. The write path
    uses it to repair a table that has gone missing since -- remembering that we
    created something is not the same as it being there now, and a memo that
    trusts its own memory over the database turns a recoverable state into a
    permanent one.
    """
    from divineos.core import _ledger_base

    try:
        key = str(_ledger_base._get_db_path())
    except Exception:  # noqa: BLE001 - path resolution must never block logging
        key = ""
    if not force and key and key in _INITIALISED_DBS:
        return

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
        if key:
            _INITIALISED_DBS.add(key)
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
    except sqlite3.OperationalError as e:
        # The memo says we created the table; the database says otherwise.
        # Remembering that we made a thing is not the same as it being there,
        # so repair once and retry rather than letting a recoverable absence
        # become permanent for the life of the process.
        if "no such table" not in str(e).lower():
            logger.warning(f"tool_logbook emit_tool_call failed: {e}")
            return ""
        conn.close()
        init_tool_logbook_tables(force=True)
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
        except _LOGBOOK_ERRORS as retry_error:
            logger.warning(f"tool_logbook emit_tool_call failed after repair: {retry_error}")
            return ""
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


def get_recent_events(
    *,
    since_ts: float,
    now_ts: float | None = None,
    tool_names: frozenset[str] | set[str] | tuple[str, ...] | None = None,
    event_type: str = "TOOL_CALL",
    limit: int = 500,
) -> list[dict]:
    """Return recent logbook events, newest first, filtered to a time window.

    Fixes F92 (Aletheia 2026-07-27): callers wanting to know whether a
    Grep/Read/Bash happened in a recent window (e.g. the verify-before-
    build gate's consult-check) must query THIS store, not the main
    ledger. Since the 2026-05-05 store split, TOOL_CALL events are
    written to ``tool_logbook`` by design and the main ``system_events``
    ledger receives none — a caller querying ``ledger.get_events`` for
    TOOL_CALL activity gets structurally-empty results and its gate
    becomes unsatisfiable. Empirical (2026-07-27): main ledger 0
    TOOL_CALL last 24h; tool_logbook 282.

    Args:
        since_ts: unix timestamp — lower bound (inclusive) on event
            timestamp.
        now_ts: unix timestamp — upper bound (inclusive). Defaults to
            ``time.time()`` at call time. Explicit param for callers
            that pre-compute ``now`` for consistency across a check.
        tool_names: optional filter to a specific set of tool names
            (e.g. ``{"Grep", "Read", "Glob"}``). ``None`` returns all.
        event_type: ``"TOOL_CALL"`` (default) or ``"TOOL_RESULT"``.
        limit: cap on rows returned. Default 500 — matches the shape
            existing callers used against ``ledger.get_events`` so this
            is a drop-in replacement at the row-count semantics.

    Returns:
        List of dicts with keys: ``log_id``, ``timestamp``, ``event_type``,
        ``tool_name``, ``tool_use_id``, ``payload`` (parsed JSON if the
        row was JSON, else the raw string), ``duration_ms``, ``failed``,
        ``error_message``. Newest first (ORDER BY timestamp DESC).

    Fail-open: on any sqlite error the function returns ``[]`` — callers
    that use this for gate-decisions should treat empty-list-under-error
    as unknown and default to the safe posture (typically allow).
    """
    if now_ts is None:
        now_ts = time.time()
    init_tool_logbook_tables()
    conn = get_connection()
    try:
        sql = (
            "SELECT log_id, timestamp, event_type, tool_name, tool_use_id, "
            "payload, duration_ms, failed, error_message "
            "FROM tool_logbook "
            "WHERE event_type = ? AND timestamp >= ? AND timestamp <= ? "
        )
        params: list = [event_type, since_ts, now_ts]
        if tool_names:
            names_list = list(tool_names)
            placeholders = ",".join("?" for _ in names_list)
            sql += f"AND tool_name IN ({placeholders}) "  # nosec B608
            params.extend(names_list)
        sql += "ORDER BY timestamp DESC LIMIT ?"
        params.append(int(limit))

        rows = conn.execute(sql, params).fetchall()
    except _LOGBOOK_ERRORS as e:
        logger.warning(f"tool_logbook get_recent_events failed: {e}")
        return []
    finally:
        conn.close()

    out: list[dict] = []
    for r in rows:
        # sqlite3 rows are index-only unless Row factory is set;
        # get_connection() returns a plain connection in this module, so
        # tuple-index the columns per the SELECT order above.
        tool_input_raw = r[5]
        if isinstance(tool_input_raw, str):
            try:
                tool_input = json.loads(tool_input_raw)
            except (ValueError, TypeError):
                tool_input = tool_input_raw
        else:
            tool_input = tool_input_raw
        # Return in ledger-event shape so existing readers that traverse
        # `ev["payload"]["tool_name"]` and `ev["payload"]["tool_input"]`
        # work unchanged. This is drop-in compatible with the
        # `divineos.core.ledger.get_events(event_type='TOOL_CALL')` shape
        # existing verify_before_build_signal readers use.
        composed_payload = {
            "tool_name": r[3],
            "tool_use_id": r[4],
            "tool_input": tool_input,
        }
        out.append(
            {
                "log_id": r[0],
                "timestamp": r[1],
                "event_type": r[2],
                "tool_name": r[3],
                "tool_use_id": r[4],
                "payload": composed_payload,
                "duration_ms": r[6],
                "failed": bool(r[7]),
                "error_message": r[8],
            }
        )
    return out


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
