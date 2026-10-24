"""A walk finding is refused unless the lens was delivered to me first, and the refusal delivers it.

Dad, 2026-10-24: "the next time either of you game a council walk? i will remove it entirely". Measured the same day on
the twelve newest walks: 41 of 96 applied findings had no load receipt for their lens. The receipt existed since August
(`mansion council --show` logs COUNCIL_LENS_LOADED) and the walk never read it. Design: docs/drafts/
a_walk_finding_needs_the_lens_loaded_first_draft_2026-10-24.md, walk-63f29104e6e3.
"""

from __future__ import annotations

import time

import pytest

from divineos.core import council_walk as cw
from divineos.core.council.engine import get_council_engine
from divineos.core.council.lens_text import lens_plain, lens_questions
from divineos.core.ledger import get_events

PROBLEM = "Whether a walk finding can be written from memory when the lens was never opened"
FINDING = "a real finding of sufficient length to be stored against this lens"


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(cw, "divineos_home", lambda: tmp_path)
    yield


def _receipts(lens):
    return [
        e
        for e in get_events(limit=500, order="desc", event_type="COUNCIL_LENS_LOADED")
        if str((e.get("payload") or {}).get("expert_name", "")).lower() == lens.lower()
    ]


def test_a_finding_with_no_delivery_is_refused_and_the_refusal_delivers_the_lens():
    w = cw.open_walk(PROBLEM)
    lens = w["lenses"][0]
    assert _receipts(lens) == []
    with pytest.raises(cw.WalkRefused) as refused:
        cw.apply_lens(w["walk_id"], lens, FINDING, question=1)
    text = str(refused.value)
    wisdom = get_council_engine().get_expert(lens)
    assert lens_questions(wisdom)[0] in text, "the refusal must carry the lens's own questions"
    assert lens_plain(wisdom) in text, "the delivered text must be the same text --show prints"
    assert _receipts(lens) != [], "the delivery is the receipt"


def test_the_retry_after_the_delivery_is_accepted_and_names_its_question():
    w = cw.open_walk(PROBLEM)
    lens = w["lenses"][0]
    with pytest.raises(cw.WalkRefused):
        cw.apply_lens(w["walk_id"], lens, FINDING, question=1)
    cw.apply_lens(w["walk_id"], lens, FINDING, question=2)
    row = next(r for r in cw.status(w["walk_id"])["lenses"] if r["lens"] == lens)
    assert row["state"] == "APPLIED"
    question_text = lens_questions(get_council_engine().get_expert(lens))[1]
    assert f"[answers Q2: {question_text}]" in row["content"]
    assert "[lens delivered" in row["content"] and "before this finding]" in row["content"]
    assert FINDING in row["content"]


def test_a_receipt_from_before_the_walk_opened_does_not_count():
    """The one-line loop at the top of a session must not cover a walk opened later."""
    probe = cw.open_walk(PROBLEM)
    lens = probe["lenses"][0]
    cw.deliver_lens(lens)  # loaded now, in the past of the walk opened next
    time.sleep(0.02)
    w = cw.open_walk(PROBLEM)
    if lens not in w["lenses"]:
        pytest.skip("the draw did not seat the same lens on the second walk")
    with pytest.raises(cw.WalkRefused):
        cw.apply_lens(w["walk_id"], lens, FINDING, question=1)


def test_a_receipt_for_one_lens_does_not_cover_another():
    w = cw.open_walk(PROBLEM)
    first, second = w["lenses"][0], w["lenses"][1]
    cw.deliver_lens(first)
    cw.apply_lens(w["walk_id"], first, FINDING, question=1)
    with pytest.raises(cw.WalkRefused):
        cw.apply_lens(w["walk_id"], second, FINDING, question=1)


def test_a_question_number_is_required_and_must_exist():
    w = cw.open_walk(PROBLEM)
    lens = w["lenses"][0]
    cw.deliver_lens(lens)
    with pytest.raises(cw.WalkRefused, match="question"):
        cw.apply_lens(w["walk_id"], lens, FINDING)
    count = len(lens_questions(get_council_engine().get_expert(lens)))
    with pytest.raises(cw.WalkRefused, match="question"):
        cw.apply_lens(w["walk_id"], lens, FINDING, question=count + 1)
    with pytest.raises(cw.WalkRefused, match="question"):
        cw.apply_lens(w["walk_id"], lens, FINDING, question=0)


def test_a_lens_not_on_the_walk_keeps_its_old_refusal_and_delivers_nothing():
    w = cw.open_walk(PROBLEM)
    with pytest.raises(cw.WalkRefused, match="not on this walk"):
        cw.apply_lens(w["walk_id"], "Gandalf", "x" * 60, question=1)
    assert _receipts("Gandalf") == []


def test_the_finding_itself_still_needs_substance():
    w = cw.open_walk(PROBLEM)
    lens = w["lenses"][0]
    cw.deliver_lens(lens)
    with pytest.raises(cw.WalkRefused, match="substance"):
        cw.apply_lens(w["walk_id"], lens, "too short", question=1)


def test_exclusion_is_still_possible_and_is_counted_in_the_status_summary():
    w = cw.open_walk(PROBLEM)
    lens = w["lenses"][0]
    cw.exclude_lens(
        w["walk_id"], lens, "this lens has nothing to say about a receipt lookup, and here is why"
    )
    summary = cw.status(w["walk_id"])
    assert any(r["lens"] == lens and r["state"] == "EXCLUDED" for r in summary["lenses"])


def test_every_lens_on_the_roster_is_found_by_the_receipt_it_was_just_delivered_under():
    """Popper's severest case: a lens whose delivered name differs from the name a walk seats it under
    would refuse forever. Delivery writes the engine's name; the walk looks it up by the seated name."""
    engine = get_council_engine()
    before = time.time() - 1
    unmatched = []
    for name in engine.list_experts():
        cw.deliver_lens(name)
        if cw._delivery_time(name, before) is None:
            unmatched.append(name)
    assert unmatched == []
