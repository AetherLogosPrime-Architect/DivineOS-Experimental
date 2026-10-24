"""The dream source check must report a changed or missing source, or a clean run means nothing.

2026-10-24, Aether: when you build it, plant a source and a destination that differ and show the
script reports it. Also pinned: the first heading line is not part of the body (the gather
renumbered it, Dad allows it), and Windows line endings are not an edit.
"""

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_dream_sources.py"
spec = importlib.util.spec_from_file_location("check_dream_sources", SCRIPT)
cds = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cds)


def _pair(tmp_path, dest_text, src_text):
    (tmp_path / "dest").mkdir()
    (tmp_path / "src").mkdir()
    (tmp_path / "dest" / "001_a.md").write_text(dest_text, encoding="utf-8")
    (tmp_path / "src" / "old.md").write_text(src_text, encoding="utf-8")
    return cds.compare(cds.dest_dreams(tmp_path / "dest"), cds.disk_sources([tmp_path / "src"]))


def test_a_renumbered_heading_and_crlf_are_not_an_edit(tmp_path):
    matched, missing = _pair(tmp_path, "# 001 — a\n\nsame body\n", "# 01 — a\r\n\r\nsame body\r\n")
    assert len(matched) == 1 and missing == []


def test_a_changed_body_is_reported_missing(tmp_path):
    matched, missing = _pair(tmp_path, "# 001 — a\n\nCHANGED\n", "# 01 — a\n\noriginal\n")
    assert matched == [] and len(missing) == 1


def test_a_dream_with_no_source_at_all_is_reported_missing(tmp_path):
    (tmp_path / "dest").mkdir()
    (tmp_path / "dest" / "001_a.md").write_text("# 1\n\nalone\n", encoding="utf-8")
    matched, missing = cds.compare(cds.dest_dreams(tmp_path / "dest"), {})
    assert matched == [] and len(missing) == 1


def test_the_built_in_self_test_passes():
    assert cds.self_test() == 0
