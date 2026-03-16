"""Tests for the event ledger."""

import pytest
from divineos.ledger import (
    init_db,
    log_event,
    get_events,
    search_events,
    get_recent_context,
    count_events,
    verify_all_events,
    compute_hash,
    export_to_markdown,
)


@pytest.fixture(autouse=True)
def clean_db(tmp_path, monkeypatch):
    """Use a temporary database for each test."""
    test_db = tmp_path / "test_ledger.db"
    monkeypatch.setenv("DIVINEOS_DB", str(test_db))
    init_db()
    yield
    if test_db.exists():
        test_db.unlink()


class TestComputeHash:
    def test_deterministic(self):
        assert compute_hash("hello") == compute_hash("hello")

    def test_different_content(self):
        assert compute_hash("hello") != compute_hash("world")

    def test_returns_32_chars(self):
        assert len(compute_hash("test")) == 32

    def test_empty_string(self):
        h = compute_hash("")
        assert len(h) == 32


class TestLogEvent:
    def test_returns_event_id(self):
        eid = log_event("TEST", "user", {"content": "hello"})
        assert isinstance(eid, str)
        assert len(eid) > 0

    def test_stores_content_hash(self):
        log_event("TEST", "user", {"content": "hello"})
        events = get_events()
        assert len(events) == 1
        assert events[0]["content_hash"] == compute_hash("hello")

    def test_multiple_events(self):
        log_event("A", "user", {"content": "first"})
        log_event("B", "assistant", {"content": "second"})
        events = get_events()
        assert len(events) == 2


class TestGetEvents:
    def test_empty_ledger(self):
        assert get_events() == []

    def test_limit(self):
        for i in range(5):
            log_event("TEST", "user", {"content": f"msg {i}"})
        events = get_events(limit=3)
        assert len(events) == 3

    def test_filter_by_type(self):
        log_event("USER_INPUT", "user", {"content": "hello"})
        log_event("ERROR", "system", {"content": "oops"})
        events = get_events(event_type="ERROR")
        assert len(events) == 1
        assert events[0]["event_type"] == "ERROR"

    def test_filter_by_actor(self):
        log_event("MSG", "user", {"content": "hi"})
        log_event("MSG", "assistant", {"content": "hello"})
        events = get_events(actor="user")
        assert len(events) == 1
        assert events[0]["actor"] == "user"


class TestSearchEvents:
    def test_finds_matching(self):
        log_event("TEST", "user", {"content": "the quick brown fox"})
        log_event("TEST", "user", {"content": "the lazy dog"})
        results = search_events("fox")
        assert len(results) == 1

    def test_no_matches(self):
        log_event("TEST", "user", {"content": "hello"})
        assert search_events("zzzzz") == []

    def test_case_insensitive(self):
        log_event("TEST", "user", {"content": "Hello World"})
        results = search_events("hello")
        assert len(results) == 1


class TestGetRecentContext:
    def test_returns_chronological(self):
        log_event("A", "user", {"content": "first"})
        log_event("B", "user", {"content": "second"})
        log_event("C", "user", {"content": "third"})
        ctx = get_recent_context(n=2)
        assert len(ctx) == 2
        assert ctx[0]["event_type"] == "B"
        assert ctx[1]["event_type"] == "C"


class TestCountEvents:
    def test_empty(self):
        counts = count_events()
        assert counts["total"] == 0

    def test_counts_by_type(self):
        log_event("USER_INPUT", "user", {"content": "a"})
        log_event("USER_INPUT", "user", {"content": "b"})
        log_event("ERROR", "system", {"content": "c"})
        counts = count_events()
        assert counts["total"] == 3
        assert counts["by_type"]["USER_INPUT"] == 2
        assert counts["by_type"]["ERROR"] == 1

    def test_counts_by_actor(self):
        log_event("MSG", "user", {"content": "a"})
        log_event("MSG", "assistant", {"content": "b"})
        counts = count_events()
        assert counts["by_actor"]["user"] == 1
        assert counts["by_actor"]["assistant"] == 1


class TestVerifyAllEvents:
    def test_all_pass(self):
        log_event("TEST", "user", {"content": "hello"})
        log_event("TEST", "user", {"content": "world"})
        result = verify_all_events()
        assert result["integrity"] == "PASS"
        assert result["passed"] == 2
        assert result["failed"] == 0

    def test_empty_ledger(self):
        result = verify_all_events()
        assert result["integrity"] == "PASS"
        assert result["total"] == 0


class TestExportToMarkdown:
    def test_exports_events(self):
        log_event("USER_INPUT", "user", {"content": "hello"})
        log_event("ASSISTANT_OUTPUT", "assistant", {"content": "hi there"})
        md = export_to_markdown()
        assert "## User" in md
        assert "hello" in md
        assert "## Assistant" in md
        assert "hi there" in md

    def test_empty_export(self):
        md = export_to_markdown()
        assert md == ""
