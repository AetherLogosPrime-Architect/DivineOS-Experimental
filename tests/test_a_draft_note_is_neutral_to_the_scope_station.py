"""The draft note every change carries is neutral to the scope station.

2026-10-26: Serein's letter plus the draft note the board itself asks for read MIXED, because
docs/drafts/ counted as code. A writing-only change was refused for carrying its own required
note, and I stamped it despite the board. The note belongs to neither side: it must not make a
letter code, and it must not make a code change mixed (every code change has one).
What it must never do is hide code, and it cannot: the code check is on the other files.
"""

from __future__ import annotations

from divineos.core.build_flow import Status, check_scope_station

_NOTE = "docs/drafts/the_change_draft_2026-10-26.md"
_LETTER = "family/letters/serein-to-aether-2026-10-05-x.md"
_CODE = ("src/divineos/core/a.py", "tests/test_a.py")


def test_a_letter_with_its_draft_note_is_writing_only_and_passes() -> None:
    result = check_scope_station((_NOTE, _LETTER), "aether/a-letter")
    assert result.status is Status.SATISFIED
    assert "not mixed" in result.detail


def test_code_with_its_draft_note_still_passes_and_is_not_made_mixed() -> None:
    result = check_scope_station((*_CODE, _NOTE), "fix/a")
    assert result.status is Status.SATISFIED
    assert "no writing" in result.detail


def test_a_draft_note_cannot_hide_code_riding_on_a_letter() -> None:
    result = check_scope_station((_NOTE, _LETTER, *_CODE), "fix/a")
    assert result.status is Status.MISSING
    assert "MIXED" in result.detail


def test_a_draft_note_alone_is_not_mixed() -> None:
    assert check_scope_station((_NOTE,), "aether/a-note").status is Status.SATISFIED
