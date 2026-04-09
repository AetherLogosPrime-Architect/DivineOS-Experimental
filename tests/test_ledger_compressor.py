"""Tests for ELMO — Event Ledger Memory Optimizer."""

import time

from divineos.core.ledger import init_db, log_event
from divineos.core.ledger_compressor import (
    _COMPRESSIBLE_TYPES,
    analyze_ledger,
    compress_ledger,
    vacuum_ledger,
)


def _setup(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DIVINEOS_DB", str(db_path))
    init_db()


def _log_old_event(event_type, days_ago=30):
    """Log an event with a backdated timestamp."""
    import json
    import uuid

    from divineos.core._ledger_base import compute_hash, get_connection

    conn = get_connection()
    event_id = str(uuid.uuid4())
    payload = {"content": f"test {event_type}", "session_id": "test-session"}
    payload_json = json.dumps(payload, sort_keys=True)
    content_hash = compute_hash(payload_json)
    old_ts = time.time() - (days_ago * 86400)
    conn.execute(
        "INSERT INTO system_events (event_id, timestamp, event_type, actor, payload, content_hash) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (event_id, old_ts, event_type, "system", payload_json, content_hash),
    )
    conn.commit()
    conn.close()
    return event_id


class TestAnalyzeLedger:
    def test_empty_ledger(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        stats = analyze_ledger()
        assert stats["total_events"] == 0
        assert stats["compressible_count"] == 0

    def test_counts_compressible(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        # Old compressible events
        _log_old_event("TOOL_CALL", days_ago=30)
        _log_old_event("TOOL_RESULT", days_ago=30)
        _log_old_event("TOOL_CALL", days_ago=30)
        # Recent compressible (should NOT be counted)
        log_event(
            "TOOL_CALL", "system", {"tool_name": "Read", "tool_use_id": "t1", "content": "recent"}
        )
        # Meaningful event (should NOT be counted)
        _log_old_event("USER_INPUT", days_ago=30)

        stats = analyze_ledger()
        assert stats["total_events"] == 5
        assert stats["compressible_count"] == 3
        assert stats["meaningful_kept"] == 2  # recent TOOL_CALL + USER_INPUT

    def test_compressible_types_complete(self):
        """All compressible types should be high-volume bookkeeping."""
        for t in _COMPRESSIBLE_TYPES:
            assert t not in {"USER_INPUT", "SESSION_END", "SUPERSESSION", "CLARITY_STATEMENT"}


class TestCompressLedger:
    def test_compress_removes_old_noise(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        _log_old_event("TOOL_CALL", days_ago=30)
        _log_old_event("TOOL_RESULT", days_ago=30)
        _log_old_event("AGENT_PATTERN", days_ago=30)
        log_event("USER_INPUT", "user", {"content": "hello"})

        result = compress_ledger(retention_days=7)
        assert result["compressed"] == 3
        assert result["dry_run"] is False
        assert result["summary_event_id"] is not None

        # Verify the compaction summary event was created
        from divineos.core._ledger_base import get_connection

        conn = get_connection()
        rows = conn.execute("SELECT event_type FROM system_events").fetchall()
        types = [r[0] for r in rows]
        conn.close()
        assert "LEDGER_COMPACTION" in types
        assert "TOOL_CALL" not in types
        assert "USER_INPUT" in types

    def test_dry_run_preserves_events(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        _log_old_event("TOOL_CALL", days_ago=30)
        _log_old_event("TOOL_RESULT", days_ago=30)

        result = compress_ledger(retention_days=7, dry_run=True)
        assert result["compressed"] == 2
        assert result["dry_run"] is True

        # Events should still exist
        from divineos.core._ledger_base import get_connection

        conn = get_connection()
        count = conn.execute("SELECT COUNT(*) FROM system_events").fetchone()[0]
        conn.close()
        assert count == 2

    def test_preserves_meaningful_events(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        _log_old_event("USER_INPUT", days_ago=60)
        _log_old_event("SESSION_END", days_ago=60)
        _log_old_event("SUPERSESSION", days_ago=60)
        _log_old_event("TOOL_CALL", days_ago=60)

        result = compress_ledger(retention_days=7)
        assert result["compressed"] == 1  # Only TOOL_CALL

        from divineos.core._ledger_base import get_connection

        conn = get_connection()
        count = conn.execute("SELECT COUNT(*) FROM system_events").fetchone()[0]
        conn.close()
        # 3 meaningful + 1 compaction summary = 4
        assert count == 4

    def test_respects_retention_window(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        _log_old_event("TOOL_CALL", days_ago=3)  # Within 7-day window

        result = compress_ledger(retention_days=7)
        assert result["compressed"] == 0

    def test_nothing_to_compress(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        result = compress_ledger()
        assert result["compressed"] == 0
        assert result["summary_event_id"] is None


class TestVacuumLedger:
    def test_vacuum_returns_sizes(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        log_event("TEST", "system", {"content": "test"})
        result = vacuum_ledger()
        assert "size_before_mb" in result
        assert "size_after_mb" in result
        assert "saved_mb" in result
