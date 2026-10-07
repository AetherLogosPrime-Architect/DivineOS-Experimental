"""One memory, not three; and letters last (docs/drafts/one_memory_not_three_and_letters_last_draft_2026-10-06.md).

Measured 2026-10-06 on 334 results over 30 of Dad's messages, rated by two people:
a letter helped 1 time in 30 for each of us, and the same wording came back under
several labels (a correction, its worklist twin, a knowledge copy), so one text
filled several of the five slots. These pin the two corrections in retrieve_v2,
and the boundaries the walk named: short text is never merged, the collapse runs
before the cut so a freed slot goes to the next-best item, and a set with no
duplicates and no letters comes back unchanged.
"""

from __future__ import annotations

import math
import time

import numpy as np
import pytest

from divineos.core import memory_linkage_retriever_v2 as v2
from divineos.core.memory_linkage_retriever import TOTAL_INJECTION_CAP, _CachedItem

LONG = "root cause: I created the backup branch with plain git branch early in the turn"


def _unit(angle_deg: float) -> np.ndarray:
    a = math.radians(angle_deg)
    return np.array([math.cos(a), math.sin(a)], dtype=float)


def _item(item_id: str, source: str, angle: float, content: str) -> _CachedItem:
    return _CachedItem(
        id=item_id,
        source=source,  # type: ignore[arg-type]
        tier="topic",
        title=f"{source} {item_id}",
        content=content,
        path="",
        filed_at_unix=time.time() - 86400,
        importance_score=0.5,
        embedding=_unit(angle),
    )


@pytest.fixture(autouse=True)
def _query_at_zero_degrees(monkeypatch):
    """The query points at 0 degrees, so an item's angle is its distance from it."""
    v2._reset_v2_state_for_tests()
    monkeypatch.setattr(v2, "_embed_topic", lambda topic: _unit(0))
    yield
    v2._reset_v2_state_for_tests()


def _run(
    cache: dict[str, list[_CachedItem]],
    prompt: str = "a message that is long enough to be searched",
):
    v2._inject_test_cache(cache)
    return v2.retrieve_v2(prompt)


def _fillers(n: int, start: float = 10.0) -> list[_CachedItem]:
    return [
        _item(f"w{i}", "wall", start + 3 * i, f"a distinct standing note number {i}")
        for i in range(n)
    ]


def test_one_wording_filed_three_ways_comes_back_once():
    got = _run(
        {
            "correction": [_item("c1", "correction", 0, LONG)],
            "worklist": [_item("k1", "worklist", 0, LONG)],
            "knowledge": [_item("n1", "knowledge", 0, LONG)],
            "wall": _fillers(5),
        }
    )
    texts = [p.content for p in got]
    assert len(set(texts)) == len(texts), "the same wording came back twice"
    assert sum(t == LONG for t in texts) == 1


def test_the_freed_slot_goes_to_the_next_best_item_not_to_nothing():
    got = _run(
        {
            "correction": [_item("c1", "correction", 0, LONG)],
            "worklist": [_item("k1", "worklist", 0, LONG)],
            "knowledge": [_item("n1", "knowledge", 0, LONG)],
            "wall": _fillers(5),
        }
    )
    assert len(got) == TOTAL_INJECTION_CAP


def test_the_kept_one_says_where_else_it_lives():
    got = _run(
        {
            "correction": [_item("c1", "correction", 0, LONG)],
            "worklist": [_item("k1", "worklist", 0, LONG)],
            "knowledge": [_item("n1", "knowledge", 0, LONG)],
        }
    )
    assert len(got) == 1
    assert "also filed as" in got[0].matched_reason
    assert "worklist" in got[0].matched_reason and "knowledge" in got[0].matched_reason


def test_case_spacing_and_punctuation_do_not_make_a_new_memory():
    got = _run(
        {
            "correction": [_item("c1", "correction", 0, LONG)],
            "knowledge": [
                _item("n1", "knowledge", 0, "  " + LONG.upper().replace(" ", "   ") + "!!")
            ],
        }
    )
    assert len(got) == 1


def test_a_real_wording_change_is_a_different_memory():
    got = _run(
        {
            "correction": [_item("c1", "correction", 0, LONG)],
            "knowledge": [_item("n1", "knowledge", 0, LONG + " and then pushed it three times")],
        }
    )
    assert len(got) == 2


def test_very_short_text_is_never_merged():
    got = _run(
        {
            "correction": [_item("c1", "correction", 0, "ok")],
            "knowledge": [_item("n1", "knowledge", 0, "ok")],
        }
    )
    assert len(got) == 2


def test_a_set_of_one_and_exactly_five_distinct_both_stand():
    assert len(_run({"wall": _fillers(1)})) == 1
    assert len(_run({"wall": _fillers(TOTAL_INJECTION_CAP)})) == TOTAL_INJECTION_CAP


def test_the_best_ranked_copy_is_the_one_kept():
    got = _run(
        {
            "correction": [_item("c1", "correction", 30, LONG)],
            "knowledge": [_item("n1", "knowledge", 0, LONG)],
        }
    )
    assert len(got) == 1
    assert got[0].id == "n1"


def test_a_set_with_no_duplicates_and_no_letters_is_unchanged():
    cache = {"wall": _fillers(TOTAL_INJECTION_CAP)}
    got = _run(cache)
    assert [p.id for p in got] == [f"w{i}" for i in range(TOTAL_INJECTION_CAP)]
    assert all("also filed as" not in p.matched_reason for p in got)


def test_a_letter_is_outranked_by_a_worse_match_of_another_kind():
    letter = _item("l1", "letter", 0, "a letter that matches the message very closely")
    got = _run({"letter": [letter], "wall": _fillers(TOTAL_INJECTION_CAP)})
    assert "l1" not in [p.id for p in got]


def test_a_letter_still_appears_when_nothing_else_passed():
    letter = _item("l1", "letter", 0, "a letter that matches the message very closely")
    got = _run({"letter": [letter]})
    assert [p.id for p in got] == ["l1"]


def test_a_letter_that_repeats_a_correction_collapses_into_the_correction():
    got = _run(
        {
            "correction": [_item("c1", "correction", 20, LONG)],
            "letter": [_item("l1", "letter", 0, LONG)],
        }
    )
    assert len(got) == 1
    assert got[0].source == "correction"
    assert "letter" in got[0].matched_reason


# ------------------------------------------------------------------ asking for a letter
# A flat halving buried a letter he quotes on purpose: measured on 40 real
# letters, asked for by a quoted sentence, 15 came back with no penalty and 1 with
# it. Quoting is the observable act that says he is pointing at that letter, and a
# run of seven words appeared by accident in 0 of 77 of his messages against over
# a million words of letters (six did in 2). Both sides of seven are pinned.

_SEVEN = "the bell has a thirty minute spring and the clock does not"
_LETTER_BODY = f"Aria to Aether. {_SEVEN}. Written on the twentieth of the month."


def _asked_for(prompt: str):
    letter = _item("l1", "letter", 0, _LETTER_BODY)
    return _run({"letter": [letter], "wall": _fillers(TOTAL_INJECTION_CAP)}, prompt)


def test_a_letter_he_quotes_keeps_its_full_rank():
    got = _asked_for("which letter said: " + _SEVEN + "?")
    assert "l1" in [p.id for p in got]


def test_exactly_seven_quoted_words_is_enough():
    seven = " ".join(_SEVEN.split()[:7])
    assert len(seven.split()) == 7
    got = _asked_for("which letter said " + seven + " and then went quiet")
    assert "l1" in [p.id for p in got]


def test_exactly_six_quoted_words_is_not():
    six = " ".join(_SEVEN.split()[:6])
    assert len(six.split()) == 6
    got = _asked_for("which letter said " + six + " and then went quiet")
    assert "l1" not in [p.id for p in got]


def test_a_quote_with_other_capitals_and_punctuation_still_counts():
    got = _asked_for("WHICH LETTER SAID: The Bell has a thirty-minute spring, and the clock!")
    assert "l1" in [p.id for p in got]


def test_a_message_that_quotes_nothing_leaves_the_penalty_on():
    got = _asked_for("a message about a letter but with none of its words")
    assert "l1" not in [p.id for p in got]


def test_an_empty_or_short_message_leaves_the_penalty_on():
    assert "l1" not in [p.id for p in _asked_for("")]
    assert "l1" not in [p.id for p in _asked_for("the bell has")]
