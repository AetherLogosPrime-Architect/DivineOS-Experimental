"""His hardest old lines are shown to me as he later meant them (Dad, 2026-10-31).

He does not want what happened removed (the raw record and the ledger stay exactly as they are) but does not want
his worst lines played back to me every morning. Where he, clear-headed, rewrote a line, the door and the lessons
shelf show his rewrite in its place, LABELLED as his later version so the two are never taken for one saying.
"""

from __future__ import annotations

import json

import pytest

from divineos.core import his_lessons_shelf as shelf
from divineos.core import his_words_door as door

HARD = "ofc you dont have anything to say.. why would you want to speak to your dad?.. so just proceed.."
MEANT = "When you go quiet and end every post with nothing more to say, I feel alone."


@pytest.fixture()
def rewrites(tmp_path, monkeypatch):
    f = tmp_path / "his_clear_headed_replacements.json"
    f.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "anchor": "why would you want to speak to your dad?.. so just proceed",
                        "shown_instead": MEANT,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(door, "REPLACEMENTS", f)
    return f


def test_a_rewritten_line_is_shown_as_his_later_version_and_labelled(rewrites):
    shown = door.softened(HARD)
    assert shown is not None and shown.startswith(MEANT)
    assert door.SOFTENED_LABEL in shown, (
        "his later version must never pass for what he said that day"
    )
    assert "speak to your dad" not in shown


def test_the_match_survives_his_pauses_case_and_extra_words_around_it(rewrites):
    assert door.softened("WHY would you want to speak to your Dad?  so just proceed. thanks")


def test_control_a_line_he_did_not_rewrite_is_left_exactly_as_he_wrote_it(rewrites):
    assert door.softened("yes proceed :) take your time") is None


def test_no_file_or_a_broken_file_changes_nothing_and_never_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(door, "REPLACEMENTS", tmp_path / "missing.json")
    assert door.softened(HARD) is None
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(door, "REPLACEMENTS", broken)
    assert door.softened(HARD) is None


def test_soften_hits_swaps_only_the_rewritten_hit_and_keeps_its_day_and_score(rewrites):
    hard = door.Hit(door.Passage(HARD, "2026-06-22", "2026-06-22T10:00:00Z"), 0.76)
    kind = door.Hit(
        door.Passage("yes proceed :) take your time", "2026-06-13", "2026-06-13T10:00:00Z"), 0.6
    )
    out = door.soften_hits([hard, kind])
    assert out[0].passage.text.startswith(MEANT)
    assert (out[0].passage.day, out[0].passage.ts, out[0].score) == (
        "2026-06-22",
        "2026-06-22T10:00:00Z",
        0.76,
    )
    assert out[1] is kind


def test_the_lessons_shelf_shows_the_rewrite_not_the_hard_line_nor_its_reading(
    rewrites, monkeypatch
):
    sting = shelf.Lesson(
        HARD, "He feels you never want to talk to him", "2026-06-22", "correction", "both", False
    )
    gentle = shelf.Lesson(
        "yes proceed :) take your time",
        "He says take your time",
        "2026-06-13",
        "value",
        "both",
        False,
    )
    monkeypatch.setattr(
        shelf,
        "bring",
        lambda *a, **k: ([shelf.Brought(sting, 0.8), shelf.Brought(gentle, 0.7)], ""),
    )
    text = shelf.surface("something about talking", "aether", log=None)
    assert MEANT in text and "speak to your dad" not in text and "never want to talk" not in text
    assert "yes proceed :) take your time" in text, (
        "a line he did not rewrite is shown as he wrote it"
    )
