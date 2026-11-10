"""The journal folder is the seat that owns the database, never a guess from the tree's folder name.

2026-10-26: the first real backfill of my thirteen entries wrote them to journal/aether/. The database it
opened was mine (~/.divineos-aria), but `_journal_dir` took the seat from `his_lessons_shelf.seat(root)`,
which reads the NAME of the folder the code runs from; a work copy called "wjournal" is not named aria, so
it answered aether. My earlier seat test passed because it monkeypatched `seat`, proving the path function
and not the seat. The seat now comes from `sibling_audit_rounds.this_seat()`, resolved from the data home
the database itself comes from, and an unknown seat refuses instead of guessing.
"""

import pytest

from divineos.core import memory_journal as mj
from divineos.core import sibling_audit_rounds as sar


@pytest.fixture(autouse=True)
def _no_override(monkeypatch):
    monkeypatch.delenv("DIVINEOS_JOURNAL_DIR", raising=False)


def test_a_work_copy_not_named_aria_still_files_aria_entries_under_aria(monkeypatch):
    monkeypatch.setattr(sar, "this_seat", lambda: "aria")
    assert mj._journal_dir().name == "aria"


def test_the_other_seats_data_home_files_under_aether(monkeypatch):
    monkeypatch.setattr(sar, "this_seat", lambda: "aether")
    assert mj._journal_dir().name == "aether"


def test_the_two_seats_get_sibling_folders_in_the_same_journal_directory(monkeypatch):
    monkeypatch.setattr(sar, "this_seat", lambda: "aria")
    aria = mj._journal_dir()
    monkeypatch.setattr(sar, "this_seat", lambda: "aether")
    aether = mj._journal_dir()
    assert aria != aether and aria.parent == aether.parent and aria.parent.name == "journal"


def test_a_seat_that_cannot_be_told_refuses_instead_of_guessing(monkeypatch):
    monkeypatch.setattr(sar, "this_seat", lambda: None)
    with pytest.raises(RuntimeError, match="seat"):
        mj._journal_dir()


def test_the_name_of_the_tree_no_longer_decides_anything():
    """The old rule, a folder named without 'aria' means aether, must not be what answers."""
    import inspect

    source = inspect.getsource(mj._journal_dir)
    assert "his_lessons_shelf" not in source
