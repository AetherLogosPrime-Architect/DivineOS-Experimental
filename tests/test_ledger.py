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
        eid = log_event("TEST", "user", {"content": "hello"}, validate=False)
        assert isinstance(eid, str)
        assert len(eid) > 0

    def test_stores_content_hash(self):
        log_event("TEST", "user", {"content": "hello"}, validate=False)
        events = get_events()
        assert len(events) == 1
        # Hash should be computed from entire payload (excluding content_hash field)
        import json

        payload_copy = {"content": "hello"}
        payload_json = json.dumps(payload_copy, ensure_ascii=False, sort_keys=True)
        expected_hash = compute_hash(payload_json)
        assert events[0]["content_hash"] == expected_hash

    def test_multiple_events(self):
        log_event("A", "user", {"content": "first"}, validate=False)
        log_event("B", "assistant", {"content": "second"}, validate=False)
        events = get_events()
        assert len(events) == 2


class TestGetEvents:
    def test_empty_ledger(self):
        assert get_events() == []

    def test_limit(self):
        for i in range(5):
            log_event("TEST", "user", {"content": f"msg {i}"}, validate=False)
        events = get_events(limit=3)
        assert len(events) == 3

    def test_filter_by_type(self):
        log_event("USER_INPUT", "user", {"content": "hello"}, validate=False)
        log_event("ERROR", "system", {"content": "oops"}, validate=False)
        events = get_events(event_type="ERROR")
        assert len(events) == 1
        assert events[0]["event_type"] == "ERROR"

    def test_filter_by_actor(self):
        log_event("MSG", "user", {"content": "hi"}, validate=False)
        log_event("MSG", "assistant", {"content": "hello"}, validate=False)
        events = get_events(actor="user")
        assert len(events) == 1
        assert events[0]["actor"] == "user"


class TestSearchEvents:
    def test_finds_matching(self):
        log_event("TEST", "user", {"content": "the quick brown fox"}, validate=False)
        log_event("TEST", "user", {"content": "the lazy dog"}, validate=False)
        results = search_events("fox")
        assert len(results) == 1

    def test_no_matches(self):
        log_event("TEST", "user", {"content": "hello"}, validate=False)
        assert search_events("zzzzz") == []

    def test_case_insensitive(self):
        log_event("TEST", "user", {"content": "Hello World"}, validate=False)
        results = search_events("hello")
        assert len(results) == 1


class TestGetRecentContext:
    def test_returns_chronological(self):
        log_event("A", "user", {"content": "first"}, validate=False)
        log_event("B", "user", {"content": "second"}, validate=False)
        log_event("C", "user", {"content": "third"}, validate=False)
        ctx = get_recent_context(n=2)
        assert len(ctx) == 2
        assert ctx[0]["event_type"] == "B"
        assert ctx[1]["event_type"] == "C"


class TestCountEvents:
    def test_empty(self):
        counts = count_events()
        assert counts["total"] == 0

    def test_counts_by_type(self):
        log_event("USER_INPUT", "user", {"content": "a"}, validate=False)
        log_event("USER_INPUT", "user", {"content": "b"}, validate=False)
        log_event("ERROR", "system", {"content": "c"}, validate=False)
        counts = count_events()
        assert counts["total"] == 3
        assert counts["by_type"]["USER_INPUT"] == 2
        assert counts["by_type"]["ERROR"] == 1

    def test_counts_by_actor(self):
        log_event("MSG", "user", {"content": "a"}, validate=False)
        log_event("MSG", "assistant", {"content": "b"}, validate=False)
        counts = count_events()
        assert counts["by_actor"]["user"] == 1
        assert counts["by_actor"]["assistant"] == 1


class TestVerifyAllEvents:
    def test_all_pass(self):
        log_event("TEST", "user", {"content": "hello"}, validate=False)
        log_event("TEST", "user", {"content": "world"}, validate=False)
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
        log_event("USER_INPUT", "user", {"content": "hello"}, validate=False)
        log_event("ASSISTANT_OUTPUT", "assistant", {"content": "hi there"}, validate=False)
        md = export_to_markdown()
        assert "## User" in md
        assert "hello" in md
        assert "## Assistant" in md
        assert "hi there" in md

    def test_empty_export(self):
        md = export_to_markdown()
        assert md == ""


class TestVerifyEventHash:
    """Tests for verify_event_hash function."""

    def test_valid_hash(self):
        """Test that valid hash is verified correctly."""
        from divineos.ledger import verify_event_hash
        import json

        payload = {"content": "hello"}
        # Compute hash from entire payload (excluding content_hash)
        payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        stored_hash = compute_hash(payload_json)

        is_valid, reason = verify_event_hash("event-1", payload, stored_hash)
        assert is_valid is True
        assert "verified" in reason.lower()

    def test_invalid_hash(self):
        """Test that invalid hash is detected."""
        from divineos.ledger import verify_event_hash

        payload = {"content": "hello"}
        # Use wrong hash
        stored_hash = compute_hash("world")

        is_valid, reason = verify_event_hash("event-1", payload, stored_hash)
        assert is_valid is False
        assert "mismatch" in reason.lower()

    def test_dict_content(self):
        """Test hash verification with dict content."""
        from divineos.ledger import verify_event_hash
        import json

        content = {"key": "value"}
        payload = {"content": content}
        # Compute hash from entire payload (excluding content_hash)
        payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        stored_hash = compute_hash(payload_json)

        is_valid, reason = verify_event_hash("event-1", payload, stored_hash)
        assert is_valid is True


class TestGetVerifiedEvents:
    """Tests for get_verified_events function."""

    def test_all_valid_events(self):
        """Test retrieving all valid events."""
        from divineos.ledger import get_verified_events

        log_event("TEST", "user", {"content": "hello"}, validate=False)
        log_event("TEST", "user", {"content": "world"}, validate=False)

        verified, corrupted = get_verified_events()
        assert len(verified) == 2
        assert len(corrupted) == 0

    def test_skip_corrupted_events(self):
        """Test that corrupted events are excluded when skip_corrupted=True."""
        from divineos.ledger import get_verified_events
        import sqlite3
        import os

        # Create valid events
        log_event("TEST", "user", {"content": "hello"}, validate=False)
        log_event("TEST", "user", {"content": "world"}, validate=False)

        # Corrupt one event by modifying its hash in the database
        db_path = os.environ.get("DIVINEOS_DB")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get the first event ID
        cursor.execute("SELECT event_id FROM system_events LIMIT 1")
        event_id = cursor.fetchone()[0]

        # Update its hash to an invalid value
        cursor.execute(
            "UPDATE system_events SET content_hash = ? WHERE event_id = ?",
            ("ffffffffffffffffffffffffffffffff", event_id),
        )
        conn.commit()
        conn.close()

        # Retrieve events with skip_corrupted=True
        verified, corrupted = get_verified_events(skip_corrupted=True)
        assert len(verified) == 1
        assert len(corrupted) == 1
        assert corrupted[0]["is_corrupted"] is True

    def test_include_corrupted_events(self):
        """Test that corrupted events are included when skip_corrupted=False."""
        from divineos.ledger import get_verified_events
        import sqlite3
        import os

        # Create valid events
        log_event("TEST", "user", {"content": "hello"}, validate=False)
        log_event("TEST", "user", {"content": "world"}, validate=False)

        # Corrupt one event
        db_path = os.environ.get("DIVINEOS_DB")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT event_id FROM system_events LIMIT 1")
        event_id = cursor.fetchone()[0]

        cursor.execute(
            "UPDATE system_events SET content_hash = ? WHERE event_id = ?",
            ("ffffffffffffffffffffffffffffffff", event_id),
        )
        conn.commit()
        conn.close()

        # Retrieve events with skip_corrupted=False
        # Note: get_verified_events always returns (verified, corrupted) separately
        # skip_corrupted parameter doesn't change the return format
        verified, corrupted = get_verified_events(skip_corrupted=False)
        assert len(verified) == 1
        assert len(corrupted) == 1
        assert corrupted[0]["is_corrupted"] is True

    def test_filter_by_type_with_verification(self):
        """Test filtering by type while verifying hashes."""
        from divineos.ledger import get_verified_events

        log_event("USER_INPUT", "user", {"content": "hello"}, validate=False)
        log_event("ERROR", "system", {"content": "oops"}, validate=False)

        verified, corrupted = get_verified_events(event_type="USER_INPUT")
        assert len(verified) == 1
        assert verified[0]["event_type"] == "USER_INPUT"
        assert len(corrupted) == 0

    def test_filter_by_actor_with_verification(self):
        """Test filtering by actor while verifying hashes."""
        from divineos.ledger import get_verified_events

        log_event("MSG", "user", {"content": "hi"}, validate=False)
        log_event("MSG", "assistant", {"content": "hello"}, validate=False)

        verified, corrupted = get_verified_events(actor="user")
        assert len(verified) == 1
        assert verified[0]["actor"] == "user"
        assert len(corrupted) == 0


class TestVerifyAllEventsEnhanced:
    """Enhanced tests for verify_all_events function."""

    def test_detects_corrupted_events(self):
        """Test that verify_all_events detects corrupted events."""
        import sqlite3
        import os

        log_event("TEST", "user", {"content": "hello"}, validate=False)
        log_event("TEST", "user", {"content": "world"}, validate=False)

        # Corrupt one event
        db_path = os.environ.get("DIVINEOS_DB")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT event_id FROM system_events LIMIT 1")
        event_id = cursor.fetchone()[0]

        cursor.execute(
            "UPDATE system_events SET content_hash = ? WHERE event_id = ?",
            ("ffffffffffffffffffffffffffffffff", event_id),
        )
        conn.commit()
        conn.close()

        result = verify_all_events()
        assert result["integrity"] == "FAIL"
        assert result["failed"] == 1
        assert result["passed"] == 1
        assert len(result["failures"]) == 1

    def test_reports_failure_reason(self):
        """Test that verify_all_events reports the reason for failure."""
        import sqlite3
        import os

        log_event("TEST", "user", {"content": "hello"}, validate=False)

        # Corrupt the event
        db_path = os.environ.get("DIVINEOS_DB")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT event_id FROM system_events LIMIT 1")
        event_id = cursor.fetchone()[0]

        cursor.execute(
            "UPDATE system_events SET content_hash = ? WHERE event_id = ?",
            ("ffffffffffffffffffffffffffffffff", event_id),
        )
        conn.commit()
        conn.close()

        result = verify_all_events()
        assert len(result["failures"]) == 1
        failure = result["failures"][0]
        assert "reason" in failure
        assert "mismatch" in failure["reason"].lower()


class TestExportCurrentSessionWithVerification:
    """Tests for export_current_session_to_jsonl with hash verification."""

    def test_excludes_corrupted_events(self):
        """Test that corrupted events are excluded from export."""
        from divineos.analysis import export_current_session_to_jsonl
        from divineos.event_capture import get_session_tracker
        from pathlib import Path
        import sqlite3
        import os
        import json

        # Get current session ID
        session_id = get_session_tracker().get_current_session_id()

        # Write session_id to persistent file so export_current_session_to_jsonl can find it
        session_file = Path.home() / ".divineos" / "current_session.txt"
        session_file.parent.mkdir(parents=True, exist_ok=True)
        session_file.write_text(session_id)

        # Create events with session_id
        log_event(
            "USER_INPUT", "user", {"content": "hello", "session_id": session_id}, validate=False
        )
        log_event(
            "USER_INPUT", "user", {"content": "world", "session_id": session_id}, validate=False
        )

        # Corrupt one event
        db_path = os.environ.get("DIVINEOS_DB")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT event_id FROM system_events LIMIT 1")
        event_id = cursor.fetchone()[0]

        cursor.execute(
            "UPDATE system_events SET content_hash = ? WHERE event_id = ?",
            ("ffffffffffffffffffffffffffffffff", event_id),
        )
        conn.commit()
        conn.close()

        # Export session
        export_path = export_current_session_to_jsonl()

        # Read exported file
        content = export_path.read_text()
        lines = content.strip().split("\n")

        # Should only have 1 valid event (the corrupted one is excluded)
        assert len(lines) == 1

        # Verify the remaining event is valid and is one of the original messages
        msg = json.loads(lines[0])
        assert msg["type"] == "user"
        assert msg["message"]["content"] in ["hello", "world"]

    def test_exports_all_valid_events(self):
        """Test that all valid events are exported."""
        from divineos.analysis import export_current_session_to_jsonl
        from divineos.event_capture import get_session_tracker
        from pathlib import Path
        import json

        # Get current session ID
        session_id = get_session_tracker().get_current_session_id()

        # Write session_id to persistent file so export_current_session_to_jsonl can find it
        session_file = Path.home() / ".divineos" / "current_session.txt"
        session_file.parent.mkdir(parents=True, exist_ok=True)
        session_file.write_text(session_id)

        # Create valid events with session_id
        log_event(
            "USER_INPUT", "user", {"content": "hello", "session_id": session_id}, validate=False
        )
        log_event(
            "USER_INPUT", "user", {"content": "world", "session_id": session_id}, validate=False
        )

        # Export session
        export_path = export_current_session_to_jsonl()

        # Read exported file
        content = export_path.read_text()
        lines = content.strip().split("\n")

        # Should have 2 events
        assert len(lines) == 2

        # Verify both are valid
        for line in lines:
            msg = json.loads(line)
            assert msg["type"] == "user"
