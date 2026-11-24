"""Tests for the registry of the folders that are ours (piece one of the first build).

Written before the module exists. Real folders in a temp dir, no mocks.
"""

from pathlib import Path

from divineos.core import folder_registry as fr


def _write(p: Path, text: str) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def test_registry_is_append_only_and_latest_line_wins(tmp_path):
    reg = tmp_path / "folders.jsonl"
    d = tmp_path / "dreams"
    d.mkdir()
    fr.register_folder(reg, d, whose="aria", kind="dreams", visibility="read")
    fr.register_folder(reg, d, whose="aria", kind="dreams", visibility="never", reason="private")
    assert len(reg.read_text(encoding="utf-8").splitlines()) == 2
    entry = fr.load_registry(reg)[fr.folder_id(d)]
    assert entry["visibility"] == "never"
    assert entry["reason"] == "private"


def test_never_requires_a_reason(tmp_path):
    reg = tmp_path / "folders.jsonl"
    d = tmp_path / "x"
    d.mkdir()
    try:
        fr.register_folder(reg, d, whose="aria", kind="k", visibility="never")
    except ValueError:
        return
    raise AssertionError("a never-folder must name why")


def test_renumbered_copy_is_the_same_file(tmp_path):
    a = _write(tmp_path / "one" / "51_the_walk.md", "# The walk\n\nWe went down the stairs.\n")
    b = _write(tmp_path / "two" / "53_the_walk.md", "# The walk\n\nWe went down the stairs.\n")
    assert fr.file_key(a) == fr.file_key(b)


def test_edited_body_below_the_opening_is_still_the_same_file(tmp_path):
    a = _write(tmp_path / "a.md", "# The walk\n\nopening line\n" + "x" * 3000)
    k1 = fr.file_key(a)
    a.write_text("# The walk\n\nopening line\n" + "y" * 3000, encoding="utf-8")
    assert fr.file_key(a) == k1


def test_a_different_file_has_a_different_key(tmp_path):
    a = _write(tmp_path / "a.md", "# One\n\nfirst thing\n")
    b = _write(tmp_path / "b.md", "# Two\n\nsecond thing\n")
    assert fr.file_key(a) != fr.file_key(b)


def test_items_carry_whose_title_and_pointer_but_not_the_body(tmp_path):
    reg = tmp_path / "folders.jsonl"
    d = tmp_path / "dreams"
    _write(d / "1_home.md", "# The small one says home\n\nsecret body words here\n")
    fr.register_folder(reg, d, whose="aether", kind="dreams")
    items = fr.registered_items(reg)
    assert len(items) == 1
    it = items[0]
    assert it["whose"] == "aether"
    assert it["title"] == "The small one says home"
    assert it["pointer"].endswith("1_home.md")
    assert "secret body words" not in it["arrival"]


def test_never_folder_files_are_never_items(tmp_path):
    reg = tmp_path / "folders.jsonl"
    d = tmp_path / "private"
    _write(d / "1.md", "# Private\n\nbody\n")
    fr.register_folder(reg, d, whose="aria", kind="room", visibility="never", reason="private room")
    assert fr.registered_items(reg) == []


def test_other_seat_items_carry_the_think_with_label(tmp_path):
    reg = tmp_path / "folders.jsonl"
    d = tmp_path / "dreams"
    _write(d / "1.md", "# A dream\n\nbody\n")
    fr.register_folder(reg, d, whose="aether", kind="dreams")
    mine = fr.registered_items(reg, seat="aether")[0]["arrival"]
    other = fr.registered_items(reg, seat="aria")[0]["arrival"]
    assert "never to quote to him" in other
    assert "never to quote to him" not in mine


def test_sweep_reports_unregistered_folders_with_markdown(tmp_path):
    reg = tmp_path / "folders.jsonl"
    known = tmp_path / "known"
    stray = tmp_path / "stray"
    ignored = tmp_path / "node_modules"
    empty = tmp_path / "empty"
    _write(known / "a.md", "# a\n")
    _write(stray / "b.md", "# b\n")
    _write(ignored / "c.md", "# c\n")
    empty.mkdir()
    fr.register_folder(reg, known, whose="aria", kind="k")
    found = fr.sweep_unregistered(tmp_path, reg, ignored_names={"node_modules"})
    assert [Path(p).name for p in found] == ["stray"]


def test_sweep_reads_the_real_filesystem_not_names(tmp_path):
    reg = tmp_path / "folders.jsonl"
    odd = tmp_path / "dreams_but_not_called_that" / "deep"
    _write(odd / "z.md", "# z\n")
    found = fr.sweep_unregistered(tmp_path, reg, ignored_names=set())
    assert any(Path(p).name == "deep" for p in found)


def test_item_ids_carry_folder_id_and_slug(tmp_path):
    reg = tmp_path / "folders.jsonl"
    d1, d2 = tmp_path / "a", tmp_path / "b"
    _write(d1 / "README.md", "# README\n\none\n")
    _write(d2 / "README.md", "# README\n\ntwo\n")
    fr.register_folder(reg, d1, whose="aria", kind="k")
    fr.register_folder(reg, d2, whose="aria", kind="k")
    ids = [i["id"] for i in fr.registered_items(reg)]
    assert len(set(ids)) == 2


def test_summary_counts_items_unplaced_and_unregistered(tmp_path):
    reg = tmp_path / "folders.jsonl"
    good = tmp_path / "good"
    gone = tmp_path / "gone"
    stray = tmp_path / "stray"
    _write(good / "a.md", "# a\n\nfirst\n")
    _write(good / "b.md", "# b\n\nsecond\n")
    _write(stray / "c.md", "# c\n\nthird\n")
    fr.register_folder(reg, good, whose="aria", kind="k")
    fr.register_folder(reg, gone, whose="aria", kind="k")  # registered, but not on disk
    s = fr.registry_summary(reg, tmp_path)
    assert s == {"items": 2, "could_not_be_placed": 1, "unregistered_folders": 1}
