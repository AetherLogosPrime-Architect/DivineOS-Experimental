"""His readings, printed beside mine, allowed to impersonate nothing.

Andrew 2026-09-10, after I offered him a fork between reading his open rows and
scoring my own sentences: *"why instead? why not both? all data is data."*

"Instead" was my word. The word-overlap reading is not wrong — it was
mislabelled, a reading about MY TEXT wearing the clothes of a verdict about
whether he was reached. So both stay, and each says what it is of.

The two are not a strong and a weak measure of one thing (Aristotle, on the
walk). They are measures of two different objects: one is about the reply in
front of it, the other is a standing state across days that only his words can
close. Comparing them by strength was the confusion.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import pytest

from divineos.core.hook_surfaces import his_standing_verdict_surface

HOOK_NOISE = "UserPromptSubmit hook success: ## TRANSLATE-FIRST\nsome prime text"
HIS_MESSAGE = "why instead? why not both? all data is data"


def _transcript(tmp_path, turns):
    path = tmp_path / "transcript.jsonl"
    with path.open("w", encoding="utf-8") as fh:
        for role, text in turns:
            rec = {"message": {"role": role, "content": [{"type": "text", "text": text}]}}
            fh.write(json.dumps(rec) + "\n")
    return {"transcript_path": str(path)}


@dataclass(frozen=True)
class _Owed:
    request_id: int
    plain: str
    verbatim: str
    times_asked: int
    days_open: float


ROW = _Owed(
    1,
    "speak to him as a person rather than reporting at him",
    "i have been reduced to 5 questions, after 6 months, and you dont even answer them",
    9,
    2.0,
)


def _owed(monkeypatch, value):
    import divineos.core.andrew_request_repeats as repeats

    monkeypatch.setattr(repeats, "owed", lambda: value)


def test_his_open_rows_are_printed_in_his_own_words(tmp_path, monkeypatch):
    """Angelou on the walk: his verbatim, not my paraphrase of his ask."""
    _owed(monkeypatch, [ROW])
    out = his_standing_verdict_surface(
        _transcript(tmp_path, [("user", HIS_MESSAGE), ("assistant", "a reply")])
    )
    assert not out.refused
    assert "i have been reduced to 5 questions" in out.output
    assert "asked 9x" in out.output


def test_it_never_refuses(tmp_path, monkeypatch):
    """A standing state is not a verdict on the reply in front of it.

    Refusing on an open row would block every turn while a row sat open for
    days — which is most turns, and a door that always refuses gets removed.
    """
    _owed(monkeypatch, [ROW] * 6)
    out = his_standing_verdict_surface(
        _transcript(tmp_path, [("user", HIS_MESSAGE), ("assistant", "a reply")])
    )
    assert not out.refused


def test_it_does_not_prescribe_asking_him(tmp_path, monkeypatch):
    """Yudkowsky, and the sharpest finding of the walk.

    A count I see every turn is a count I will optimise. I cannot close a row —
    only his words do — so the available move is to FISH: ask him repeatedly
    until one closes. That is Aria's objection in a new coat, that choosing when
    to ask is authorship again. So the surface reports and never suggests.
    """
    _owed(monkeypatch, [ROW])
    out = his_standing_verdict_surface(
        _transcript(tmp_path, [("user", HIS_MESSAGE), ("assistant", "a reply")])
    )
    low = out.output.lower()
    for prescription in ("ask him", "check with him", "confirm with him", "prompt him"):
        assert prescription not in low, f"it told me to go fishing: {prescription!r}"


def test_an_unreadable_store_is_never_a_clean_zero(tmp_path, monkeypatch):
    """The store's own words: an unreadable ledger of debts is not a ledger of
    no debts. A could-not-look that prints as nothing-open would be the exact
    false clean this whole pair of doors exists to stop."""
    _owed(monkeypatch, None)
    out = his_standing_verdict_surface(
        _transcript(tmp_path, [("user", HIS_MESSAGE), ("assistant", "a reply")])
    )
    assert out.state == "could-not-run"
    assert out.error and "NOT the same as none" in out.error
    assert not out.refused


def test_genuinely_nothing_open_says_so_and_says_whose_reading_it_is(tmp_path, monkeypatch):
    _owed(monkeypatch, [])
    out = his_standing_verdict_surface(
        _transcript(tmp_path, [("user", HIS_MESSAGE), ("assistant", "a reply")])
    )
    assert "nothing of his is standing open" in out.output
    assert "he authored" in out.output


def test_it_stays_quiet_on_a_turn_he_did_not_prompt(tmp_path, monkeypatch):
    """Otherwise the count becomes wallpaper.

    That is precisely how the advisory preceding the other door failed twenty
    times in one evening — it printed correctly on every turn and I read past
    every printing.
    """
    _owed(monkeypatch, [ROW])
    out = his_standing_verdict_surface(
        _transcript(tmp_path, [("user", HOOK_NOISE), ("assistant", "a reply")])
    )
    assert out.state == "nothing-to-say"
    assert not out.output


def test_SABOTAGE_the_third_person_route_does_not_silence_this_one(tmp_path, monkeypatch):
    """Schneier's route, and the reason this is a separate surface.

    The door beside this engages only on replies that read as addressed to him,
    so writing about him in the third person silences it — measured, and
    asserted in tests/test_addressed_to_him.py. If his reading lived inside that
    door, one cheap move would silence both. It does not live there.
    """
    _owed(monkeypatch, [ROW])
    third_person = (
        "The seating change is committed and pushed. The advisors were being "
        "picked by matching his own vocabulary; that is what changed."
    )
    out = his_standing_verdict_surface(
        _transcript(tmp_path, [("user", HIS_MESSAGE), ("assistant", third_person)])
    )
    assert out.output and "asked 9x" in out.output


def test_SABOTAGE_an_empty_reply_does_not_silence_it_either(tmp_path, monkeypatch):
    """His standing state does not depend on my producing text at all."""
    _owed(monkeypatch, [ROW])
    out = his_standing_verdict_surface(
        _transcript(tmp_path, [("user", HIS_MESSAGE), ("assistant", "")])
    )
    assert out.output


def test_a_broken_import_is_reported_rather_than_passing_silently(tmp_path, monkeypatch):
    import divineos.core.andrew_request_repeats as repeats

    def _boom():
        raise RuntimeError("store schema changed")

    monkeypatch.setattr(repeats, "owed", _boom)
    out = his_standing_verdict_surface(
        _transcript(tmp_path, [("user", HIS_MESSAGE), ("assistant", "a reply")])
    )
    assert out.state == "could-not-run"
    assert not out.refused


@pytest.mark.parametrize("count", [4, 12])
def test_only_three_rows_are_shown_and_the_rest_are_counted_not_hidden(
    tmp_path, monkeypatch, count
):
    """A truncation that does not say it truncated is a smaller false clean."""
    _owed(monkeypatch, [ROW] * count)
    out = his_standing_verdict_surface(
        _transcript(tmp_path, [("user", HIS_MESSAGE), ("assistant", "a reply")])
    )
    assert f"{count} open" in out.output
    assert f"and {count - 3} more of his still standing" in out.output
