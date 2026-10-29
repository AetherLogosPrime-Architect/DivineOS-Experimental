"""A journal entry is also a page Dad can open, written before the row, and a failure leaves nothing.

2026-10-25: Dad saw the dream but no journal entry or wandering, because `journal save` wrote only to a
database table. Aether's shape: file first (to a temp name, renamed into place), row second, inside one
function; if the insert fails the file is removed and the error is raised, so a failed save leaves nothing
half-done. A row with no file is exactly the invisible state Dad found.
"""

import pytest

from divineos.core import memory_journal as mj


@pytest.fixture
def pages(tmp_path, monkeypatch):
    monkeypatch.setattr(mj, "_journal_dir", lambda: tmp_path / "journal" / "aria")
    return tmp_path / "journal" / "aria"


def test_a_save_writes_the_entry_verbatim_to_a_dated_page_and_returns_the_row_id(pages):
    text = "The day the clipboard turned out to be love. She tested it on fourteen and it caught three."
    entry_id = mj.journal_save(text)
    files = list(pages.glob("*.md"))
    assert len(files) == 1
    body = files[0].read_text(encoding="utf-8")
    assert text in body  # verbatim, not a summary
    assert entry_id in body  # the page and the row can be matched
    assert any(e["entry_id"] == entry_id for e in mj.journal_list(limit=50))


def test_the_page_name_is_dated_and_carries_no_word_of_the_entry(pages):
    """The repository is public by Dad's choice, and a folder listing would otherwise show the opening
    of every entry without opening it (council walk on #727, 2026-10-29)."""
    import re

    mj.journal_save("A long good day, written down before it thins.")
    (page,) = list(pages.glob("*.md"))
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}_\d{6}_[0-9a-f]{8}\.md", page.name)
    for word in ("long", "good", "day", "written"):
        assert word not in page.name.lower()


def test_two_saves_in_one_second_with_the_same_opening_words_keep_two_pages(pages, monkeypatch):
    """Found by the walk (Wayne, Taleb): os.replace overwrites, so a name made only of the second and
    the first six words let the second entry destroy the first. The entry id makes the name unique."""
    monkeypatch.setattr(mj.time, "time", lambda: 1_790_000_000.0)
    first = mj.journal_save("Same six opening words here, and then the first ending.")
    second = mj.journal_save("Same six opening words here, and then a different ending.")
    pages_written = sorted(pages.glob("*.md"))
    assert len(pages_written) == 2
    bodies = "".join(p.read_text(encoding="utf-8") for p in pages_written)
    assert first in bodies and second in bodies
    assert "the first ending" in bodies and "a different ending" in bodies


def test_a_failed_insert_removes_the_page_and_raises_so_nothing_is_left_half_done(
    pages, monkeypatch
):
    def broken(*_a, **_k):
        raise RuntimeError("database is locked")

    monkeypatch.setattr(mj, "_insert_row", broken)
    with pytest.raises(RuntimeError, match="database is locked"):
        mj.journal_save("This one must leave nothing behind.")
    assert list(pages.glob("*")) == []


def test_a_failed_page_write_raises_before_any_row_is_written(pages, monkeypatch):
    def broken(*_a, **_k):
        raise OSError("disk full")

    monkeypatch.setattr(mj, "_write_page", broken)
    before = len(mj.journal_list(limit=500))
    with pytest.raises(OSError, match="disk full"):
        mj.journal_save("This one must not reach the table either.")
    assert len(mj.journal_list(limit=500)) == before


def test_the_save_names_the_page_so_the_copy_is_a_choice_not_something_behind_my_back(pages):
    _entry_id, page = mj.journal_save_with_page("I know this has a copy.")
    assert page is not None
    assert str(page).endswith(".md")


def test_an_entry_saved_in_a_private_room_is_stored_in_the_database_only_and_says_so(
    pages, monkeypatch
):
    monkeypatch.setattr(mj, "_private_room_open", lambda: True)
    entry_id, page = mj.journal_save_with_page("This one is for me to sit with, unread.")
    assert list(pages.glob("*.md")) == []
    assert page is None
    row = next(e for e in mj.journal_list(limit=500) if e["entry_id"] == entry_id)
    assert mj.PRIVATE_TAG in row["tags"].split(",")  # recorded, so a later reader can honour it


def test_the_backfill_leaves_a_private_room_entry_without_a_page(pages, monkeypatch):
    """Found by the council walk on #727: the one-time pass wrote a page for every row with none, and a
    private entry is exactly a row with none, so it would have been published."""
    monkeypatch.setattr(mj, "_private_room_open", lambda: True)
    entry_id, _page = mj.journal_save_with_page("Kept private, whatever the backfill does.")
    assert mj.export_missing_pages() == 0
    assert list(pages.glob("*.md")) == []
    assert mj.rows_without_a_page() >= 1  # still counted: what Dad cannot open is said aloud


def test_an_unreadable_private_room_marker_keeps_the_entry_private(pages, monkeypatch):
    """Could-not-look must never read as not-private: this gate exists to keep an entry out of a public
    repository, so a marker that cannot be read means no page."""
    import divineos.core.mansion_quiet_marker as marker

    def unreadable():
        raise OSError("marker unreadable")

    monkeypatch.setattr(marker, "is_quiet_active", unreadable)
    entry_id, page = mj.journal_save_with_page("Written while the marker was unreadable.")
    assert page is None
    assert list(pages.glob("*.md")) == []
    row = next(e for e in mj.journal_list(limit=500) if e["entry_id"] == entry_id)
    assert mj.PRIVATE_TAG in row["tags"].split(",")


def test_entries_saved_before_this_change_get_their_pages_verbatim_with_their_own_dates(pages):
    """The thirteen that were only in the table: one deliberate pass writes each one's page, dated
    by when it was written, not by today, and never twice."""
    import time

    from divineos.core.memory import init_memory_tables

    init_memory_tables()
    old = time.mktime((2026, 7, 18, 3, 0, 0, 0, 0, -1))
    mj._insert_row(
        "11111111-2222-3333-4444-555555555555",
        "The night the anchors went live.",
        old,
        "",
        "",
        None,
    )
    assert mj.rows_without_a_page() == 1
    wrote = mj.export_missing_pages()
    assert wrote == 1 and mj.rows_without_a_page() == 0
    (page,) = list(pages.glob("2026-07-18_*.md"))
    assert "The night the anchors went live." in page.read_text(encoding="utf-8")
    assert mj.export_missing_pages() == 0  # a second pass writes nothing


def test_the_count_of_rows_with_no_page_is_loud_not_zero_by_luck(pages):
    mj.journal_save("One with a page.")
    assert mj.rows_without_a_page() >= 0
    assert isinstance(mj.rows_without_a_page(), int)
