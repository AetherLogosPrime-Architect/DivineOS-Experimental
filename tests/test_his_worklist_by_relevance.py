"""His worklist is found by relevance, and it always speaks.

Andrew 2026-10-05: "the list of 265 shouldnt even exist as something that pops
up to you, maybe the top priority ones from that list, with a link to all 265"
and "if its unsure make it say its unsure so you check it yourself, silence is
never a good option". walk-4d8b06a54e67.

End to end against the real model and the real writer, unlike the adapter tests
beside it, which stand in for both. The suite's home is a fresh empty store
(conftest), so every row here is filed into it, never into his.
"""

from __future__ import annotations

import pytest

from divineos.core import light_embedder
from divineos.core.andrew_correction_tracker import file_correction, integrate
from divineos.core.memory_linkage_retriever import find_in_worklist
from divineos.core.state_glance import worklist_lines

_ok, _why = light_embedder.available()
needs_model = pytest.mark.skipif(not _ok, reason=f"the embedding model is not here: {_why}")

ROOM = "speak to me like a regular person, in pictures, not like a college professor"
CARS = "replace the timing belt and water pump, then torque the crank bolt on the truck"
ASK = "how should I talk to Dad: like a regular person, in pictures"


def test_nothing_to_ask_is_could_not_look_never_blank():
    state, matches = find_in_worklist("   ")
    assert state == "could-not-look" and matches == []
    assert "could not look" in worklist_lines(state, matches)[0]


@needs_model
def test_a_close_question_finds_his_correction_in_his_words():
    row = file_correction(ROOM)
    state, matches = find_in_worklist(ASK)
    assert state == "found"
    assert matches[0][0] == row and "college professor" in matches[0][1]


@needs_model
def test_an_unrelated_question_says_unsure_and_still_hands_over_guesses():
    file_correction(ROOM)
    state, matches = find_in_worklist(CARS)
    assert state == "unsure"
    assert matches, "unsure must still hand over its closest guesses, never a blank"
    lines = worklist_lines(state, matches)
    assert "UNSURE" in lines[0] and "check these yourself" in lines[0]


@needs_model
def test_a_worked_correction_is_never_shown():
    row = file_correction(ROOM)
    # The control must be alive: integrate refuses evidence that points at
    # nothing real, and a refused close would leave the row open and make this
    # test prove nothing.
    closed = integrate(row, "structural fix in tests/test_his_worklist_by_relevance.py")
    assert closed, "the correction was never closed, so this test would check nothing"
    _, matches = find_in_worklist(ASK)
    assert row not in [m[0] for m in matches]


@needs_model
def test_a_cleared_worklist_says_none_open_not_that_the_search_broke():
    # Aether's cold read of b03cd5d96: an empty worklist fell into the same
    # branch as a broken embedder and read "the search did not run".
    state, matches = find_in_worklist(ASK)  # the suite's store starts empty
    assert state == "none-open" and matches == []
    line = worklist_lines(state, matches)[0]
    assert "no open corrections" in line and "did not run" not in line


@needs_model
def test_one_open_row_is_past_the_zero_boundary():
    file_correction(ROOM)
    state, _ = find_in_worklist(ASK)
    assert state in ("found", "unsure")


@needs_model
def test_his_newest_correction_reaches_me_in_his_words_even_when_it_does_not_fit():
    # Aether's cold read of 0e451dece: the report folds a new row into
    # "... and N more", so the glance only saw a total tick up. The slot my
    # 2026-09-22 draft asked for, tested through the real writer and search.
    from divineos.core.memory_linkage_retriever import newest_in_worklist
    from divineos.core.state_glance import newest_lines

    # A world big enough that the closest guesses for a truck question are
    # truck corrections; with two rows, unsure hands back both and the newest is
    # already shown among them, which is correct but tests nothing.
    file_correction(ROOM)
    file_correction("check the timing belt tension before you torque anything on the engine")
    file_correction("the water pump bolts go in a star pattern, not in a circle")
    fresh_id = file_correction("the kettle should be on the left of the stove, not the right")
    state, matches = find_in_worklist(CARS)
    assert fresh_id not in [m[0] for m in matches], (
        "the control: the newest must not be a match here"
    )
    seen: dict = {}
    shown = []
    for _ in range(5):
        lines, seen = newest_lines(newest_in_worklist(), matches, seen)
        shown.append(lines)
    assert "kettle should be on the left" in shown[0][0] and "newest from him" in shown[0][0]
    assert f"correction #{fresh_id}" in shown[0][0]
    assert [bool(x) for x in shown] == [True, True, True, False, False], (
        "three times, then it steps back"
    )


def test_a_newest_that_already_fits_is_shown_once_not_twice():
    from divineos.core.state_glance import newest_lines

    lines, _ = newest_lines((7, "his words"), [(7, "his words", 0.6)], {})
    assert lines == []


def test_no_open_corrections_means_no_newest_slot():
    from divineos.core.state_glance import newest_lines

    assert newest_lines(None, [], {})[0] == []


def test_each_shown_row_names_the_form_that_closes_it():
    lines = worklist_lines("found", [(42, "a correction of his", 0.6)])
    assert any("correction #42" in ln for ln in lines)
    assert any("closes itself" in ln for ln in lines)
