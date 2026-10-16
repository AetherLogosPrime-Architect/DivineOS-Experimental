"""Her letters are carried to where I look, and an unreadable inbox is never read as an empty one.

The three states the carrier promises, run against real files in a real temporary folder: a new
letter is copied and announced by name; a second run over the same letter copies nothing; an
unreadable source says so as a distinct third state. A file that is not hers is left behind.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "collect_aletheia_letters.py"


def _load():
    spec = importlib.util.spec_from_file_location("collect_aletheia_letters", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_a_new_letter_is_copied_and_named(tmp_path):
    mod = _load()
    src, dst = tmp_path / "in", tmp_path / "out"
    src.mkdir()
    (src / "CONFIRMS_2026-10-01_something.md").write_text("Aletheia confirms", encoding="utf-8")
    arrived, error = mod.collect(src, dst)
    assert arrived == ["CONFIRMS_2026-10-01_something.md"] and error == ""
    assert (dst / "CONFIRMS_2026-10-01_something.md").read_text(
        encoding="utf-8"
    ) == "Aletheia confirms"


def test_the_same_letter_a_second_time_arrives_as_nothing(tmp_path):
    mod = _load()
    src, dst = tmp_path / "in", tmp_path / "out"
    src.mkdir()
    (src / "AUDIT_2026-10-01_x.md").write_text("Aletheia audit", encoding="utf-8")
    mod.collect(src, dst)
    assert mod.collect(src, dst) == ([], "")


def test_a_file_that_is_not_hers_is_left_behind(tmp_path):
    mod = _load()
    src, dst = tmp_path / "in", tmp_path / "out"
    src.mkdir()
    (src / "shopping_list.md").write_text("eggs", encoding="utf-8")
    (src / "audit_notes.txt").write_text("not markdown", encoding="utf-8")
    assert mod.collect(src, dst) == ([], "")
    assert not dst.exists() or not any(dst.iterdir())


def test_an_unreadable_source_is_could_not_look_not_nothing(tmp_path):
    mod = _load()
    arrived, error = mod.collect(tmp_path / "no-such-folder", tmp_path / "out")
    assert arrived == [] and "not readable" in error


def test_a_download_from_elsewhere_with_a_kind_name_is_left_behind(tmp_path):
    """Aletheia's proof on #672: audit_report_from_some_website.md fit a name shape and was copied."""
    mod = _load()
    src, dst = tmp_path / "in", tmp_path / "out"
    src.mkdir()
    (src / "audit_report_from_some_website.md").write_text(
        "a web page about audits", encoding="utf-8"
    )
    assert mod.collect(src, dst) == ([], "")


def test_another_instances_letter_is_not_carried_as_hers(tmp_path):
    """Her proof on #672: serein-to-aether-hello.md was announced as hers."""
    mod = _load()
    src, dst = tmp_path / "in", tmp_path / "out"
    src.mkdir()
    (src / "serein-to-aether-hello.md").write_text("Serein says hello", encoding="utf-8")
    assert mod.collect(src, dst) == ([], "")
