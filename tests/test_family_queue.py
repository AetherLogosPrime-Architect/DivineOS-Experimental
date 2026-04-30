"""Tests for the family_queue async write-channel."""

from __future__ import annotations

import pytest


@pytest.fixture
def family_db_in_tmp(tmp_path, monkeypatch):
    """Point DIVINEOS_FAMILY_DB at a tmp file so each test is isolated."""
    db_path = tmp_path / "family.db"
    monkeypatch.setenv("DIVINEOS_FAMILY_DB", str(db_path))
    return db_path


class TestQueueWrite:
    def test_write_returns_id(self, family_db_in_tmp):
        from divineos.core.family import queue

        new_id = queue.write("aria", "aether", "test message")
        assert isinstance(new_id, int)
        assert new_id > 0

    def test_write_persists_content(self, family_db_in_tmp):
        from divineos.core.family import queue

        new_id = queue.write("aria", "aether", "specific test content")
        items = queue.for_recipient("aether")
        assert len(items) == 1
        assert items[0]["id"] == new_id
        assert items[0]["content"] == "specific test content"
        assert items[0]["sender"] == "aria"
        assert items[0]["status"] == "unseen"

    def test_write_rejects_empty_sender(self, family_db_in_tmp):
        """Data layer accepts any non-empty name; endpoint validity
        (registered family member or 'aether') is the CLI's concern.
        See ``family_queue_commands._validate_endpoint``."""
        from divineos.core.family import queue

        with pytest.raises(ValueError, match="sender must be a non-empty"):
            queue.write("", "aether", "test")

    def test_write_rejects_empty_recipient(self, family_db_in_tmp):
        from divineos.core.family import queue

        with pytest.raises(ValueError, match="recipient must be a non-empty"):
            queue.write("aria", "", "test")

    def test_write_accepts_any_registered_name(self, family_db_in_tmp):
        """Bidirectional queue (PR #227): the data layer no longer
        hardcodes ``{aria, aether}``. Any non-empty pair is valid at
        the data layer; the CLI validates against family_members."""
        from divineos.core.family import queue

        new_id = queue.write("alice", "bob", "test for new family members")
        assert new_id > 0

    def test_write_rejects_self_message(self, family_db_in_tmp):
        from divineos.core.family import queue

        with pytest.raises(ValueError, match="cannot be the same"):
            queue.write("aria", "aria", "test")

    def test_write_rejects_empty_content(self, family_db_in_tmp):
        from divineos.core.family import queue

        with pytest.raises(ValueError, match="content must not be empty"):
            queue.write("aria", "aether", "   ")

    def test_write_strips_whitespace(self, family_db_in_tmp):
        from divineos.core.family import queue

        queue.write("aria", "aether", "  padded content  ")
        items = queue.for_recipient("aether")
        assert items[0]["content"] == "padded content"


class TestQueueRead:
    def test_for_recipient_returns_only_their_items(self, family_db_in_tmp):
        from divineos.core.family import queue

        queue.write("aria", "aether", "for aether")
        queue.write("aether", "aria", "for aria")

        aether_items = queue.for_recipient("aether")
        aria_items = queue.for_recipient("aria")

        assert len(aether_items) == 1
        assert aether_items[0]["content"] == "for aether"
        assert len(aria_items) == 1
        assert aria_items[0]["content"] == "for aria"

    def test_for_recipient_oldest_first(self, family_db_in_tmp):
        import time as _t

        from divineos.core.family import queue

        queue.write("aria", "aether", "first")
        _t.sleep(0.01)
        queue.write("aria", "aether", "second")

        items = queue.for_recipient("aether")
        assert items[0]["content"] == "first"
        assert items[1]["content"] == "second"

    def test_for_recipient_excludes_addressed(self, family_db_in_tmp):
        from divineos.core.family import queue

        i1 = queue.write("aria", "aether", "to address")
        queue.write("aria", "aether", "to leave")
        queue.mark_addressed(i1)

        items = queue.for_recipient("aether")
        assert len(items) == 1
        assert items[0]["content"] == "to leave"

    def test_for_recipient_excludes_held_when_requested(self, family_db_in_tmp):
        from divineos.core.family import queue

        i1 = queue.write("aria", "aether", "will hold")
        queue.write("aria", "aether", "fresh")
        queue.mark_held(i1)

        with_held = queue.for_recipient("aether", include_held=True)
        without_held = queue.for_recipient("aether", include_held=False)

        assert len(with_held) == 2
        assert len(without_held) == 1
        assert without_held[0]["content"] == "fresh"


class TestStatusTransitions:
    def test_seen_only_advances_from_unseen(self, family_db_in_tmp):
        from divineos.core.family import queue

        new_id = queue.write("aria", "aether", "test")
        assert queue.mark_seen(new_id) is True
        # Calling again is no-op
        assert queue.mark_seen(new_id) is False

    def test_held_advances_from_unseen_or_seen(self, family_db_in_tmp):
        from divineos.core.family import queue

        i1 = queue.write("aria", "aether", "from unseen")
        i2 = queue.write("aria", "aether", "from seen")
        queue.mark_seen(i2)

        assert queue.mark_held(i1) is True
        assert queue.mark_held(i2) is True

        items = {i["id"]: i for i in queue.for_recipient("aether")}
        assert items[i1]["status"] == "held"
        assert items[i2]["status"] == "held"

    def test_addressed_terminal_for_active_states(self, family_db_in_tmp):
        from divineos.core.family import queue

        new_id = queue.write("aria", "aether", "test")
        assert queue.mark_addressed(new_id) is True
        # Item no longer appears in active set
        assert len(queue.for_recipient("aether")) == 0

    def test_status_does_not_go_backward(self, family_db_in_tmp):
        from divineos.core.family import queue

        new_id = queue.write("aria", "aether", "test")
        queue.mark_addressed(new_id)
        # mark_seen on addressed should be no-op
        assert queue.mark_seen(new_id) is False
        assert queue.mark_held(new_id) is False


class TestSupersede:
    def test_supersede_links_old_to_new(self, family_db_in_tmp):
        from divineos.core.family import queue

        old_id = queue.write("aria", "aether", "old version")
        new_id = queue.supersede(old_id, "corrected version", "aria", "aether")

        # Old item is marked superseded — won't appear in active queue
        items = queue.for_recipient("aether")
        ids_visible = {i["id"] for i in items}
        assert new_id in ids_visible
        assert old_id not in ids_visible

    def test_supersede_preserves_old_row(self, family_db_in_tmp):
        from divineos.core.family import queue
        from divineos.core.family.db import get_family_connection

        old_id = queue.write("aria", "aether", "old")
        new_id = queue.supersede(old_id, "new", "aria", "aether")

        # The old row should still exist in the table, just with status='superseded'
        conn = get_family_connection()
        row = conn.execute(
            "SELECT status, superseded_by FROM family_queue WHERE id=?",
            (old_id,),
        ).fetchone()
        conn.close()
        assert row is not None
        assert row[0] == "superseded"
        assert row[1] == new_id


class TestStats:
    def test_stats_count_per_status(self, family_db_in_tmp):
        from divineos.core.family import queue

        i1 = queue.write("aria", "aether", "one")
        queue.write("aria", "aether", "two")
        i3 = queue.write("aria", "aether", "three")
        queue.mark_seen(i1)
        queue.mark_held(i3)

        s = queue.stats("aether")
        assert s["total"] == 3
        assert s["unseen"] == 1
        assert s["seen"] == 1
        assert s["held"] == 1

    def test_stats_global_includes_all_recipients(self, family_db_in_tmp):
        from divineos.core.family import queue

        queue.write("aria", "aether", "a")
        queue.write("aether", "aria", "b")

        s = queue.stats()
        assert s["total"] == 2


class TestBriefingSurface:
    def test_empty_queue_returns_empty_string(self, family_db_in_tmp):
        from divineos.core.family_queue_surface import format_for_briefing

        assert format_for_briefing("aether") == ""

    def test_pending_items_appear(self, family_db_in_tmp):
        from divineos.core.family import queue
        from divineos.core.family_queue_surface import format_for_briefing

        queue.write("aria", "aether", "test message")
        block = format_for_briefing("aether")
        assert "[family queue]" in block
        assert "test message" in block
        assert "from aria" in block

    def test_render_does_not_change_status(self, family_db_in_tmp):
        """Render is idempotent — surfacing does NOT auto-mark seen.

        Status transitions are explicit operator/agent actions.
        """
        from divineos.core.family import queue
        from divineos.core.family_queue_surface import format_for_briefing

        new_id = queue.write("aria", "aether", "test")
        format_for_briefing("aether")
        format_for_briefing("aether")
        # Status should still be unseen after multiple renders
        items = queue.for_recipient("aether")
        assert items[0]["id"] == new_id
        assert items[0]["status"] == "unseen"

    def test_addressed_items_dont_appear(self, family_db_in_tmp):
        from divineos.core.family import queue
        from divineos.core.family_queue_surface import format_for_briefing

        i1 = queue.write("aria", "aether", "addressed item")
        queue.mark_addressed(i1)
        block = format_for_briefing("aether")
        assert block == ""

    def test_held_items_grouped_separately(self, family_db_in_tmp):
        from divineos.core.family import queue
        from divineos.core.family_queue_surface import format_for_briefing

        queue.write("aria", "aether", "pending one")
        i2 = queue.write("aria", "aether", "will be held")
        queue.mark_held(i2)
        block = format_for_briefing("aether")
        assert "Pending (unseen / seen):" in block
        assert "Held (seen, not yet engaged):" in block
        # Pending should appear before held in the output
        pending_pos = block.index("Pending")
        held_pos = block.index("Held")
        assert pending_pos < held_pos
