"""A journal save returns the page it wrote, and keeps no memory of it between calls.

2026-10-26, Aether's attack on #727: `_LAST_PAGE` was a module variable set by one save and read later by
`last_page_path()`. A caller that asked without having just saved, or that caught a failed save, was
handed the PREVIOUS entry's page and printed it as current: a wrong answer that looks right. State that
outlives the call is the defect class this change exists to remove, so the save now returns its page,
and nothing outside can ask for a path it did not just earn.
"""

import pytest

from divineos.core import memory_journal as mj


@pytest.fixture
def pages(tmp_path, monkeypatch):
    monkeypatch.setattr(mj, "_journal_dir", lambda: tmp_path / "journal" / "aria")
    return tmp_path / "journal" / "aria"


def test_the_save_hands_back_the_row_id_and_the_page_it_wrote(pages):
    entry_id, page = mj.journal_save_with_page("A page I can be handed, not asked for later.")
    assert page is not None and page.exists() and page.parent == pages
    assert "A page I can be handed" in page.read_text(encoding="utf-8")
    assert any(e["entry_id"] == entry_id for e in mj.journal_list(limit=50))


def test_a_private_room_hands_back_no_page(pages, monkeypatch):
    monkeypatch.setattr(mj, "_private_room_open", lambda: True)
    entry_id, page = mj.journal_save_with_page("Kept in the database only.")
    assert page is None and list(pages.glob("*.md")) == []
    assert any(e["entry_id"] == entry_id for e in mj.journal_list(limit=50))


def test_a_failed_save_then_a_private_save_never_returns_an_older_page(pages, monkeypatch):
    _first_id, first_page = mj.journal_save_with_page("The first entry, with a page.")
    assert first_page is not None
    with monkeypatch.context() as broken:

        def explode(*_a, **_k):
            raise RuntimeError("database is locked")

        broken.setattr(mj, "_insert_row", explode)
        with pytest.raises(RuntimeError):
            mj.journal_save_with_page("This one fails and leaves nothing.")
    monkeypatch.setattr(mj, "_private_room_open", lambda: True)
    _id, page = mj.journal_save_with_page("A private one after the failure.")
    assert page is None  # never the first entry's page


def test_the_old_way_of_asking_for_the_last_page_is_gone():
    assert not hasattr(mj, "last_page_path")
    assert not hasattr(mj, "_LAST_PAGE")


def test_journal_save_still_returns_only_the_id_for_everything_else_that_calls_it(pages):
    result = mj.journal_save("Old callers still get a plain id back.")
    assert isinstance(result, str) and len(result) == 36


def test_the_two_seats_get_their_own_folders_and_never_each_others(monkeypatch):
    """Aether's request: my seat writes to journal/aria, his to journal/aether, by the same code."""
    from divineos.core import sibling_audit_rounds

    monkeypatch.delenv("DIVINEOS_JOURNAL_DIR", raising=False)
    monkeypatch.setattr(sibling_audit_rounds, "this_seat", lambda: "aria")
    aria = mj._journal_dir()
    monkeypatch.setattr(sibling_audit_rounds, "this_seat", lambda: "aether")
    aether = mj._journal_dir()
    assert aria.name == "aria" and aether.name == "aether"
    assert aria != aether and aria.parent == aether.parent
