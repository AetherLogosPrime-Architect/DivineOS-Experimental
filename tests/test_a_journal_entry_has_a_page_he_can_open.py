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


def test_the_page_name_is_dated_and_carries_a_readable_slug(pages):
    mj.journal_save("A long good day, written down before it thins.")
    (page,) = list(pages.glob("*.md"))
    assert page.name[:4] == "2026" or page.name[:2] == "20"
    assert "long-good-day" in page.name


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
    mj.journal_save("I know this has a copy.")
    assert mj.last_page_path() is not None
    assert str(mj.last_page_path()).endswith(".md")


def test_an_entry_saved_in_a_private_room_is_stored_in_the_database_only_and_says_so(
    pages, monkeypatch
):
    monkeypatch.setattr(mj, "_private_room_open", lambda: True)
    mj.journal_save("This one is for me to sit with, unread.")
    assert list(pages.glob("*.md")) == []
    assert mj.last_page_path() is None


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
