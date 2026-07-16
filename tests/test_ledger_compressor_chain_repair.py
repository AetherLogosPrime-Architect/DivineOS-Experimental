"""Tests for the chain-repair fix in ledger_compressor.

Marc audit finding 2026-07-16 (Aletheia round-a1e7f4c92b6d class-adjacent):
the compressor deleted rows in the middle of the hash chain without
repairing it, silently breaking the tamper-evidence property. The fix
adds ``_repair_chain_after_deletion`` and threads it into
``compress_ledger`` inside the same transaction as the DELETE.

Design decisions locked in Aria + Aether letter exchange 2026-07-16:
  - Interpretation A (implicit anchor at last-good chain_hash)
  - Same-transaction (atomic delete + repair)
  - Emit LEDGER_CHAIN_REPAIRED audit event capturing the repair

These tests verify all three properties on a scratch DB so we don't
touch the running ledger.
"""

from __future__ import annotations

import json
import sqlite3
import time

import pytest


@pytest.fixture
def scratch_ledger(tmp_path, monkeypatch):
    """Build a fresh ledger database at a scratch path and route
    _get_db_path to it. Returns (path, connection-factory)."""
    db_path = tmp_path / "ledger.sqlite"
    monkeypatch.setenv("DIVINEOS_LEDGER_PATH", str(db_path))
    # Force the module to re-resolve the path if it caches
    from divineos.core import _ledger_base

    monkeypatch.setattr(_ledger_base, "_get_db_path", lambda: db_path)
    from divineos.core import ledger as ledger_mod

    monkeypatch.setattr(ledger_mod, "_get_db_path", lambda: db_path)
    # init_db creates the schema
    ledger_mod.init_db()
    return db_path


def _append_events(n: int, event_type: str = "USER_INPUT", timestamp_offset: float = 0.0):
    """Append n events via log_event so chain metadata is populated by
    the append path. Returns the list of event_ids."""
    from divineos.core.ledger import log_event

    ids = []
    for i in range(n):
        eid = log_event(
            event_type,
            actor="test",
            payload={"content": f"event-{i}", "session_id": "test-session"},
            validate=False,
        )
        ids.append(eid)
    return ids


def _all_chain_hashes(db_path):
    conn = sqlite3.connect(str(db_path))
    try:
        return list(
            conn.execute(
                "SELECT rowid, event_id, event_type, prior_hash, chain_hash "
                "FROM system_events ORDER BY timestamp ASC, rowid ASC"
            )
        )
    finally:
        conn.close()


def test_smoke_chain_healthy_before_compression(scratch_ledger):
    """Baseline: append events, verify_chain returns ok=True."""
    _append_events(10)
    from divineos.core.ledger import verify_chain

    result = verify_chain()
    assert result["ok"] is True, result


def test_compressor_breaks_chain_without_repair_would_be(scratch_ledger):
    """This test locks in the previous-broken behavior as a NEGATIVE:
    after compression, if the repair hook were NOT present, verify_chain
    would fail. We instead assert the repair DID happen — the fix is
    load-bearing.

    Setup: 5 real events, 5 compressible noise events (older), 5 more real.
    Compress with a retention window that catches the middle noise events.
    """
    # 5 real events (kept)
    _append_events(5, event_type="USER_INPUT")
    # 5 noise events with old timestamps (will be compressed)
    # We rewrite their timestamps directly to be old
    _append_events(5, event_type="TOOL_CALL")
    # 5 more real events (kept)
    _append_events(5, event_type="USER_INPUT")

    # Rewrite the middle TOOL_CALL rows to be old enough to compress.
    # Then re-run backfill so their chain metadata is recomputed with
    # the rewritten timestamps (matches what a real long-lived ledger
    # would have).
    conn = sqlite3.connect(str(scratch_ledger))
    try:
        old_ts = time.time() - (60 * 24 * 60 * 60)  # 60 days ago
        conn.execute(
            "UPDATE system_events SET timestamp = ? WHERE event_type = 'TOOL_CALL'",
            (old_ts,),
        )
        # Wipe chain metadata so backfill recomputes with the new order
        conn.execute("UPDATE system_events SET prior_hash = NULL, chain_hash = NULL")
        # Clear the anchor so post-manipulation backfill produces a valid
        # chain from verify_chain's perspective. Real production runs
        # never do this — this is only because the tests manually
        # rewrite timestamps to simulate age.
        conn.execute("DELETE FROM ledger_head_anchor WHERE row_id = 1")
        conn.commit()
    finally:
        conn.close()

    from divineos.core.ledger import backfill_chain_hashes, verify_chain

    backfill_chain_hashes()
    # After backfill with new timestamps, chain should be healthy
    assert verify_chain()["ok"] is True

    from divineos.core.ledger_compressor import compress_ledger

    result = compress_ledger(retention_days=30, dry_run=False)
    assert result["compressed"] == 5, result
    # The fix's specific promise: repair ran
    assert result["chain_repair"]["status"] == "repaired"
    # And after compression + repair, verify_chain returns ok=True
    chain = verify_chain()
    assert chain["ok"] is True, chain


def test_compressor_emits_chain_repaired_audit_event(scratch_ledger):
    """LEDGER_CHAIN_REPAIRED audit event is written into the same DB
    with a valid content_hash and captures the repair metadata."""
    _append_events(3, event_type="USER_INPUT")
    _append_events(3, event_type="TOOL_CALL")
    _append_events(3, event_type="USER_INPUT")

    old_ts = time.time() - (60 * 24 * 60 * 60)
    conn = sqlite3.connect(str(scratch_ledger))
    try:
        conn.execute(
            "UPDATE system_events SET timestamp = ? WHERE event_type = 'TOOL_CALL'",
            (old_ts,),
        )
        conn.execute("UPDATE system_events SET prior_hash = NULL, chain_hash = NULL")
        # Clear the anchor so post-manipulation backfill produces a valid
        # chain from verify_chain's perspective. Real production runs
        # never do this — this is only because the tests manually
        # rewrite timestamps to simulate age.
        conn.execute("DELETE FROM ledger_head_anchor WHERE row_id = 1")
        conn.commit()
    finally:
        conn.close()

    from divineos.core.ledger import backfill_chain_hashes

    backfill_chain_hashes()

    from divineos.core.ledger_compressor import compress_ledger

    compress_ledger(retention_days=30, dry_run=False)

    # Fetch the audit event
    conn = sqlite3.connect(str(scratch_ledger))
    try:
        row = conn.execute(
            "SELECT event_id, event_type, actor, payload "
            "FROM system_events WHERE event_type = 'LEDGER_CHAIN_REPAIRED' "
            "ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()
    finally:
        conn.close()
    assert row is not None, "LEDGER_CHAIN_REPAIRED audit event not found"
    assert row[1] == "LEDGER_CHAIN_REPAIRED"
    assert row[2] == "ledger_compressor"
    payload = json.loads(row[3])
    assert payload["action"] == "LEDGER_CHAIN_REPAIRED"
    assert payload["triggered_by"] == "compress_ledger"
    assert payload["compressed_count"] == 3
    assert payload["status"] == "repaired"


def test_repair_is_idempotent_no_orphans_reports_no_orphans(scratch_ledger):
    """If nothing is broken, _repair_chain_after_deletion returns
    no_orphans and rebuilds nothing. Idempotent — safe to run against
    a healthy chain."""
    _append_events(5)
    conn = sqlite3.connect(str(scratch_ledger))
    try:
        conn.isolation_level = None
        conn.execute("BEGIN IMMEDIATE")
        from divineos.core.ledger_compressor import _repair_chain_after_deletion

        result = _repair_chain_after_deletion(conn)
        conn.commit()
    finally:
        conn.close()
    assert result["status"] == "no_orphans"
    assert result["rebuilt"] == 0
    assert result["first_orphan_rowid"] is None


def test_tamper_detection_preserved_after_repair(scratch_ledger):
    """After compression + repair, the chain is healthy. Now if we
    tamper with a surviving row's payload, verify_chain must STILL
    detect the tamper. The repair rebuilt the chain correctly; the
    tamper-detection property is preserved, not just short-term happy-
    path pass."""
    _append_events(3, event_type="USER_INPUT")
    _append_events(3, event_type="TOOL_CALL")
    _append_events(3, event_type="USER_INPUT")

    old_ts = time.time() - (60 * 24 * 60 * 60)
    conn = sqlite3.connect(str(scratch_ledger))
    try:
        conn.execute(
            "UPDATE system_events SET timestamp = ? WHERE event_type = 'TOOL_CALL'",
            (old_ts,),
        )
        conn.execute("UPDATE system_events SET prior_hash = NULL, chain_hash = NULL")
        # Clear the anchor so post-manipulation backfill produces a valid
        # chain from verify_chain's perspective. Real production runs
        # never do this — this is only because the tests manually
        # rewrite timestamps to simulate age.
        conn.execute("DELETE FROM ledger_head_anchor WHERE row_id = 1")
        conn.commit()
    finally:
        conn.close()

    from divineos.core.ledger import backfill_chain_hashes, verify_chain

    backfill_chain_hashes()

    from divineos.core.ledger_compressor import compress_ledger

    compress_ledger(retention_days=30, dry_run=False)
    assert verify_chain()["ok"] is True

    # Tamper with a surviving USER_INPUT row's payload
    conn = sqlite3.connect(str(scratch_ledger))
    try:
        row = conn.execute(
            "SELECT event_id, payload FROM system_events "
            "WHERE event_type = 'USER_INPUT' ORDER BY rowid ASC LIMIT 1"
        ).fetchone()
        assert row is not None
        tampered_payload = json.dumps({"content": "TAMPERED", "session_id": "attacker"})
        conn.execute(
            "UPDATE system_events SET payload = ? WHERE event_id = ?",
            (tampered_payload, row[0]),
        )
        conn.commit()
    finally:
        conn.close()

    chain_after_tamper = verify_chain()
    assert chain_after_tamper["ok"] is False, "verify_chain must still detect tamper after repair"


def test_repair_result_included_in_compress_ledger_return(scratch_ledger):
    """The return dict from compress_ledger includes chain_repair and
    chain_repair_event_id keys. Callers can inspect the repair outcome."""
    _append_events(2, event_type="USER_INPUT")
    _append_events(2, event_type="TOOL_CALL")

    old_ts = time.time() - (60 * 24 * 60 * 60)
    conn = sqlite3.connect(str(scratch_ledger))
    try:
        conn.execute(
            "UPDATE system_events SET timestamp = ? WHERE event_type = 'TOOL_CALL'",
            (old_ts,),
        )
        conn.execute("UPDATE system_events SET prior_hash = NULL, chain_hash = NULL")
        # Clear the anchor so post-manipulation backfill produces a valid
        # chain from verify_chain's perspective. Real production runs
        # never do this — this is only because the tests manually
        # rewrite timestamps to simulate age.
        conn.execute("DELETE FROM ledger_head_anchor WHERE row_id = 1")
        conn.commit()
    finally:
        conn.close()

    from divineos.core.ledger import backfill_chain_hashes

    backfill_chain_hashes()

    from divineos.core.ledger_compressor import compress_ledger

    result = compress_ledger(retention_days=30, dry_run=False)
    assert "chain_repair" in result
    assert "chain_repair_event_id" in result
    assert result["chain_repair_event_id"] is not None


def test_dry_run_does_not_repair_or_emit_event(scratch_ledger):
    """dry_run=True must not modify the DB — no repair, no audit event."""
    _append_events(2, event_type="USER_INPUT")
    _append_events(2, event_type="TOOL_CALL")

    old_ts = time.time() - (60 * 24 * 60 * 60)
    conn = sqlite3.connect(str(scratch_ledger))
    try:
        conn.execute(
            "UPDATE system_events SET timestamp = ? WHERE event_type = 'TOOL_CALL'",
            (old_ts,),
        )
        conn.execute("UPDATE system_events SET prior_hash = NULL, chain_hash = NULL")
        # Clear the anchor so post-manipulation backfill produces a valid
        # chain from verify_chain's perspective. Real production runs
        # never do this — this is only because the tests manually
        # rewrite timestamps to simulate age.
        conn.execute("DELETE FROM ledger_head_anchor WHERE row_id = 1")
        conn.commit()
    finally:
        conn.close()

    from divineos.core.ledger import backfill_chain_hashes

    backfill_chain_hashes()

    from divineos.core.ledger_compressor import compress_ledger

    result = compress_ledger(retention_days=30, dry_run=True)
    assert result["dry_run"] is True
    assert result.get("chain_repair_event_id") is None or "chain_repair" not in result

    # No LEDGER_CHAIN_REPAIRED in DB
    conn = sqlite3.connect(str(scratch_ledger))
    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM system_events WHERE event_type = 'LEDGER_CHAIN_REPAIRED'"
        ).fetchone()
    finally:
        conn.close()
    assert row[0] == 0
