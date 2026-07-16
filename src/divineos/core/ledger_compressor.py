"""ELMO — Event Ledger Memory Optimizer.

Compresses the append-only ledger by archiving high-volume noise events
(TOOL_CALL, TOOL_RESULT, AGENT_PATTERN*) older than a retention window.

The ledger uses a per-event content_hash AND a sequential hash chain
(prior_hash / chain_hash — see ledger.py module docstring). Compression
deletes rows in the middle of that chain, which orphans every surviving
row whose prior_hash pointed at a now-deleted predecessor.

Marc audit finding 2026-07-16 named the shape: prior docstring here
claimed "no hash chain, safe to delete" — false invariant. The schema
HAS the columns; the append path DOES populate them; every extract
cycle silently broke the chain-integrity property for the tamper-
evidence layer. Damage measured on Aria's ledger 2026-07-16: 7730/7730
surviving events orphaned in the tamper-evidence sense (per-row
content_hash still verifies; chain-completeness does not).

Compression strategy (post-fix):
1. Count events by type and age
2. Summarize high-volume events into a single LEDGER_COMPACTION event
3. Delete the originals
4. Repair the chain for surviving rows whose predecessors were deleted
   (see _repair_chain_after_deletion) — same transaction as the delete
5. Emit LEDGER_CHAIN_REPAIRED audit event capturing pre/post orphan
   counts (auditable-repair pattern, same shape as
   LEDGER_CORRUPTION_REPAIRED in ledger_verify.py)
6. VACUUM the database

Meaningful events (USER_INPUT, SESSION_END, CLARITY_*, SUPERSESSION, etc.)
are NEVER deleted.

Interpretation A (Aria + Aether coordination 2026-07-16 letters): the
repair uses the last-good chain_hash as the implicit anchor for the
rebuilt segment, preserving the pre-deletion chain-continuity claim.
Symmetric to the doorman UNLOCK-CONTINGENT slot — the recording that
stays must be the ACTUAL recording, not a fresh made-up one.
"""

# Module-level guardrail marker — Aletheia Finding 48 class-fix
# 2026-05-14. CI test enforces marker-vs-guardrail-list consistency.
__guardrail_required__ = True


import json
import sqlite3
import time
from typing import Any

from loguru import logger

from divineos.core._ledger_base import _get_db_path, compute_hash, get_connection
from divineos.core.ledger import _CHAIN_GENESIS, _compute_chain_hash
from divineos.core.constants import (
    LEDGER_MAX_SIZE_GB,
    LEDGER_WARNING_PERCENT,
    SECONDS_PER_DAY,
    TIME_LEDGER_EMERGENCY_RETENTION_DAYS,
    TIME_LEDGER_RETENTION_DAYS,
)

# Errors this module handles during the compress-transaction rollback path.
# Broad-exception CI (test_check_broad_exceptions) requires module-level
# tuple form. Anything unexpected outside this set should propagate (raise)
# rather than silently roll back and swallow — the transaction's rollback
# is a recovery step, not a swallowing step.
_LC_ERRORS = (sqlite3.Error, OSError, TypeError, ValueError)

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


def _repair_chain_after_deletion(conn) -> dict[str, Any]:
    """Repair the hash chain after compression deletes rows in the middle.

    Interpretation A (Aria 2026-07-16 letter to Aether): find the earliest
    surviving row whose prior_hash no longer resolves to a surviving
    chain_hash (or _CHAIN_GENESIS), NULL out chain metadata from that row
    forward, and let ``backfill_chain_hashes()`` rebuild the segment. The
    implicit anchor is the last surviving row with a still-valid chain_hash
    — preserving the pre-deletion chain-continuity claim rather than
    minting a fresh genesis. Symmetric to the doorman UNLOCK-CONTINGENT
    slot (substrate cite 721ec1ec): the recording that stays must be the
    ACTUAL recording, not a fresh made-up one.

    Self-healing: on first run after this fix lands, any existing orphans
    from prior compression cycles get rebuilt too (per-row content_hash
    integrity, still intact, is the witness for the anchor row —
    Andrew 2026-07-16: "we can prove they were not tampered with").

    Called INSIDE the same transaction as ``DELETE`` in ``compress_ledger``
    (Aria 2026-07-16 letter to Aether — same-transaction locked). If the
    delete succeeds and repair fails, both roll back together, so the
    caller either sees fully-healed post-state or fully-restored pre-state.
    No silent looks-fine-isn't-wired middle ground.

    Args:
        conn: Open sqlite3 connection with an in-flight transaction.
            The caller is responsible for BEGIN and COMMIT.

    Returns:
        dict with keys:
          - ``first_orphan_rowid``: rowid of the earliest orphaned row,
            or None if no orphans found
          - ``rebuilt``: count of rows whose chain metadata was
            recomputed (0 if no orphans)
          - ``status``: ``"no_orphans"`` | ``"repaired"``
    """
    valid_hashes = {
        row[0]
        for row in conn.execute("SELECT chain_hash FROM system_events WHERE chain_hash IS NOT NULL")
    }
    valid_hashes.add(_CHAIN_GENESIS)

    first_orphan_rowid = None
    for rowid, prior_hash in conn.execute(
        "SELECT rowid, prior_hash FROM system_events "
        "WHERE prior_hash IS NOT NULL "
        "ORDER BY timestamp ASC, rowid ASC"
    ):
        if prior_hash not in valid_hashes:
            first_orphan_rowid = rowid
            break

    if first_orphan_rowid is None:
        return {
            "first_orphan_rowid": None,
            "rebuilt": 0,
            "status": "no_orphans",
        }

    conn.execute(
        "UPDATE system_events SET prior_hash = NULL, chain_hash = NULL WHERE rowid >= ?",
        (first_orphan_rowid,),
    )

    # Inline the backfill loop on the caller's connection to preserve
    # single-transaction discipline. Delegating to backfill_chain_hashes()
    # would open a second connection with its own BEGIN IMMEDIATE and
    # deadlock against the caller's outstanding write lock — the exact
    # failure mode this same-transaction design is meant to prevent.
    prior_hash = _latest_valid_chain_hash_before(conn, first_orphan_rowid)
    rebuilt = 0
    for row in conn.execute(
        "SELECT rowid, event_id, timestamp, event_type, actor, payload, content_hash "
        "FROM system_events WHERE chain_hash IS NULL "
        "ORDER BY timestamp ASC, rowid ASC"
    ).fetchall():
        rowid, event_id, ts, etype, actor, payload_json, content_hash = row
        chain_hash = _compute_chain_hash(
            prior_hash=prior_hash,
            event_id=event_id,
            timestamp=ts,
            event_type=etype,
            actor=actor,
            payload_json=payload_json,
            content_hash=content_hash,
        )
        conn.execute(
            "UPDATE system_events SET prior_hash = ?, chain_hash = ? WHERE rowid = ?",
            (prior_hash, chain_hash, rowid),
        )
        prior_hash = chain_hash
        rebuilt += 1

    return {
        "first_orphan_rowid": first_orphan_rowid,
        "rebuilt": rebuilt,
        "status": "repaired",
    }


def _latest_valid_chain_hash_before(conn, rowid: int) -> str:
    """Return the chain_hash of the newest surviving row whose rowid is
    strictly less than ``rowid`` and whose chain_hash is still populated.
    Falls back to _CHAIN_GENESIS if no such row exists (early-truncation
    case). This IS the implicit anchor for Interpretation A rebuild —
    Aria + Aether 2026-07-16 coordination locked."""
    row = conn.execute(
        "SELECT chain_hash FROM system_events "
        "WHERE rowid < ? AND chain_hash IS NOT NULL "
        "ORDER BY timestamp DESC, rowid DESC LIMIT 1",
        (rowid,),
    ).fetchone()
    if not row or not row[0]:
        return _CHAIN_GENESIS
    return str(row[0])


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

        # Same-transaction discipline (Aria + Aether coordination 2026-07-16):
        # summary insert + delete + chain repair all commit or roll back
        # together. Delete-succeeds-repair-fails would leave the DB in a
        # state that LOOKS repaired (rows gone, nothing complains) but is
        # actually silently worse than before — reinstantiating the exact
        # "looks fine, isn't wired" failure class Marc's audit surfaced.
        # isolation_level=None + BEGIN IMMEDIATE matches backfill_chain_hashes
        # (ledger.py:826-827) and serializes against concurrent log_event.
        prior_isolation = conn.isolation_level
        conn.isolation_level = None
        conn.execute("BEGIN IMMEDIATE")
        try:
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

            # Repair the chain for surviving rows whose predecessors were
            # deleted (Marc audit finding 2026-07-16 / Aletheia round
            # a1e7f4c92b6d). Interpretation A: preserve the last-good
            # chain_hash as the implicit anchor, rebuild forward from the
            # first orphaned row.
            repair_result = _repair_chain_after_deletion(conn)

            # Audit event: same shape as LEDGER_CORRUPTION_REPAIRED in
            # ledger_verify.py — the repair itself becomes a first-class
            # ledger event so the audit trail includes the fact of repair.
            # Emit BEFORE COMMIT so it's part of the same atomic unit.
            import uuid as _uuid  # local import to avoid top-level shadow

            repair_event_id = str(_uuid.uuid4())
            repair_payload = {
                "action": "LEDGER_CHAIN_REPAIRED",
                "triggered_by": "compress_ledger",
                "compaction_event_id": event_id,
                "compressed_count": total_compressed,
                "first_orphan_rowid": repair_result["first_orphan_rowid"],
                "rebuilt_row_count": repair_result["rebuilt"],
                "status": repair_result["status"],
                "repaired_at": time.time(),
            }
            repair_payload_json = json.dumps(repair_payload, sort_keys=True)
            repair_content_hash = compute_hash(repair_payload_json)
            conn.execute(
                "INSERT INTO system_events (event_id, timestamp, event_type, actor, payload, content_hash) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    repair_event_id,
                    time.time(),
                    "LEDGER_CHAIN_REPAIRED",
                    "ledger_compressor",
                    repair_payload_json,
                    repair_content_hash,
                ),
            )

            conn.commit()
        except _LC_ERRORS:
            conn.rollback()
            raise
        finally:
            conn.isolation_level = prior_isolation

        logger.info(
            "ELMO compressed %d events (%s); chain repair: %s (rebuilt %d)",
            total_compressed,
            ", ".join(f"{k}: {v}" for k, v in compressed_by_type.items()),
            repair_result["status"],
            repair_result["rebuilt"],
        )

        return {
            "compressed": total_compressed,
            "by_type": compressed_by_type,
            "dry_run": False,
            "summary_event_id": event_id,
            "chain_repair": repair_result,
            "chain_repair_event_id": repair_event_id,
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
