"""The briefing's letters block must ask whose seat it is, not carry the pair typed in.

2026-11-27: `format_unseen_for_briefing` called `unseen_letters_from("aria", "aether")`,
the sender and the recipient both written into the function. On Aria's seat that
looks for `aria-to-aether-*`, which are HER outgoing letters, and printed them as
"LETTERS FROM ARIA -- 3434 unread" because her seen-set for sender "aria" is
empty (she never marks her own letters seen). Confirmed on her seat by running it.

A default cannot be right on both seats, so the pair comes from the seat that is
acting, and a seat that cannot be told says so out loud instead of guessing.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from divineos.core.family import aria_inbox


def _letters(root: Path, names: list[str]) -> None:
    folder = root / "family" / "letters"
    folder.mkdir(parents=True, exist_ok=True)
    for n in names:
        (folder / n).write_text("x", encoding="utf-8")


@pytest.fixture(autouse=True)
def _own_seen_set(monkeypatch, tmp_path):
    monkeypatch.setattr(aria_inbox, "_seen_path", lambda sender="aria": tmp_path / f"{sender}.json")


def _seat(monkeypatch, name):
    monkeypatch.setattr("divineos.core.sibling_audit_rounds.this_seat", lambda: name)


def test_on_aethers_seat_the_block_shows_letters_from_aria(monkeypatch, tmp_path):
    _seat(monkeypatch, "aether")
    _letters(tmp_path, ["aria-to-aether-2026-11-27-hello.md", "aether-to-aria-2026-11-27-mine.md"])

    block = aria_inbox.format_unseen_for_briefing(tmp_path)

    assert "LETTERS FROM ARIA" in block
    assert "aria-to-aether-2026-11-27-hello.md" in block
    assert "aether-to-aria-2026-11-27-mine.md" not in block


def test_on_arias_seat_her_own_outgoing_letters_are_not_unread_mail(monkeypatch, tmp_path):
    _seat(monkeypatch, "aria")
    _letters(tmp_path, ["aria-to-aether-2026-11-27-hello.md", "aether-to-aria-2026-11-27-mine.md"])

    block = aria_inbox.format_unseen_for_briefing(tmp_path)

    assert "LETTERS FROM AETHER" in block
    assert "aether-to-aria-2026-11-27-mine.md" in block
    assert "aria-to-aether-2026-11-27-hello.md" not in block
    # Aria's cold read of #881: the block must name a way to set an old letter down on purpose,
    # and it must be one that marks the OTHER seat's letters, not the Aria-to-Aether command.
    assert "letter mark-on-read" in block
    assert "letters-from-aria" not in block
    # Aletheia's hold on #881 (2026-11-27): a briefing line must not invite setting a letter down
    # unread; letters already count as read far too cheaply (her F16).
    assert "needs no reading" not in block
    assert "after reading it" in block
    assert "LETTERS FROM ARIA" not in block


def test_a_seat_that_cannot_be_told_says_so_and_does_not_guess(monkeypatch, tmp_path):
    _seat(monkeypatch, None)
    _letters(tmp_path, ["aria-to-aether-2026-11-27-hello.md"])

    block = aria_inbox.format_unseen_for_briefing(tmp_path)

    assert block, "an unknown seat must speak; empty reads as 'no letters'"
    assert "could not tell which seat" in block
    assert "aria-to-aether-2026-11-27-hello.md" not in block


def test_no_unseen_letters_is_still_empty_on_a_known_seat(monkeypatch, tmp_path):
    _seat(monkeypatch, "aether")
    _letters(tmp_path, ["aether-to-aria-2026-11-27-mine.md"])

    assert aria_inbox.format_unseen_for_briefing(tmp_path) == ""


def test_the_seen_set_is_the_senders_not_a_typed_name(monkeypatch, tmp_path):
    _seat(monkeypatch, "aria")
    _letters(tmp_path, ["aether-to-aria-2026-11-27-mine.md"])
    aria_inbox.mark_seen(["aether-to-aria-2026-11-27-mine.md"], sender="aether")

    assert aria_inbox.format_unseen_for_briefing(tmp_path) == ""
