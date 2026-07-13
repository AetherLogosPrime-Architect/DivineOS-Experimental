"""Tests for ledger size guard — auto-compression when approaching limit."""

import json
import time
import uuid

from divineos.core._ledger_base import compute_hash, get_connection
from divineos.core.ledger import init_db
from divineos.core.ledger_compressor import (
    auto_compress_if_needed,
    check_ledger_size,
    get_ledger_size_mb,
)


def _setup(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DIVINEOS_DB", str(db_path))
    init_db()
    return db_path


class TestCheckLedgerSize:
    def test_empty_ledger(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        status = check_ledger_size(max_size_gb=50.0)
        assert status["size_mb"] >= 0
        assert not status["over_limit"]
        assert not status["warning"]

    def test_small_ledger_not_warning(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        status = check_ledger_size(max_size_gb=1.0)
        assert not status["over_limit"]
        # A tiny test DB won't be anywhere near 800 MB (80% of 1 GB)
        assert not status["warning"]

    def test_over_limit_detection(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        # Set absurdly small limit so even an empty DB triggers it
        status = check_ledger_size(max_size_gb=0.000001)  # ~1 KB
        assert status["over_limit"]
        assert status["warning"]


class TestGetLedgerSizeMb:
    def test_returns_float(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        size = get_ledger_size_mb()
        assert isinstance(size, float)
        assert size >= 0


class TestAutoCompressIfNeeded:
    def test_no_compress_when_small(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        result = auto_compress_if_needed(max_size_gb=50.0)
        assert result is None  # Not needed

    def test_compress_when_over_limit(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        # Insert some old compressible events
        conn = get_connection()
        old_ts = time.time() - (30 * 86400)
        for i in range(10):
            eid = str(uuid.uuid4())
            payload = json.dumps({"tool_name": "Read", "content": f"test {i}"}, sort_keys=True)
            conn.execute(
                "INSERT INTO system_events (event_id, timestamp, event_type, actor, payload, content_hash) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (eid, old_ts, "TOOL_CALL", "system", payload, compute_hash(payload)),
            )
        conn.commit()
        conn.close()

        # Use absurdly small limit to trigger compression
        result = auto_compress_if_needed(max_size_gb=0.000001)
        assert result is not None
        assert result["compressed"] == 10
        assert result["trigger"] in ("over_limit", "warning_80pct")
