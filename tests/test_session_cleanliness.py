"""Tests for Item 8 PR-2 — session_cleanliness tagging.

Covers:
    - Tag creation + idempotency
    - Sanity check: HIGH finding blocks tag
    - Sanity check: unresolved MEDIUM finding blocks tag
    - Resolved MEDIUM finding allows tag
    - Nonexistent round rejected
    - Untag with reason + ledger event
    - Untag without reason rejected
    - Query: is_session_clean, list, count, since filter
"""

from __future__ import annotations

import os
import time

import pytest


@pytest.fixture(autouse=True)
def _fresh_db(tmp_path):
    """Isolated DB per test with watchmen tables initialized."""
    os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
    from divineos.core.knowledge import init_knowledge_table
    from divineos.core.ledger import init_db
    from divineos.core.watchmen._schema import init_watchmen_tables

    init_db()
    init_knowledge_table()
    init_watchmen_tables()
    try:
        yield
    finally:
        os.environ.pop("DIVINEOS_DB", None)


def _make_round(round_id: str = "round-test-abc", actor: str = "user") -> None:
    """Create a bare audit round for tagging tests."""
    from divineos.core.knowledge import _get_connection

    conn = _get_connection()
    try:
        conn.execute(
            "INSERT INTO audit_rounds "
            "(round_id, created_at, actor, focus, expert_count, finding_count, notes, tier) "
            "VALUES (?, ?, ?, ?, 0, 0, '', 'STRONG')",
            (round_id, time.time(), actor, "test round focus"),
        )
        conn.commit()
    finally:
        conn.close()


def _add_finding(
    round_id: str, severity: str, status: str = "OPEN", finding_id: str | None = None
) -> str:
    """Add a finding directly to the DB (skips submit_finding's actor
    validation which would reject test actors)."""
    from divineos.core.knowledge import _get_connection

    fid = finding_id or f"find-{severity.lower()}-{int(time.time() * 1000) % 1000000}"
    conn = _get_connection()
    try:
        conn.execute(
            "INSERT INTO audit_findings "
            "(finding_id, round_id, created_at, actor, severity, category, title, "
            "description, status, tier) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'STRONG')",
            (fid, round_id, time.time(), "user", severity, "BEHAVIOR", "title", "desc", status),
        )
        conn.commit()
    finally:
        conn.close()
    return fid


class TestTagging:
    def test_tag_clean_round_succeeds(self) -> None:
        from divineos.core.watchmen.cleanliness import is_session_clean, tag_session_clean

        _make_round()
        tag_session_clean("session-001", "round-test-abc", "post-audit tag")
        assert is_session_clean("session-001")

    def test_tag_with_note_stores_note(self) -> None:
        from divineos.core.watchmen.cleanliness import list_clean_sessions, tag_session_clean

        _make_round()
        tag_session_clean("session-002", "round-test-abc", "specific rationale here")
        clean = list_clean_sessions()
        assert clean[0]["notes"] == "specific rationale here"

    def test_tag_idempotent_same_round(self) -> None:
        from divineos.core.watchmen.cleanliness import count_clean_sessions, tag_session_clean

        _make_round()
        tag_session_clean("session-003", "round-test-abc")
        tag_session_clean("session-003", "round-test-abc")  # second call = no-op
        assert count_clean_sessions() == 1

    def test_retag_by_different_clean_round_updates(self) -> None:
        from divineos.core.watchmen.cleanliness import list_clean_sessions, tag_session_clean

        _make_round("round-first")
        _make_round("round-second")
        tag_session_clean("session-004", "round-first", "first tag")
        tag_session_clean("session-004", "round-second", "re-affirmed")
        clean = list_clean_sessions()
        assert len(clean) == 1
        assert clean[0]["tagging_round_id"] == "round-second"
        assert clean[0]["notes"] == "re-affirmed"


class TestSanityChecks:
    def test_high_finding_blocks_tag(self) -> None:
        from divineos.core.watchmen.cleanliness import tag_session_clean

        _make_round()
        _add_finding("round-test-abc", "HIGH")
        with pytest.raises(ValueError, match="HIGH"):
            tag_session_clean("session-100", "round-test-abc")

    def test_unresolved_medium_finding_blocks_tag(self) -> None:
        from divineos.core.watchmen.cleanliness import tag_session_clean

        _make_round()
        _add_finding("round-test-abc", "MEDIUM", status="OPEN")
        with pytest.raises(ValueError, match="unresolved MEDIUM"):
            tag_session_clean("session-101", "round-test-abc")

    def test_resolved_medium_finding_allows_tag(self) -> None:
        from divineos.core.watchmen.cleanliness import is_session_clean, tag_session_clean

        _make_round()
        _add_finding("round-test-abc", "MEDIUM", status="RESOLVED")
        tag_session_clean("session-102", "round-test-abc")
        assert is_session_clean("session-102")

    def test_low_finding_does_not_block(self) -> None:
        from divineos.core.watchmen.cleanliness import is_session_clean, tag_session_clean

        _make_round()
        _add_finding("round-test-abc", "LOW", status="OPEN")
        tag_session_clean("session-103", "round-test-abc")
        assert is_session_clean("session-103")

    def test_nonexistent_round_rejected(self) -> None:
        from divineos.core.watchmen.cleanliness import tag_session_clean

        with pytest.raises(ValueError, match="does not exist"):
            tag_session_clean("session-200", "round-bogus-id")


class TestUntagging:
    def test_untag_with_reason_removes(self) -> None:
        from divineos.core.watchmen.cleanliness import (
            is_session_clean,
            tag_session_clean,
            untag_session_clean,
        )

        _make_round()
        tag_session_clean("session-300", "round-test-abc")
        removed = untag_session_clean("session-300", reason="audit round was flawed")
        assert removed is True
        assert not is_session_clean("session-300")

    def test_untag_without_reason_rejected(self) -> None:
        from divineos.core.watchmen.cleanliness import untag_session_clean

        with pytest.raises(ValueError, match="non-empty reason"):
            untag_session_clean("session-400", reason="")

    def test_untag_emits_ledger_event(self) -> None:
        from divineos.core.ledger import get_events
        from divineos.core.watchmen.cleanliness import tag_session_clean, untag_session_clean

        _make_round()
        tag_session_clean("session-500", "round-test-abc")
        untag_session_clean("session-500", reason="flawed audit round")
        events = get_events(event_type="SESSION_CLEANLINESS_UNTAGGED", limit=5)
        assert len(events) >= 1
        assert events[-1]["payload"]["session_id"] == "session-500"
        assert "flawed" in events[-1]["payload"]["reason"]

    def test_untag_nonexistent_returns_false(self) -> None:
        from divineos.core.watchmen.cleanliness import untag_session_clean

        removed = untag_session_clean("session-600", reason="speculative")
        assert removed is False


class TestQueries:
    def test_is_session_clean_false_by_default(self) -> None:
        from divineos.core.watchmen.cleanliness import is_session_clean

        assert not is_session_clean("never-tagged")

    def test_list_clean_sessions_returns_all(self) -> None:
        from divineos.core.watchmen.cleanliness import list_clean_sessions, tag_session_clean

        _make_round()
        for i in range(5):
            tag_session_clean(f"session-{i:03d}", "round-test-abc")
        clean = list_clean_sessions()
        assert len(clean) == 5

    def test_list_clean_sessions_since_filter(self) -> None:
        from divineos.core.watchmen.cleanliness import list_clean_sessions, tag_session_clean

        _make_round()
        tag_session_clean("session-old", "round-test-abc")
        future = time.time() + 10000
        clean_since_future = list_clean_sessions(since=future)
        assert clean_since_future == []

    def test_list_clean_sessions_limit_respected(self) -> None:
        from divineos.core.watchmen.cleanliness import list_clean_sessions, tag_session_clean

        _make_round()
        for i in range(10):
            tag_session_clean(f"session-{i:03d}", "round-test-abc")
        clean = list_clean_sessions(limit=3)
        assert len(clean) == 3

    def test_count_clean_sessions(self) -> None:
        from divineos.core.watchmen.cleanliness import count_clean_sessions, tag_session_clean

        _make_round()
        for i in range(7):
            tag_session_clean(f"session-{i:03d}", "round-test-abc")
        assert count_clean_sessions() == 7

    def test_count_clean_sessions_since_filter(self) -> None:
        from divineos.core.watchmen.cleanliness import count_clean_sessions, tag_session_clean

        _make_round()
        tag_session_clean("session-one", "round-test-abc")
        future = time.time() + 10000
        assert count_clean_sessions(since=future) == 0

    def test_list_clean_sessions_includes_round_focus(self) -> None:
        """Ergonomics fix (claim 2026-04-24 18:43): callers see round focus
        text without a second lookup."""
        from divineos.core.watchmen.cleanliness import list_clean_sessions, tag_session_clean

        _make_round()
        tag_session_clean("session-with-focus", "round-test-abc")
        clean = list_clean_sessions()
        assert len(clean) == 1
        assert clean[0]["round_focus"] == "test round focus"

    def test_list_clean_sessions_focus_is_null_when_round_deleted(self) -> None:
        """LEFT JOIN preserves the cleanliness row when the round is gone."""
        from divineos.core.knowledge import _get_connection
        from divineos.core.watchmen.cleanliness import list_clean_sessions, tag_session_clean

        _make_round()
        tag_session_clean("session-orphan", "round-test-abc")
        conn = _get_connection()
        try:
            conn.execute("DELETE FROM audit_rounds WHERE round_id = 'round-test-abc'")
            conn.commit()
        finally:
            conn.close()
        clean = list_clean_sessions()
        assert len(clean) == 1
        assert clean[0]["round_focus"] is None


class TestTaggingTOCTOU:
    """TOCTOU close (claim 2026-04-24 18:43): blocking-check + INSERT now
    share an IMMEDIATE-mode transaction so concurrent HIGH findings can't
    sneak between the read and the write."""

    def test_tag_uses_immediate_transaction(self) -> None:
        """The tag write should still succeed when no concurrent writer exists."""
        from divineos.core.watchmen.cleanliness import is_session_clean, tag_session_clean

        _make_round()
        tag_session_clean("session-tx", "round-test-abc")
        assert is_session_clean("session-tx")

    def test_high_finding_added_before_tag_blocks(self) -> None:
        """Pre-existing HIGH findings still block — sanity check that the
        TOCTOU refactor didn't break the basic blocking semantics."""
        import pytest

        from divineos.core.watchmen.cleanliness import is_session_clean, tag_session_clean

        _make_round()
        _add_finding("round-test-abc", "HIGH")
        with pytest.raises(ValueError, match="HIGH finding"):
            tag_session_clean("session-blocked", "round-test-abc")
        assert not is_session_clean("session-blocked")
