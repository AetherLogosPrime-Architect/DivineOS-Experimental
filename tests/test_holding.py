"""Tests for the holding room — pre-categorical reception space."""

import pytest

from divineos.core.holding import (
    age_holding,
    format_holding,
    get_holding,
    hold,
    holding_stats,
    init_holding_table,
    promote,
    MAX_SESSIONS_UNREVIEWED,
)


@pytest.fixture(autouse=True)
def _setup():
    init_holding_table()


class TestHold:
    """Putting things in the holding room."""

    def test_hold_returns_id(self):
        item_id = hold("Something I noticed but don't know what to do with")
        assert item_id.startswith("hold-")

    def test_hold_with_hint(self):
        hold("Andrew's teaching style is Socratic", hint="might be a relationship note")
        items = get_holding()
        assert items[0]["hint"] == "might be a relationship note"

    def test_hold_with_source(self):
        hold("Half-formed thought about gates", source="session")
        items = get_holding()
        assert items[0]["source"] == "session"

    def test_multiple_items(self):
        hold("First thing")
        hold("Second thing")
        hold("Third thing")
        items = get_holding()
        assert len(items) == 3


class TestGetHolding:
    """Retrieving items from the holding room."""

    def test_empty_room(self):
        items = get_holding()
        assert items == []

    def test_only_active_items(self):
        item_id = hold("Active item")
        promote(item_id, "knowledge")
        hold("Still here")
        items = get_holding()
        assert len(items) == 1
        assert items[0]["content"] == "Still here"

    def test_excludes_stale_by_default(self):
        hold("Will go stale")
        # Age it past the threshold
        from divineos.core.knowledge import _get_connection

        conn = _get_connection()
        try:
            conn.execute(
                "UPDATE holding_room SET sessions_seen = ?, stale = 1",
                (MAX_SESSIONS_UNREVIEWED,),
            )
            conn.commit()
        finally:
            conn.close()
        items = get_holding()
        assert len(items) == 0

    def test_include_stale(self):
        hold("Will go stale")
        from divineos.core.knowledge import _get_connection

        conn = _get_connection()
        try:
            conn.execute("UPDATE holding_room SET stale = 1")
            conn.commit()
        finally:
            conn.close()
        items = get_holding(include_stale=True)
        assert len(items) == 1


class TestPromote:
    """Moving items out of holding."""

    def test_promote_returns_true(self):
        item_id = hold("Ready to be knowledge")
        assert promote(item_id, "knowledge") is True

    def test_promoted_item_disappears_from_active(self):
        item_id = hold("Promote me")
        promote(item_id, "opinion")
        items = get_holding()
        assert len(items) == 0

    def test_double_promote_fails(self):
        item_id = hold("Already promoted")
        promote(item_id, "knowledge")
        assert promote(item_id, "opinion") is False

    def test_promote_nonexistent(self):
        assert promote("hold-doesntexist", "knowledge") is False

    def test_promote_to_discarded(self):
        """Discarding is a valid promotion — it went somewhere."""
        item_id = hold("Not useful after all")
        assert promote(item_id, "discarded") is True


class TestAging:
    """Items age between sleep cycles."""

    def test_age_increments_sessions(self):
        hold("Aging item")
        age_holding()
        items = get_holding()
        assert items[0]["sessions_seen"] == 1

    def test_items_go_stale(self):
        hold("Will go stale eventually")
        for _ in range(MAX_SESSIONS_UNREVIEWED):
            age_holding()
        items = get_holding()
        assert len(items) == 0  # stale items hidden by default

    def test_age_returns_stale_count(self):
        hold("Stale candidate")
        # Fast-forward to just before threshold
        from divineos.core.knowledge import _get_connection

        conn = _get_connection()
        try:
            conn.execute(
                "UPDATE holding_room SET sessions_seen = ?",
                (MAX_SESSIONS_UNREVIEWED - 1,),
            )
            conn.commit()
        finally:
            conn.close()
        newly_stale = age_holding()
        assert newly_stale == 1

    def test_promoted_items_dont_age(self):
        item_id = hold("Already promoted")
        promote(item_id, "knowledge")
        age_holding()
        # Should still show 0 sessions_seen (wasn't aged)
        from divineos.core.knowledge import _get_connection

        conn = _get_connection()
        try:
            row = conn.execute(
                "SELECT sessions_seen FROM holding_room WHERE item_id = ?",
                (item_id,),
            ).fetchone()
            assert row[0] == 0
        finally:
            conn.close()


class TestStats:
    """Holding room statistics."""

    def test_empty_stats(self):
        stats = holding_stats()
        assert stats["total"] == 0
        assert stats["active"] == 0

    def test_stats_with_items(self):
        hold("Active")
        item_id = hold("Will promote")
        promote(item_id, "knowledge")
        stats = holding_stats()
        assert stats["active"] == 1
        assert stats["promoted"] == 1
        assert stats["total"] == 2


class TestFormat:
    """Display formatting."""

    def test_empty_format(self):
        result = format_holding()
        assert "empty" in result.lower()

    def test_format_shows_content(self):
        hold("My half-formed thought", hint="maybe knowledge")
        result = format_holding()
        assert "half-formed" in result
        assert "maybe knowledge" in result
