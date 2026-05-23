"""Tests for event integrity verification system."""

import pytest
from hypothesis_compat import HAS_HYPOTHESIS, given, settings, st

from divineos.core.event_verifier import EventVerifier, VerificationReport
from divineos.core.ledger import (
    _get_connection,
    init_db,
    log_event,
)

# Skip all tests in this module if hypothesis is not installed
pytestmark = pytest.mark.skipif(not HAS_HYPOTHESIS, reason="hypothesis not installed")


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


# Adversarial input table — the boundaries where event hashing could plausibly
# break, tested DETERMINISTICALLY. This replaces the random-fuzz property tests
# that intermittently flaked the push gate (2026-05-20, 2026-05-23). Council
# walk 2026-05-23 (Dijkstra/Popper/Knuth/Schneier/Polya): the content-hash path
# is correct by construction (write and verify serialize the payload identically
# and SHA256 it), proven further by 7000 curated inputs carrying no real bug —
# so the harm was nondeterminism (random unicode x random test order), not a
# data-integrity defect. A fixed boundary table tests the SAME property but
# passes-always-or-fails-always (a reliable falsifier), covers the dangerous
# inputs explicitly (Knuth boundaries), and its assertions dump input + reason
# so any future failure is instantly root-caused (Schneier: surface the
# non-logic failure modes too).
_ADVERSARIAL_CONTENT = [
    "simple",
    "",
    " ",
    "a",
    "x" * 5000,
    "café résumé naïve",  # latin-1 supplement
    "日本語テスト",  # CJK
    "emoji 😀🔥🜂",  # astral plane
    "\t\r\n",  # whitespace controls
    "\x00",  # bare NUL
    "a\x00b",  # embedded NUL
    "\x01\x1f\x7f",  # control chars
    '{"nested": "json", "n": 1}',  # JSON-shaped content
    'quote"and\\backslash/slash',  # JSON-escaping chars
    "ﬀ ﬁ ﬂ",  # ligatures (NFKC-foldable)
    "​‍﻿",  # zero-width joiners + BOM
]

_ADVERSARIAL_EVENT_TYPES = ["T", "EVENT_TYPE", "a-b_c.d", "日本", "with space"]


class TestEventVerifierProperties:
    """Boundary tests for event-hash integrity (formerly random-fuzz).

    **Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5**

    See _ADVERSARIAL_CONTENT above for why these are deterministic tables
    rather than Hypothesis fuzz. A reproducible fuzz test (derandomized so it
    can never flake the gate) is kept at the end for continued exploration.
    """

    @pytest.fixture(autouse=True)
    def setup_isolated_db(self, isolated_db):
        """Ensure isolated database for each test."""
        yield

    @pytest.mark.parametrize("content", _ADVERSARIAL_CONTENT)
    @pytest.mark.parametrize("event_type", _ADVERSARIAL_EVENT_TYPES)
    def test_logged_event_hash_verifies(self, event_type, content):
        """Property: a logged event's stored hash always re-verifies.

        **Validates: Requirement 9.2**
        """
        event_id = log_event(event_type, "user", {"content": content}, validate=False)
        is_valid, reason = EventVerifier().verify_event(event_id)
        assert is_valid, (
            f"hash verify failed: event_type={event_type!r} content={content!r} "
            f"reason={reason!r} event_id={event_id!r}"
        )

    @pytest.mark.parametrize("content", _ADVERSARIAL_CONTENT)
    def test_hash_computation_deterministic(self, content):
        """Property: identical content yields an identical stored hash.

        **Validates: Requirement 9.1**
        """
        event_id_1 = log_event("TEST", "user", {"content": content}, validate=False)
        event_id_2 = log_event("TEST", "user", {"content": content}, validate=False)
        conn = _get_connection()
        try:
            hash_1 = conn.execute(
                "SELECT content_hash FROM system_events WHERE event_id = ?", (event_id_1,)
            ).fetchone()[0]
            hash_2 = conn.execute(
                "SELECT content_hash FROM system_events WHERE event_id = ?", (event_id_2,)
            ).fetchone()[0]
        finally:
            conn.close()
        assert hash_1 == hash_2, (
            f"non-deterministic hash for content={content!r}: {hash_1} != {hash_2}"
        )

    # Reproducible fuzz (option c, council walk 2026-05-23): derandomize=True
    # fixes Hypothesis's example set, so this explores 200 generated inputs but
    # CANNOT flake — it passes always or fails always on a given code state.
    # Keeps open-ended exploration without ever blocking a push on a seed
    # roulette. codec="utf-8" excludes lone surrogates (not valid Unicode;
    # 2026-05-20 fix). If this ever fails, the message names the exact input.
    @given(
        event_type=st.text(st.characters(codec="utf-8"), min_size=1, max_size=50),
        content=st.text(st.characters(codec="utf-8"), min_size=1, max_size=500),
    )
    @pytest.mark.slow
    @settings(max_examples=200, derandomize=True)
    def test_fuzz_logged_event_hash_verifies(self, event_type, content):
        """Reproducible-fuzz companion to the deterministic boundary table."""
        event_id = log_event(event_type, "user", {"content": content}, validate=False)
        is_valid, reason = EventVerifier().verify_event(event_id)
        assert is_valid, (
            f"fuzz hash verify failed: event_type={event_type!r} content={content!r} "
            f"reason={reason!r}"
        )
