"""Tests for the fidelity system."""

from divineos.core.fidelity import (
    compute_content_hash,
    create_manifest,
    create_receipt,
    reconcile,
    verify_single_event,
    FidelityManifest,
    FidelityReceipt,
)


class TestComputeContentHash:
    def test_deterministic(self):
        assert compute_content_hash("test") == compute_content_hash("test")

    def test_different_input(self):
        assert compute_content_hash("a") != compute_content_hash("b")

    def test_length(self):
        assert len(compute_content_hash("hello")) == 32


class TestCreateManifest:
    def test_empty(self):
        m = create_manifest([])
        assert m.count == 0
        assert m.content_hash == ""
        assert m.bytes_total == 0

    def test_single_message(self):
        m = create_manifest([{"content": "hello"}])
        assert m.count == 1
        assert m.bytes_total == 5
        assert len(m.content_hash) == 32

    def test_multiple_messages(self):
        m = create_manifest([{"content": "a"}, {"content": "b"}])
        assert m.count == 2
        assert m.bytes_total == 2


class TestCreateReceipt:
    def test_empty(self):
        r = create_receipt([])
        assert r.count == 0
        assert r.stored_ids == []

    def test_from_events(self):
        events = [
            {"event_id": "e1", "payload": {"content": "hello"}},
            {"event_id": "e2", "payload": {"content": "world"}},
        ]
        r = create_receipt(events)
        assert r.count == 2
        assert r.stored_ids == ["e1", "e2"]
        assert r.bytes_total == 10


class TestReconcile:
    def test_matching(self):
        m = FidelityManifest(count=2, content_hash="abc", bytes_total=10)
        r = FidelityReceipt(count=2, content_hash="abc", bytes_total=10, stored_ids=["a", "b"])
        result = reconcile(m, r)
        assert result.passed is True
        assert all(result.checks.values())

    def test_count_mismatch(self):
        m = FidelityManifest(count=3, content_hash="abc", bytes_total=10)
        r = FidelityReceipt(count=2, content_hash="abc", bytes_total=10, stored_ids=["a", "b"])
        result = reconcile(m, r)
        assert result.passed is False
        assert "COUNT MISMATCH" in result.errors[0]

    def test_hash_mismatch(self):
        m = FidelityManifest(count=1, content_hash="aaa", bytes_total=5)
        r = FidelityReceipt(count=1, content_hash="bbb", bytes_total=5, stored_ids=["a"])
        result = reconcile(m, r)
        assert result.passed is False
        assert "HASH MISMATCH" in result.errors[0]

    def test_total_data_loss(self):
        m = FidelityManifest(count=5, content_hash="abc", bytes_total=50)
        r = FidelityReceipt(count=0, content_hash="", bytes_total=0, stored_ids=[])
        result = reconcile(m, r)
        assert result.passed is False
        assert any("TOTAL DATA LOSS" in e for e in result.errors)

    def test_byte_loss_warning(self):
        m = FidelityManifest(count=1, content_hash="abc", bytes_total=100)
        r = FidelityReceipt(count=1, content_hash="abc", bytes_total=90, stored_ids=["a"])
        result = reconcile(m, r)
        assert result.passed is True  # byte mismatch is warning, not error
        assert any("BYTE LOSS" in w for w in result.warnings)


class TestVerifySingleEvent:
    def test_valid_event(self):
        content = "hello world"
        h = compute_content_hash(content)
        event = {"payload": {"content": content, "content_hash": h}}
        ok, msg = verify_single_event(event)
        assert ok is True
        assert msg == "OK"

    def test_corrupted_event(self):
        event = {"payload": {"content": "hello", "content_hash": "wrong"}}
        ok, msg = verify_single_event(event)
        assert ok is False
        assert "HASH_MISMATCH" in msg

    def test_no_hash(self):
        event = {"payload": {"content": "hello"}}
        ok, msg = verify_single_event(event)
        assert ok is False
        assert "NO_HASH" in msg
