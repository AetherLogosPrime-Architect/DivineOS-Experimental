"""Tests for must-read gates.

Two load-bearing ones:

* ``test_read_once_then_quiet`` — the anti-wallpaper property. A must-read
  that re-arms every turn is a screen I clear rather than read, which is worse
  than no gate at all.
* ``test_unreadable_index_is_none_not_empty`` — the third word. A gate that
  cannot see its own pending list must not report "nothing pending".
"""

from __future__ import annotations

import pytest

from divineos.core import must_read as mr


def test_arm_then_pending_then_clear(tmp_path):
    p = mr.require_read("k", "room speaking", "because relevant", home=tmp_path)
    assert p is not None
    assert p.path.read_text(encoding="utf-8") == "room speaking"

    items, error = mr.pending(home=tmp_path)
    assert error is None
    assert [i.key for i in items] == ["k"]

    assert mr.mark_read(p.path, home=tmp_path) == ["k"]
    items, _ = mr.pending(home=tmp_path)
    assert items == []


def test_read_once_then_quiet(tmp_path):
    """Anti-wallpaper: identical content never re-arms after being read."""
    p = mr.require_read("k", "same words", "r", home=tmp_path)
    mr.mark_read(p.path, home=tmp_path)

    assert mr.require_read("k", "same words", "r", home=tmp_path) is None
    items, _ = mr.pending(home=tmp_path)
    assert items == []

    # Different content under the same key still arms — new words, new read.
    assert mr.require_read("k", "different words", "r", home=tmp_path) is not None


def test_rearming_unread_content_keeps_original_timestamp(tmp_path):
    a = mr.require_read("k", "words", "r", home=tmp_path)
    b = mr.require_read("k", "words", "r", home=tmp_path)
    assert a is not None and b is not None
    assert a.armed_at == b.armed_at  # a repeating surface cannot reset the clock


def test_empty_content_refused(tmp_path):
    """A must-read for nothing is a wall with no room behind it."""
    with pytest.raises(ValueError):
        mr.require_read("k", "   \n ", "r", home=tmp_path)


def test_unreadable_index_is_none_not_empty(tmp_path):
    mr.require_read("k", "words", "r", home=tmp_path)
    mr._index(tmp_path).write_text("{not json", encoding="utf-8")
    items, error = mr.pending(home=tmp_path)
    assert items is None  # NOT []
    assert "cannot read must-read index" in error


def test_arming_survives_unreadable_index(tmp_path):
    """Fail toward 'you must read this' — the safe direction for THIS gate."""
    mr._dir(tmp_path)
    mr._index(tmp_path).write_text("{corrupt", encoding="utf-8")
    p = mr.require_read("k", "words", "r", home=tmp_path)
    assert p is not None
    items, error = mr.pending(home=tmp_path)
    assert error is None
    assert [i.key for i in items] == ["k"]


def test_mark_read_on_unrelated_path_clears_nothing(tmp_path):
    mr.require_read("k", "words", "r", home=tmp_path)
    assert mr.mark_read(tmp_path / "somewhere-else.md", home=tmp_path) == []
    items, _ = mr.pending(home=tmp_path)
    assert [i.key for i in items] == ["k"]


def test_render_block_names_files_and_the_unlock(tmp_path):
    p = mr.require_read("k", "words", "the reason it matters", home=tmp_path)
    out = mr.render_block([p])
    assert "MUST-READ PENDING" in out
    assert "the reason it matters" in out
    assert str(p.path) in out
    assert "invoke the Read tool" in out
    # The honest limit must stay in the message.
    assert "cannot make you understand" in out


def test_multiple_pending_sorted_by_arm_time(tmp_path):
    mr.require_read("first", "a words here", "r", home=tmp_path)
    mr.require_read("second", "b words here", "r", home=tmp_path)
    items, _ = mr.pending(home=tmp_path)
    assert [i.key for i in items] == ["first", "second"]


class TestTheDoorMustOpenOntoSomething:
    """2026-09-20: a block was armed on a file nothing could open.

    The key came from a live caller and it was a good name for the situation
    -- a hook filename, which carries a colon. On Windows a colon in a path
    opens an alternate data stream rather than failing: the write returned
    cleanly, the existence check passed, and the folder held a zero-byte stub
    under the name truncated at the colon. The gate then demanded a file that
    could not be read, and because it clears on the attempt rather than the
    result, the failed read satisfied it.

    The real key is used here rather than a made-up one carrying a colon,
    because the made-up version proves only that I can construct the input I
    already fixed for.
    """

    REAL_KEY = "broken-hook:circle-first-compose-prime.sh"

    def test_the_key_that_broke_it_now_produces_a_readable_file(self, tmp_path):
        p = mr.require_read(self.REAL_KEY, "the room behind the door", "r", home=tmp_path)
        assert p is not None
        # The property is readability, not spelling: whatever the name became,
        # opening it must return what was stored.
        assert p.path.read_text(encoding="utf-8") == "the room behind the door"
        assert p.path.name in {f.name for f in p.path.parent.iterdir()}

    def test_the_armed_path_is_the_one_the_block_tells_me_to_open(self, tmp_path):
        mr.require_read(self.REAL_KEY, "the room behind the door", "r", home=tmp_path)
        items, _ = mr.pending(home=tmp_path)
        assert str(items[0].path) in mr.render_block(items)
        assert items[0].path.read_text(encoding="utf-8") == "the room behind the door"

    def test_a_write_that_leaves_nothing_readable_refuses_to_arm(self, tmp_path, monkeypatch):
        """The class, not the character. Any silently-empty write must refuse.

        A door onto nothing is worse than no door: it stops me, cannot let me
        through, and the thing it was guarding goes unread either way.
        """
        monkeypatch.setattr(mr.Path, "write_text", lambda self, *a, **k: None)
        with pytest.raises(OSError, match="is not openable"):
            mr.require_read("k", "content that never lands", "r", home=tmp_path)

    def test_the_guard_catches_it_even_with_the_sanitiser_bypassed(self, tmp_path, monkeypatch):
        """Belt and braces, each proven to hold on its own.

        The sanitiser stops the key becoming a stream. This asserts the guard
        behind it would have caught the same thing unaided -- which the first
        version of that guard did NOT, because it compared content only, and
        reading a stream back in Python succeeds. What was missing was a
        directory entry, and a directory entry is what the reader the block
        names actually needs.
        """
        monkeypatch.setattr(mr, "_safe_key", lambda k: k)
        with pytest.raises(OSError, match="is not openable"):
            mr.require_read(self.REAL_KEY, "the room behind the door", "r", home=tmp_path)
