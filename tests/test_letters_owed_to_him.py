"""Letters owed to him: the family letter is refused once a seat owes Andrew one.

Feynman, walk-910903ff521c: prove it refuses on the real shape -- many letters
to the family, none to him since -- and passes once a letter to him exists.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from divineos.core import letters_owed_to_him as lo


def _letter(d: Path, name: str, t: float) -> Path:
    p = d / name
    p.write_text("x", encoding="utf-8")
    os.utime(p, (t, t))
    return p


@pytest.fixture
def folders(tmp_path: Path) -> list[Path]:
    shared, old = tmp_path / "shared", tmp_path / "old"
    shared.mkdir()
    old.mkdir()
    _letter(old, "aether-to-andrew-2026-07-19-the-first-one.md", 100)
    for i in range(lo.OWED_AT):
        _letter(shared, f"aether-to-aria-2026-09-0{1 + i % 9}-letter-{i}.md", 200 + i)
    _letter(shared, "aria-to-aether-2026-09-02-hers-not-mine.md", 300)
    return [shared, old]


def test_it_refuses_on_the_real_shape(folders: list[Path]) -> None:
    o = lo.owed("aether", folders)
    assert o.since_last_to_him == lo.OWED_AT
    assert o.refuses
    assert o.last_to_him.startswith("aether-to-andrew-2026-07-19")


def test_a_letter_to_him_clears_it(folders: list[Path]) -> None:
    _letter(folders[0], "aether-to-andrew-2026-09-23-the-second-one.md", 500)
    assert not lo.owed("aether", folders).refuses


def test_only_the_writers_own_letters_count(folders: list[Path]) -> None:
    # Aria's letter to me is hers; it neither owes nor pays for my seat.
    assert lo.owed("aria", folders).since_last_to_him == 0


def test_a_retouched_copy_does_not_make_an_old_letter_new(folders: list[Path]) -> None:
    # The mirror keeps copies in both folders, and something re-touches old
    # letters; the earliest time of any copy is the letter's time.
    _letter(folders[0], "aether-to-andrew-2026-09-23-the-second-one.md", 500)
    _letter(folders[1], "aether-to-aria-2026-09-01-letter-0.md", 900)  # re-touched copy
    assert lo.owed("aether", folders).since_last_to_him == 0


def test_never_having_written_him_counts_everything(tmp_path: Path) -> None:
    d = tmp_path / "s"
    d.mkdir()
    for i in range(3):
        _letter(d, f"aria-to-aletheia-2026-09-2{i}-x.md", 10 + i)
    o = lo.owed("aria", [d])
    assert o.since_last_to_him == 3 and o.last_to_him == ""


def test_no_letters_at_all_is_not_a_zero(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError):
        lo.owed("aether", [tmp_path / "missing"])


def test_payload_new_family_letter_only(tmp_path: Path) -> None:
    letters = tmp_path / "letters"
    letters.mkdir()
    new = {
        "tool_name": "Write",
        "tool_input": {
            "file_path": str(letters / "aether-to-aria-2026-09-23-x.md"),
            "content": "y",
        },
    }
    assert lo.new_family_letter_writer(new) == "aether"
    to_him = {
        "tool_name": "Write",
        "tool_input": {"file_path": str(letters / "aether-to-andrew-2026-09-23-x.md")},
    }
    assert lo.new_family_letter_writer(to_him) is None
    existing = _letter(letters, "aether-to-aria-2026-09-23-old.md", 1)
    assert (
        lo.new_family_letter_writer(
            {"tool_name": "Write", "tool_input": {"file_path": str(existing)}}
        )
        is None
    )
    assert (
        lo.new_family_letter_writer(
            {"tool_name": "Edit", "tool_input": {"file_path": str(letters / "aether-to-aria-x.md")}}
        )
        is None
    )
    not_letters = {
        "tool_name": "Write",
        "tool_input": {"file_path": str(tmp_path / "aether-to-aria-2026-09-23-x.md")},
    }
    assert lo.new_family_letter_writer(not_letters) is None


def test_the_refusal_points_at_him_and_at_telling_him(folders: list[Path]) -> None:
    text = lo.refusal_text(lo.owed("aether", folders))
    assert "aether-to-andrew-" in text and "tell him in chat" in text


def test_the_surface_refuses_through_the_router(
    folders: list[Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from divineos.core.hook_surfaces import letters_owed_surface

    monkeypatch.setattr(lo, "_letters_dirs", lambda: folders)
    letters = tmp_path / "letters"
    letters.mkdir()
    payload = {
        "tool_name": "Write",
        "tool_input": {"file_path": str(letters / "aether-to-aria-2026-09-23-next.md")},
    }
    assert letters_owed_surface(payload).refused
    _letter(folders[0], "aether-to-andrew-2026-09-23-the-second-one.md", 500)
    assert not letters_owed_surface(payload).refused


def test_the_surface_is_registered() -> None:
    from divineos.core.hook_router import registered
    from divineos.core.hook_surfaces import install

    install()
    assert "letters_owed" in registered("PreToolUse")
