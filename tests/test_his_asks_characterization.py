"""Today's behaviour of his asks' store, pinned before any of it changes.

Feathers: characterize first, so every change in dad_kept_and_known flips one
of these visibly instead of drifting in unnoticed. Each test names the
decision in docs/drafts/dad_kept_and_known_store_threadwalk_2026-09-24.md that
will flip it. When that decision lands, the test is rewritten to the new
behaviour in the same commit, never deleted quietly.
"""

from __future__ import annotations

import pytest

from divineos.core import andrew_request_repeats as rr
from divineos.core import hook_surfaces


@pytest.fixture(autouse=True)
def isolated_store(monkeypatch, tmp_path):
    monkeypatch.setattr(rr, "divineos_home", lambda: tmp_path)


def test_the_store_lives_in_each_seats_own_home(tmp_path):
    """FLIPS IN D2: one shared file at the crossing point, not one per seat."""
    assert rr._db_path() == tmp_path / "andrew_request_repeats.db"


def test_identity_is_my_paraphrase_matched_exactly():
    """FLIPS IN D3: his record's uuid becomes identity; `plain` only a label.

    Today two of his asks are 'the same' only if I worded my summary the same.
    """
    rr.open_request("please build the thing for me", "build the thing he asked for")
    with pytest.raises(rr.RequestRefused):
        rr.open_request("totally different words of his", "Build the thing he asked for ")
    rr.open_request("please build the thing for me", "build that thing he asked for")
    assert len(rr.owed() or []) == 2


def test_a_row_closes_on_any_string_i_type():
    """FLIPS IN D6: closing must quote a filed message of his, exactly."""
    rid = rr.open_request("please build the thing for me", "build the thing he asked for")
    rr.mark_landed(rid, "words he never actually said")
    assert rr.owed() == []


def test_the_owed_list_is_printed_on_every_prompt():
    """FLIPS IN D7: the every-turn surface comes out of the prompt path."""
    with open(hook_surfaces.__file__, encoding="utf-8") as handle:
        source = handle.read()
    assert '("still_owed_to_him", "divineos.core.andrew_request_repeats", "surface"' in source
