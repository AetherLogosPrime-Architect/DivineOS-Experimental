"""What Dad cannot open is said at the start of a session, split by WHY (council walk on #727, 2026-10-29).

`rows_without_a_page` was a number nobody asked for. It is now split three ways, because the three call for
three different things: a private room (leave it), an unreadable marker (a person should look), and a row
with no tag and no page (old entries awaiting the one-time pass).
"""

import pytest

from divineos.core import memory_journal as mj


@pytest.fixture
def pages(tmp_path, monkeypatch):
    monkeypatch.setattr(mj, "_journal_dir", lambda: tmp_path / "journal" / "aria")
    return tmp_path / "journal" / "aria"


def test_each_kind_is_counted_on_its_own(pages, monkeypatch):
    before = mj.rows_without_a_page_by_kind()
    monkeypatch.setattr(mj, "_private_room_open", lambda: True)
    mj.journal_save("Kept in a private room.")
    monkeypatch.setattr(mj, "_private_room_open", lambda: None)
    mj.journal_save("Written while the marker could not be read.")
    mj._insert_row(
        "aaaaaaaa-0000-0000-0000-000000000001", "An old one, no tag.", 1_780_000_000.0, "", "", None
    )
    after = mj.rows_without_a_page_by_kind()
    assert after["room"] == before["room"] + 1
    assert after["unverified"] == before["unverified"] + 1
    assert after["untagged"] == before["untagged"] + 1


def test_a_home_with_no_known_seat_gets_a_line_saying_so_not_a_dead_briefing(monkeypatch):
    """Aether's cold read: _journal_dir raises RuntimeError in a home the seat table does not know, and the
    briefing's guard does not catch that, so the first command of every session would die."""

    def no_seat():
        raise RuntimeError("cannot tell which seat's journal this is")

    monkeypatch.setattr(mj, "_journal_dir", no_seat)
    line = mj.format_for_briefing()
    assert "could not tell which seat" in line


def test_the_briefing_line_names_the_kinds_and_is_empty_when_nothing_is_missing(monkeypatch):
    monkeypatch.setattr(
        mj, "rows_without_a_page_by_kind", lambda: {"room": 0, "unverified": 0, "untagged": 0}
    )
    assert mj.format_for_briefing() == ""
    monkeypatch.setattr(
        mj, "rows_without_a_page_by_kind", lambda: {"room": 2, "unverified": 1, "untagged": 13}
    )
    line = mj.format_for_briefing()
    assert "13" in line and "2" in line and "1" in line
    assert "could not tell" in line
    assert "journal export" in line  # says how to write the pages that can be written
