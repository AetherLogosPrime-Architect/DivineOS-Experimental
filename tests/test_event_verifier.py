"""Tests for event integrity verification system."""

import pytest
from hypothesis import given, strategies as st, settings

from divineos.core.ledger import (
    init_db,
    log_event,
    _get_connection,
)
from divineos.core.event_verifier import EventVerifier, VerificationReport


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Use a temporary database for each test."""
    test_db = tmp_path / "test_verifier.db"
    monkeypatch.setenv("DIVINEOS_DB", str(test_db))
    init_db()
    yield
    if test_db.exists():
        test_db.unlink()


class TestEventVerifier:
    """Test EventVerifier class."""

    def test_verifier_initialization(self):
        """Test that EventVerifier initializes correctly."""
        verifier = EventVerifier()
        assert verifier is not None
        assert verifier.logger is not None

    def test_verify_all_events_empty_ledger(self):
        """Test verification on empty ledger."""
        verifier = EventVerifier()
        report = verifier.verify_all_events()

        assert report.total_events == 0
        assert report.valid_events == 0
        assert report.corrupted_events == 0
        assert report.verification_status == "PASS"

    def test_verify_all_events_single_valid_event(self):
        """Test verification with single valid event."""
        # Create an event
        event_id = log_event("TEST", "user", {"content": "hello"}, validate=False)

        verifier = EventVerifier()
        report = verifier.verify_all_events()

        assert report.total_events == 1
        assert report.valid_events == 1
        assert report.corrupted_events == 0
        assert report.verification_status == "PASS"
        assert event_id not in report.corrupted_event_ids

    def test_verify_all_events_multiple_valid_events(self):
        """Test verification with multiple valid events."""
        # Create multiple events
        for i in range(5):
            log_event("TEST", "user", {"content": f"message {i}"}, validate=False)

        verifier = EventVerifier()
        report = verifier.verify_all_events()

        assert report.total_events == 5
        assert report.valid_events == 5
        assert report.corrupted_events == 0
        assert report.verification_status == "PASS"

    def test_verify_single_event_valid(self):
        """Test verification of single valid event."""
        event_id = log_event("TEST", "user", {"content": "hello"}, validate=False)

        verifier = EventVerifier()
        is_valid, reason = verifier.verify_event(event_id)

        assert is_valid is True
        assert "verified" in reason.lower() or "hash" in reason.lower()

    def test_verify_single_event_not_found(self):
        """Test verification of non-existent event."""
        verifier = EventVerifier()
        is_valid, reason = verifier.verify_event("nonexistent-id")

        assert is_valid is False
        assert "not found" in reason.lower()

    def test_detect_corrupted_events_empty_ledger(self):
        """Test corruption detection on empty ledger."""
        verifier = EventVerifier()
        corrupted = verifier.detect_corrupted_events()

        assert corrupted == []

    def test_detect_corrupted_events_no_corruption(self):
        """Test corruption detection with valid events."""
        # Create valid events
        for i in range(3):
            log_event("TEST", "user", {"content": f"message {i}"}, validate=False)

        verifier = EventVerifier()
        corrupted = verifier.detect_corrupted_events()

        assert corrupted == []

    def test_detect_corrupted_events_with_corrupted_hash(self):
        """Test corruption detection with corrupted hash."""
        # Create an event
        event_id = log_event("TEST", "user", {"content": "hello"}, validate=False)

        # Corrupt the hash in the database
        conn = _get_connection()
        try:
            conn.execute(
                "UPDATE system_events SET content_hash = ? WHERE event_id = ?",
                ("corrupted_hash_value", event_id),
            )
            conn.commit()
        finally:
            conn.close()

        verifier = EventVerifier()
        corrupted = verifier.detect_corrupted_events()

        assert len(corrupted) == 1
        assert corrupted[0]["event_id"] == event_id
        assert corrupted[0]["corruption_type"] == "hash_mismatch"

    def test_detect_corrupted_events_with_missing_hash(self):
        """Test corruption detection with missing hash."""
        # Create an event
        event_id = log_event("TEST", "user", {"content": "hello"}, validate=False)

        # Remove the hash from the database
        conn = _get_connection()
        try:
            conn.execute(
                "UPDATE system_events SET content_hash = ? WHERE event_id = ?",
                ("", event_id),
            )
            conn.commit()
        finally:
            conn.close()

        verifier = EventVerifier()
        corrupted = verifier.detect_corrupted_events()

        assert len(corrupted) == 1
        assert corrupted[0]["event_id"] == event_id
        assert corrupted[0]["corruption_type"] == "missing_hash"

    def test_detect_corrupted_events_with_malformed_payload(self):
        """Test corruption detection with malformed JSON payload."""
        # Create an event
        event_id = log_event("TEST", "user", {"content": "hello"}, validate=False)

        # Corrupt the payload JSON
        conn = _get_connection()
        try:
            conn.execute(
                "UPDATE system_events SET payload = ? WHERE event_id = ?",
                ("invalid json {", event_id),
            )
            conn.commit()
        finally:
            conn.close()

        verifier = EventVerifier()
        corrupted = verifier.detect_corrupted_events()

        assert len(corrupted) == 1
        assert corrupted[0]["event_id"] == event_id
        assert corrupted[0]["corruption_type"] == "malformed_payload"

    def test_generate_verification_report(self):
        """Test verification report generation."""
        # Create some events
        for i in range(3):
            log_event("TEST", "user", {"content": f"message {i}"}, validate=False)

        verifier = EventVerifier()
        report = verifier.generate_verification_report()

        assert isinstance(report, VerificationReport)
        assert report.total_events == 3
        assert report.valid_events == 3
        assert report.corrupted_events == 0
        assert report.verification_status == "PASS"
        assert report.verification_timestamp != ""

    def test_verification_report_to_dict(self):
        """Test conversion of verification report to dictionary."""
        log_event("TEST", "user", {"content": "hello"}, validate=False)

        verifier = EventVerifier()
        report = verifier.verify_all_events()
        report_dict = report.to_dict()

        assert isinstance(report_dict, dict)
        assert "total_events" in report_dict
        assert "valid_events" in report_dict
        assert "corrupted_events" in report_dict
        assert "corrupted_event_ids" in report_dict
        assert "verification_timestamp" in report_dict
        assert "verification_status" in report_dict

    def test_verification_report_to_markdown_pass(self):
        """Test conversion of passing verification report to markdown."""
        log_event("TEST", "user", {"content": "hello"}, validate=False)

        verifier = EventVerifier()
        report = verifier.verify_all_events()
        markdown = report.to_markdown()

        assert "Event Integrity Verification Report" in markdown
        assert "PASS" in markdown
        assert "1" in markdown  # total events

    def test_verification_report_to_markdown_fail(self):
        """Test conversion of failing verification report to markdown."""
        # Create an event and corrupt it
        event_id = log_event("TEST", "user", {"content": "hello"}, validate=False)

        conn = _get_connection()
        try:
            conn.execute(
                "UPDATE system_events SET content_hash = ? WHERE event_id = ?",
                ("corrupted_hash", event_id),
            )
            conn.commit()
        finally:
            conn.close()

        verifier = EventVerifier()
        report = verifier.verify_all_events()
        markdown = report.to_markdown()

        assert "Event Integrity Verification Report" in markdown
        assert "FAIL" in markdown
        assert "Corrupted Events" in markdown
        assert event_id in markdown


class TestEventVerifierProperties:
    """Property-based tests for EventVerifier.

    **Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5**
    """

    @pytest.fixture(autouse=True)
    def setup_isolated_db(self, isolated_db):
        """Ensure isolated database for each property test."""
        yield

    @given(
        event_type=st.text(min_size=1, max_size=50),
        content=st.text(min_size=1, max_size=500),
    )
    @pytest.mark.slow
    @settings(max_examples=5)
    def test_all_events_have_valid_hashes(self, event_type, content):
        """Property: All events in ledger have valid hashes.

        **Validates: Requirement 9.2**
        """
        # Create event
        event_id = log_event(event_type, "user", {"content": content}, validate=False)

        # Verify event
        verifier = EventVerifier()
        is_valid, _ = verifier.verify_event(event_id)

        assert is_valid is True

    @given(
        content=st.text(min_size=1, max_size=100),
    )
    @pytest.mark.slow
    @settings(max_examples=5)
    def test_hash_computation_deterministic(self, content):
        """Property: Hash computation is deterministic.

        **Validates: Requirement 9.1**
        """
        # Create two events with same content
        event_id_1 = log_event("TEST", "user", {"content": content}, validate=False)
        event_id_2 = log_event("TEST", "user", {"content": content}, validate=False)

        # Get events from database
        conn = _get_connection()
        try:
            cursor = conn.execute(
                "SELECT content_hash FROM system_events WHERE event_id = ?",
                (event_id_1,),
            )
            hash_1 = cursor.fetchone()[0]

            cursor = conn.execute(
                "SELECT content_hash FROM system_events WHERE event_id = ?",
                (event_id_2,),
            )
            hash_2 = cursor.fetchone()[0]
        finally:
            conn.close()

        # Hashes should be identical for same content
        assert hash_1 == hash_2
