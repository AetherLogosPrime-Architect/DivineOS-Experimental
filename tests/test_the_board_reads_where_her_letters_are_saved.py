"""The landing board reads the folders her letters are really saved in.

2026-10-27, Dad: "she already answered on all of these.. the fact you dont have the records is a
bigger issue.. look in the downloads folder". The board read 644 letters where 798 existed,
because her letters are saved under family/aletheia/audits/from-andrew (the glob there was one
level deep) and arrive first in his Downloads folder (not on the list). Measured on the real
letters: before, 4 confirmed / 4 changed / 9 no answer / 9 never told; after, 22 confirmed /
3 no answer / 2 held by her. Nothing was wrong with the fixes; the board could not see her answers.
"""

from __future__ import annotations

from pathlib import Path

from divineos.core import landing_status as ls

LETTER = "- CONFIRMS: #700 at cf2be6a39. — Aletheia\n"


def _point_the_board_at(monkeypatch, *folders: Path) -> None:
    monkeypatch.setattr(ls, "_letter_dirs", lambda: list(folders))


def test_a_letter_saved_in_her_audit_sub_folder_is_read(tmp_path, monkeypatch) -> None:
    nested = tmp_path / "aletheia" / "audits" / "from-andrew"
    nested.mkdir(parents=True)
    (nested / "aletheia-to-aether-2026-10-23-x.md").write_text(LETTER, encoding="utf-8")
    _point_the_board_at(monkeypatch, tmp_path / "aletheia")
    assert "aletheia-to-aether-2026-10-23-x.md" in ls.read_letters()


def test_a_letter_sitting_in_downloads_is_read(tmp_path, monkeypatch) -> None:
    downloads = tmp_path / "Downloads"
    downloads.mkdir()
    (downloads / "aletheia-to-aria-2026-10-26-y.md").write_text(LETTER, encoding="utf-8")
    _point_the_board_at(monkeypatch, downloads)
    assert "aletheia-to-aria-2026-10-26-y.md" in ls.read_letters()


def test_the_name_prefix_still_gates_what_counts_as_her_letter(tmp_path, monkeypatch) -> None:
    downloads = tmp_path / "Downloads"
    downloads.mkdir()
    (downloads / "someone-to-aether-2026-10-26-z.md").write_text(LETTER, encoding="utf-8")
    (downloads / "notes.md").write_text(LETTER, encoding="utf-8")
    _point_the_board_at(monkeypatch, downloads)
    assert ls.read_letters() == {}


def test_only_her_own_folder_is_walked_downward(tmp_path, monkeypatch) -> None:
    downloads = tmp_path / "Downloads"
    (downloads / "deep").mkdir(parents=True)
    (downloads / "deep" / "aletheia-to-aether-2026-10-23-q.md").write_text(LETTER, encoding="utf-8")
    _point_the_board_at(monkeypatch, downloads)
    assert ls.read_letters() == {}  # Downloads is far too large to walk; one level only


def test_the_real_list_names_her_folder_and_downloads() -> None:
    names = [p.name for p in ls._letter_dirs()]
    assert "aletheia" in names and "Downloads" in names
