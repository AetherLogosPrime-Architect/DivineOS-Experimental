"""ELMO — Event Ledger Memory Optimizer.

Compresses the append-only ledger by archiving high-volume noise events
(TOOL_CALL, TOOL_RESULT, AGENT_PATTERN*) older than a retention window.

The ledger uses independent per-event hashes (no hash chain), so old events
can be safely removed without breaking integrity of remaining events.

Compression strategy:
1. Count events by type and age
2. Summarize high-volume events into a single LEDGER_COMPACTION event
3. Delete the originals
4. VACUUM the database

Meaningful events (USER_INPUT, SESSION_END, CLARITY_*, SUPERSESSION, etc.)
are NEVER deleted.
"""

import json
import time
from typing import Any

from loguru import logger

from divineos.core._ledger_base import _get_db_path, compute_hash, get_connection
from divineos.core.constants import (
    LEDGER_MAX_SIZE_GB,
    LEDGER_WARNING_PERCENT,
    SECONDS_PER_DAY,
    TIME_LEDGER_EMERGENCY_RETENTION_DAYS,
    TIME_LEDGER_RETENTION_DAYS,
)

# Events that are safe to archive after the retention window.
# These are high-volume bookkeeping — their content is not needed
# for briefings, knowledge, or session continuity.
_COMPRESSIBLE_TYPES = frozenset(
    {
        "TOOL_CALL",
        "TOOL_RESULT",
        "AGENT_PATTERN",
        "AGENT_PATTERN_UPDATE",
        "AGENT_WORK",
        "AGENT_WORK_OUTCOME",
        "AGENT_LEARNING_AUDIT",
        "AGENT_CONTEXT_COMPRESSION",
        # Item 6: allow-events are frequent (every gated tool call)
        # but carry no per-event forensic weight. Item 8 uses block/
        # allow *ratios* which survive pruning — the ratio is
        # computed over the live-window before compression runs.
        # FIRED events are deliberately NOT in this set: they are
        # forensic records of enforcement and must persist for audit.
        # Follow-up claim df5b3113: guardrail this file post-Item-6
        # so adding FIRED here later requires multi-party review.
        "COMPASS_RUDDER_ALLOW",
    }
)

# Default retention: keep 7 days of everything, compress older.
_DEFAULT_RETENTION_DAYS = TIME_LEDGER_RETENTION_DAYS


def analyze_ledger() -> dict[str, Any]:
    """Analyze the ledger for compression opportunities.

    Returns stats about event counts, sizes, and what would be compressed.
    """
    conn = get_connection()
    try:
        # Total size
        total = conn.execute("SELECT COUNT(*) FROM system_events").fetchone()[0]

        # By type
        rows = conn.execute(
            "SELECT event_type, COUNT(*) FROM system_events GROUP BY event_type"
        ).fetchall()
        by_type = {r[0]: r[1] for r in rows}

        # Compressible events older than retention window
        cutoff = time.time() - (_DEFAULT_RETENTION_DAYS * SECONDS_PER_DAY)
        placeholders = ",".join("?" for _ in _COMPRESSIBLE_TYPES)
        compressible = conn.execute(
            f"SELECT COUNT(*) FROM system_events "  # nosec B608: table/column names from module constants; values parameterized
            f"WHERE event_type IN ({placeholders}) AND timestamp < ?",
            (*_COMPRESSIBLE_TYPES, cutoff),
        ).fetchone()[0]

        # Estimate space: average payload size * compressible count
        avg_size_row = conn.execute(
            f"SELECT AVG(LENGTH(payload)) FROM system_events WHERE event_type IN ({placeholders})",  # nosec B608: table/column names from module constants; values parameterized
            (*_COMPRESSIBLE_TYPES,),
        ).fetchone()
        avg_payload_size = avg_size_row[0] if avg_size_row[0] else 0

        return {
            "total_events": total,
            "by_type": by_type,
            "compressible_count": compressible,
            "estimated_savings_mb": round((compressible * avg_payload_size) / (1024 * 1024), 1),
            "retention_days": _DEFAULT_RETENTION_DAYS,
            "meaningful_kept": total - compressible,
        }
    finally:
        conn.close()


def compress_ledger(
    retention_days: int = _DEFAULT_RETENTION_DAYS,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Compress the ledger by archiving old high-volume events.

    Args:
        retention_days: Keep events newer than this many days.
        dry_run: If True, report what would happen without deleting.

    Returns:
        Summary of compression results.
    """
    cutoff = time.time() - (retention_days * SECONDS_PER_DAY)
    conn = get_connection()
    try:
        # Count what we're about to compress, grouped by type
        placeholders = ",".join("?" for _ in _COMPRESSIBLE_TYPES)
        rows = conn.execute(
            f"SELECT event_type, COUNT(*) FROM system_events "  # nosec B608: table/column names from module constants; values parameterized
            f"WHERE event_type IN ({placeholders}) AND timestamp < ? "
            f"GROUP BY event_type",
            (*_COMPRESSIBLE_TYPES, cutoff),
        ).fetchall()
        compressed_by_type = {r[0]: r[1] for r in rows}
        total_compressed = sum(compressed_by_type.values())

        if total_compressed == 0:
            return {
                "compressed": 0,
                "by_type": {},
                "dry_run": dry_run,
                "summary_event_id": None,
            }

        if dry_run:
            return {
                "compressed": total_compressed,
                "by_type": compressed_by_type,
                "dry_run": True,
                "summary_event_id": None,
            }

        # Get the time range of compressed events
        time_range = conn.execute(
            f"SELECT MIN(timestamp), MAX(timestamp) FROM system_events "  # nosec B608: table/column names from module constants; values parameterized
            f"WHERE event_type IN ({placeholders}) AND timestamp < ?",
            (*_COMPRESSIBLE_TYPES, cutoff),
        ).fetchone()

        # Create a summary compaction event before deleting
        import uuid

        event_id = str(uuid.uuid4())
        summary_payload = {
            "action": "LEDGER_COMPACTION",
            "compressed_count": total_compressed,
            "compressed_by_type": compressed_by_type,
            "time_range_start": time_range[0],
            "time_range_end": time_range[1],
            "retention_days": retention_days,
            "compressed_at": time.time(),
        }
        payload_json = json.dumps(summary_payload, sort_keys=True)
        content_hash = compute_hash(payload_json)

        conn.execute(
            "INSERT INTO system_events (event_id, timestamp, event_type, actor, payload, content_hash) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (event_id, time.time(), "LEDGER_COMPACTION", "system", payload_json, content_hash),
        )

        # Delete the compressed events
        conn.execute(
            f"DELETE FROM system_events WHERE event_type IN ({placeholders}) AND timestamp < ?",  # nosec B608: table/column names from module constants; values parameterized
            (*_COMPRESSIBLE_TYPES, cutoff),
        )
        conn.commit()

        logger.info(
            "ELMO compressed %d events (%s)",
            total_compressed,
            ", ".join(f"{k}: {v}" for k, v in compressed_by_type.items()),
        )

        return {
            "compressed": total_compressed,
            "by_type": compressed_by_type,
            "dry_run": False,
            "summary_event_id": event_id,
        }
    finally:
        conn.close()


def vacuum_ledger() -> dict[str, Any]:
    """VACUUM the ledger database to reclaim disk space.

    Should be run after compression. Returns before/after sizes.
    """
    conn = get_connection()
    try:
        # Get page count before
        page_count = conn.execute("PRAGMA page_count").fetchone()[0]
        page_size = conn.execute("PRAGMA page_size").fetchone()[0]
        size_before = page_count * page_size

        conn.execute("VACUUM")

        page_count = conn.execute("PRAGMA page_count").fetchone()[0]
        size_after = page_count * page_size

        return {
            "size_before_mb": round(size_before / (1024 * 1024), 1),
            "size_after_mb": round(size_after / (1024 * 1024), 1),
            "saved_mb": round((size_before - size_after) / (1024 * 1024), 1),
        }
    finally:
        conn.close()


# ─── Size Guard ─────────────────────────────────────────────────────


# Default max ledger size from constants.
_DEFAULT_MAX_SIZE_GB = LEDGER_MAX_SIZE_GB


def get_ledger_size_mb() -> float:
    """Get the current ledger database file size in MB."""
    db_path = _get_db_path()
    if not db_path.exists():
        return 0.0
    return db_path.stat().st_size / (1024 * 1024)


def check_ledger_size(max_size_gb: float = _DEFAULT_MAX_SIZE_GB) -> dict[str, Any]:
    """Check if ledger exceeds the size limit.

    Returns status and size info. Does NOT auto-compress — the caller decides.
    """
    size_mb = get_ledger_size_mb()
    max_mb = max_size_gb * 1024
    usage_pct = (size_mb / max_mb * 100) if max_mb > 0 else 0

    return {
        "size_mb": round(size_mb, 1),
        "max_size_gb": max_size_gb,
        "usage_percent": round(usage_pct, 1),
        "over_limit": size_mb > max_mb,
        "warning": size_mb > (max_mb * LEDGER_WARNING_PERCENT / 100),
    }


def auto_compress_if_needed(
    max_size_gb: float = _DEFAULT_MAX_SIZE_GB,
    retention_days: int = _DEFAULT_RETENTION_DAYS,
) -> dict[str, Any] | None:
    """Auto-compress and vacuum if ledger exceeds 80% of size limit.

    Returns compression result if triggered, None if not needed.
    """
    status = check_ledger_size(max_size_gb)

    if not status["warning"]:
        return None

    logger.info(
        "Ledger at %.1f MB (%.1f%% of %.0f GB limit) — auto-compressing",
        status["size_mb"],
        status["usage_percent"],
        max_size_gb,
    )

    # Aggressively compress if over limit — reduce retention
    if status["over_limit"]:
        retention_days = min(retention_days, TIME_LEDGER_EMERGENCY_RETENTION_DAYS)

    result = compress_ledger(retention_days=retention_days)
    if result["compressed"] > 0:
        vac = vacuum_ledger()
        result["vacuum"] = vac

    result["trigger"] = "over_limit" if status["over_limit"] else "warning_80pct"
    result["size_before_check_mb"] = status["size_mb"]
    return result
