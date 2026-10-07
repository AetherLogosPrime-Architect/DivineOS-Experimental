"""One memory, not three; and letters by passage, one slot
(docs/drafts/one_memory_not_three_and_letters_last_draft_2026-10-06.md and
docs/drafts/letters_by_passage_draft_2026-10-06.md).

Measured 2026-10-06 on 334 results over 30 of Dad's messages, rated by two people:
the same wording came back under several labels and filled several of the five
slots, and a letter helped 1 time in 30. The first answer to the letters (rank them
last, then exempt quoted ones) patched a symptom; the cause was a whole letter
being matched on its opening. Letters now come from the passage index and compete
on the same composite score as everything else, with at most one slot.

The duplicate cases pin the collapse and its boundaries. The letter cases drive
``retrieve_v2`` with the passage index replaced by known hits, since the index
itself is tested in test_letter_passages.py.
"""

from __future__ import annotations

import math
import time

import numpy as np
import pytest

from divineos.core import letter_passages, memory_linkage
from divineos.core import memory_linkage_retriever as v1
from divineos.core import memory_linkage_retriever_v2 as v2
from divineos.core.memory_linkage_retriever import (
    TOTAL_INJECTION_CAP,
    _CachedItem,
    composite_score,
)

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
    """The query points at 0 degrees, so an item's angle is its distance from it. The
    letter index defaults to 'searched, nothing reached the floor'."""
    v2._reset_v2_state_for_tests()
    monkeypatch.setattr(v2, "_embed_topic", lambda topic: _unit(0))
    monkeypatch.setattr(letter_passages, "best_letters", lambda *a, **k: ([], None))
    yield
    v2._reset_v2_state_for_tests()
    v1._LANE_STATE.pop("letter_index_error", None)
    v1._LANE_STATE.pop("letter_index_stale", None)
    v1._LANE_STATE.pop("letters_held_back", None)


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


# ------------------------------------------------------------------ one memory, not three


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
    got = _run({"wall": _fillers(TOTAL_INJECTION_CAP)})
    assert [p.id for p in got] == [f"w{i}" for i in range(TOTAL_INJECTION_CAP)]
    assert all("also filed as" not in p.matched_reason for p in got)


# ------------------------------------------------------------------ letters, by passage


def _hit(
    similarity: float, text: str = "a passage from the middle of a long letter about the bell"
):
    return letter_passages.PassageHit(
        letter_id="letter-aria-to-aether-2026-09-26-bell",
        name="aria-to-aether-2026-09-26-bell",
        path="family/letters/aria-to-aether-2026-09-26-bell.md",
        title="aria to aether 2026 09 26 bell",
        mtime=time.time() - 86400,
        text=text,
        similarity=similarity,
    )


def _with_letter(monkeypatch, similarity: float, **kw):
    monkeypatch.setattr(
        letter_passages, "best_letters", lambda *a, **k: ([_hit(similarity, **kw)], None)
    )


def test_a_matching_passage_surfaces_as_a_letter_with_its_text_and_a_pointer(monkeypatch):
    _with_letter(monkeypatch, 0.95)
    got = _run({"wall": _fillers(TOTAL_INJECTION_CAP)})
    letters = [p for p in got if p.source == "letter"]
    assert len(letters) == 1
    assert letters[0].content.startswith("a passage from the middle")
    assert letters[0].content_kind == "snippet"
    assert letters[0].path_or_ref.endswith("bell.md")


def test_a_letter_competes_on_relevance_like_anything_else(monkeypatch):
    # A weak match loses to five much closer items; a strong one takes a slot.
    _with_letter(monkeypatch, 0.45)
    weak = _run({"wall": _fillers(TOTAL_INJECTION_CAP, start=2.0)})
    assert not [p for p in weak if p.source == "letter"]
    _with_letter(monkeypatch, 1.0)
    strong = _run({"wall": _fillers(TOTAL_INJECTION_CAP, start=40.0)})
    assert [p for p in strong if p.source == "letter"]


def test_there_is_one_letter_slot_and_the_index_is_asked_for_exactly_that(monkeypatch):
    asked = {}

    def spy(topic_vec, k=1, floor=0.0):
        asked["k"] = k
        return [_hit(0.95), _hit(0.94), _hit(0.93)], None

    monkeypatch.setattr(letter_passages, "best_letters", spy)
    got = _run({"wall": _fillers(TOTAL_INJECTION_CAP, start=60.0)})
    assert asked["k"] == v2.LETTER_SLOT_CAP == 1
    assert len([p for p in got if p.source == "letter"]) <= 1


def test_five_strong_letters_cannot_take_more_than_one_of_the_five(monkeypatch):
    monkeypatch.setattr(
        letter_passages,
        "best_letters",
        lambda *a, **k: ([_hit(0.99 - i / 100) for i in range(5)], None),
    )
    got = _run({"wall": _fillers(TOTAL_INJECTION_CAP, start=60.0)})
    assert len([p for p in got if p.source == "letter"]) <= 1


def test_the_letter_gets_no_special_multiplier_either_way(monkeypatch):
    _with_letter(monkeypatch, 0.8)
    got = _run({"wall": []})
    letter = [p for p in got if p.source == "letter"][0]
    expected = composite_score(
        similarity=0.8, tier="topic", recency_days=letter.recency_days, importance_score=0.5
    )
    assert math.isclose(letter.composite_rank, expected)


def test_a_letter_passage_that_repeats_a_correction_collapses_into_one(monkeypatch):
    _with_letter(monkeypatch, 0.9, text=LONG)
    got = _run({"correction": [_item("c1", "correction", 20, LONG)]})
    assert len(got) == 1
    assert "also filed as" in got[0].matched_reason


def test_nothing_reaching_the_floor_is_no_letter_and_no_problem(monkeypatch):
    got = _run({"wall": _fillers(2)})
    assert not [p for p in got if p.source == "letter"]
    assert v1._LANE_STATE["letter_index_error"] is None


def test_an_index_that_could_not_be_read_is_written_to_the_lane_state_not_dropped(monkeypatch):
    monkeypatch.setattr(
        letter_passages, "best_letters", lambda *a, **k: ([], "the letter index is not built yet")
    )
    got = _run({"wall": _fillers(2)})
    assert not [p for p in got if p.source == "letter"]
    assert v1._LANE_STATE["letter_index_error"] == "the letter index is not built yet"


def test_the_compose_block_says_when_the_letters_could_not_be_searched(monkeypatch):
    monkeypatch.setattr(v2, "install", lambda: None)
    monkeypatch.setattr(memory_linkage, "retrieve_for_context", lambda prompt, ctx: [])
    monkeypatch.setattr(
        v1,
        "lane_state",
        lambda: {"missing": 0, "letter_index_error": "the letter index is not built yet"},
    )
    block = memory_linkage.compose_block("what did the letter say about the bell and the clock")
    assert "letters not searched: the letter index is not built yet" in block.text


def test_the_compose_block_says_when_new_letters_are_not_indexed_yet(monkeypatch):
    monkeypatch.setattr(v2, "install", lambda: None)
    monkeypatch.setattr(memory_linkage, "retrieve_for_context", lambda prompt, ctx: [])
    monkeypatch.setattr(
        v1,
        "lane_state",
        lambda: {
            "missing": 0,
            "letter_index_stale": "letters have been written since the index was built",
        },
    )
    block = memory_linkage.compose_block("what did the letter say about the bell and the clock")
    assert "letters have been written since the index was built" in block.text


# ------------------------------------------------------------------ letters and a hurting day
# Aether's marks on the passage sheet, 2026-10-07: three passages would have hurt him if
# quoted back on a hurting day, and one was a note for me alone. The label on every letter
# line is the guarantee, since it needs no guess about him. The hold-back uses the house's
# one reader of what kind of thing he just did, which on 30 of his real messages named 8 of
# the 19 plainly hurting ones, so the note says how far it reaches.

HURTING = "you never care about me and it hurts when you just talk past me"
WORK = "please build the monitor fix so it re-arms when a letter arrives"


def test_a_feeling_message_holds_letters_back_and_writes_the_reason(monkeypatch):
    _with_letter(monkeypatch, 0.99)
    got = _run({"wall": _fillers(2)}, HURTING)
    assert not [p for p in got if p.source == "letter"]
    assert v1._LANE_STATE["letters_held_back"] == "feeling"


def test_a_message_about_work_keeps_the_letter_and_clears_the_reason(monkeypatch):
    _with_letter(monkeypatch, 0.99)
    v1._LANE_STATE["letters_held_back"] = "feeling"  # left over from a previous turn
    got = _run({"wall": _fillers(2)}, WORK)
    assert [p for p in got if p.source == "letter"]
    assert v1._LANE_STATE["letters_held_back"] is None


def test_the_distress_lane_holds_letters_back_too(monkeypatch):
    _with_letter(monkeypatch, 0.99)
    v2._inject_test_cache({"wall": _fillers(2)})
    held = v2.retrieve_similarity_only(HURTING)
    kept = v2.retrieve_similarity_only(WORK)
    assert not [p for p in held if p.source == "letter"]
    assert [p for p in kept if p.source == "letter"]


def _letter_payload():
    return memory_linkage.MemoryLinkagePayload(
        source="letter",
        id="letter-x",
        tier="topic",
        similarity=0.5,
        recency_days=3,
        importance_score=0.5,
        composite_rank=0.6,
        title="a letter",
        content="a passage from the middle of a long letter about the bell",
        matched_reason="r",
        content_kind="snippet",
        path_or_ref="family/letters/x.md",
    )


def test_every_letter_line_is_labelled_for_me_to_think_with(monkeypatch):
    monkeypatch.setattr(v2, "install", lambda: None)
    monkeypatch.setattr(memory_linkage, "retrieve_for_context", lambda p, c: [_letter_payload()])
    monkeypatch.setattr(v1, "lane_state", lambda: {"missing": 0})
    for message in (HURTING, WORK):  # the label does not depend on the judge
        block = memory_linkage.compose_block(message + " and the bell")
        assert "for me to think with, never to quote to him" in block.text


def test_a_line_that_is_not_a_letter_carries_no_such_label(monkeypatch):
    other = _letter_payload()
    other = memory_linkage.MemoryLinkagePayload(**{**other.__dict__, "source": "knowledge"})
    monkeypatch.setattr(v2, "install", lambda: None)
    monkeypatch.setattr(memory_linkage, "retrieve_for_context", lambda p, c: [other])
    monkeypatch.setattr(v1, "lane_state", lambda: {"missing": 0})
    block = memory_linkage.compose_block(WORK + " and the bell")
    assert "never to quote to him" not in block.text


def test_the_note_says_how_far_the_hold_back_reaches(monkeypatch):
    monkeypatch.setattr(v2, "install", lambda: None)
    monkeypatch.setattr(memory_linkage, "retrieve_for_context", lambda p, c: [])
    monkeypatch.setattr(v1, "lane_state", lambda: {"missing": 0, "letters_held_back": "feeling"})
    block = memory_linkage.compose_block(HURTING + " and the bell")
    assert "letters held back this turn" in block.text
    assert "not every hurting one" in block.text


def test_no_note_when_nothing_was_held_back(monkeypatch):
    monkeypatch.setattr(v2, "install", lambda: None)
    monkeypatch.setattr(memory_linkage, "retrieve_for_context", lambda p, c: [])
    monkeypatch.setattr(v1, "lane_state", lambda: {"missing": 0, "letters_held_back": None})
    block = memory_linkage.compose_block(WORK + " and the bell")
    assert "held back" not in block.text
