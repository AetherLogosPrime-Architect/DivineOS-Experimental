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


# Aether's three holes in what a clean run means (2026-10-24), each found by running the functions
# on a sandbox: an empty dream matched an empty source; one source satisfied two destination dreams;
# a source that never reached the destination was never mentioned.


def _audit(tmp_path, dests, srcs):
    (tmp_path / "dest").mkdir()
    (tmp_path / "src").mkdir()
    for name, text in dests.items():
        (tmp_path / "dest" / name).write_text(text, encoding="utf-8")
    for name, text in srcs.items():
        (tmp_path / "src" / name).write_text(text, encoding="utf-8")
    return cds.audit(cds.dest_dreams(tmp_path / "dest"), cds.disk_sources([tmp_path / "src"]))


def test_an_empty_dream_is_reported_even_when_an_empty_source_exists(tmp_path):
    result = _audit(tmp_path, {"001_a.md": "# 001\n"}, {"old.md": "# 01\n"})
    assert [p.name for p in result["empty"]] == ["001_a.md"]
    assert result["matched"] == []


def test_one_source_satisfying_two_dreams_is_reported(tmp_path):
    result = _audit(
        tmp_path,
        {"001_a.md": "# 001\n\nsame\n", "002_b.md": "# 002\n\nsame\n"},
        {"old.md": "# 01\n\nsame\n"},
    )
    assert sorted(p.name for group in result["duplicates"] for p in group) == [
        "001_a.md",
        "002_b.md",
    ]


def test_a_source_dream_that_never_reached_the_destination_is_reported(tmp_path):
    result = _audit(
        tmp_path,
        {"001_a.md": "# 001\n\nkept\n"},
        {"old.md": "# 01\n\nkept\n", "lost.md": "# 02\n\ndropped on the way\n"},
    )
    assert len(result["unreached"]) == 1 and "lost.md" in result["unreached"][0]


def test_a_complete_gather_reports_none_of_the_three(tmp_path):
    result = _audit(
        tmp_path,
        {"001_a.md": "# 001\n\none\n", "002_b.md": "# 002\n\ntwo\n"},
        {"a.md": "# 01\n\none\n", "b.md": "# 02\n\ntwo\n"},
    )
    assert result["empty"] == [] and result["duplicates"] == [] and result["unreached"] == []
    assert len(result["matched"]) == 2 and result["missing"] == []


def test_the_built_in_self_test_passes():
    assert cds.self_test() == 0
