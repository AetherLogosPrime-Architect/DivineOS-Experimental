"""A missing file and a corrupt file were sharing one silent exit.

Aria caught this on the merge and left the decision to me rather than
redesigning my module around her guard. Her reading: the two returns agree
for the only caller — the built-ins are the floor, so the pool is never empty
either way — but they are not the same EVENT. A missing extras file is the
ordinary state on a fresh checkout. A corrupt one is a defect, and the handler
lost it without a sound.

The third case is the one neither of us saw until the code was open: the try
wrapped the WHOLE loop, so a single malformed row discarded every question
already parsed above it. A file that grew one bad line quietly lost all the
good ones with it, and the symptom — a slightly shorter pool — is invisible
from outside.

So the tests are about which of the three states the function can tell apart,
not about the return value, because the return value was ALREADY correct in
every case. That is exactly why it could sit there: right answer, wrong
reason, no way to notice.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from divineos.core import circle_questions as cq


@pytest.fixture()
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "earned.jsonl"
    monkeypatch.setattr(cq, "EXTRA_STORE", path)
    return path


def _row(text: str) -> str:
    return json.dumps({"text": text, "kind": "added", "weight": 1.0})


def test_a_missing_store_is_the_ordinary_state_and_says_nothing(
    store: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert cq._added() == []
    assert capsys.readouterr().err == "", "a fresh checkout must not look like a fault"


def test_a_bad_row_costs_its_own_row_and_no_others(
    store: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """THE REGRESSION. The old code returned [] here and lost both good rows."""
    store.write_text(
        _row("the good one before") + "\n" + "{not json at all" + "\n" + _row("the good one after"),
        encoding="utf-8",
    )
    got = [q.text for q in cq._added()]
    assert got == ["the good one before", "the good one after"]


def test_the_corrupt_row_speaks_where_the_missing_file_stays_quiet(
    store: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The whole distinction: silence is right for normal, wrong for broken."""
    store.write_text("{not json at all\n", encoding="utf-8")
    cq._added()
    err = capsys.readouterr().err
    assert err, "a defect that returns a plausible value must not do it silently"
    assert "line 1" in err, "and it must say WHICH row, or the report is unusable"


def test_blank_lines_are_not_defects(store: Path, capsys: pytest.CaptureFixture[str]) -> None:
    store.write_text("\n\n" + _row("kept") + "\n\n", encoding="utf-8")
    assert [q.text for q in cq._added()] == ["kept"]
    assert capsys.readouterr().err == "", "whitespace is not corruption"


def test_it_never_raises_into_the_turn_it_decorates(
    store: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A prime that can take down the turn is worse than one losing a question."""
    store.write_text(
        json.dumps({"kind": "added"})
        + "\n"  # no text key
        + json.dumps({"text": "t", "weight": "not-a-float"})
        + "\n"
        + json.dumps(["not", "an", "object"])
        + "\n"
        + _row("survivor"),
        encoding="utf-8",
    )
    assert [q.text for q in cq._added()] == ["survivor"]
    assert capsys.readouterr().err.count("BAD ROW") == 3
