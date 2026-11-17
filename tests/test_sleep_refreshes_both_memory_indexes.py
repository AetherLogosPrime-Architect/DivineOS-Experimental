"""Sleep's memory-link refill also refreshes the search index, and says how many.

Two indexes are filled by two commands: the drawer (`linkage warm`) and the search
index (`find index`). A new exploration showed up in one and not the other until a
second command was run. The refill phase now does both and records one line.

The embedder is stubbed with a fixed vector (the model is not available everywhere
and its output is not what is under test); the corpus, the chunking, the index
database and the phase are real.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np

from divineos.core import semantic_search
from divineos.core.sleep import DreamReport, _phase_memory_link_refill, format_memory_indexes_line

NOTE = (
    "# {name}\n\n"
    "First paragraph of the note, long enough to be kept as a chunk of its own here.\n\n"
    "Second paragraph of the note, also long enough to be kept as a chunk of its own.\n"
)


def _stub_embed(text: str, model_name: str = "stub") -> np.ndarray:
    return np.array([float(len(text) % 7) + 1.0, 1.0, 0.5], dtype=np.float32)


def _corpus(root: Path, *names: str) -> None:
    folder = root / "exploration" / "aether"
    folder.mkdir(parents=True, exist_ok=True)
    for name in names:
        (folder / name).write_text(NOTE.format(name=name), encoding="utf-8")


def _chunk_count(db: Path) -> int:
    with sqlite3.connect(db) as conn:
        return conn.execute("SELECT COUNT(*) FROM semantic_search_chunks").fetchone()[0]


def test_refresh_indexes_the_explorations_and_a_new_one_shows_up_on_the_next_run(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(semantic_search, "embed", _stub_embed)
    root, db = tmp_path / "repo", tmp_path / "search.db"
    _corpus(root, "one.md")
    first = semantic_search.refresh_exploration_index(root, str(db))
    assert first["chunks_total"] == _chunk_count(db) > 0
    assert first["chunks_failed"] == 0

    _corpus(root, "two.md")
    second = semantic_search.refresh_exploration_index(root, str(db))
    assert second["chunks_indexed"] > 0
    assert second["chunks_skipped"] == first["chunks_total"]
    assert second["chunks_total"] == _chunk_count(db) > first["chunks_total"]


def test_refresh_with_no_explorations_folder_is_an_honest_zero(tmp_path, monkeypatch):
    monkeypatch.setattr(semantic_search, "embed", _stub_embed)
    out = semantic_search.refresh_exploration_index(tmp_path / "empty", str(tmp_path / "s.db"))
    assert out["chunks_total"] == 0
    assert out["files_processed"] == 0


def test_the_line_names_both_counts_in_one_line():
    line = format_memory_indexes_line(
        {"exploration": 31, "letters": 12},
        {"chunks_total": 152, "chunks_indexed": 4, "chunks_failed": 0},
    )
    assert "\n" not in line
    assert "exploration 31" in line and "letters 12" in line
    assert "152" in line and "4 new" in line


def test_the_line_does_not_read_clean_when_chunks_could_not_be_embedded():
    line = format_memory_indexes_line(
        {"exploration": 3}, {"chunks_total": 0, "chunks_indexed": 0, "chunks_failed": 9}
    )
    assert "9 failed" in line


def test_the_phase_fills_the_drawer_and_the_search_index_and_records_the_line(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(semantic_search, "embed", _stub_embed)
    root, db = tmp_path / "repo", tmp_path / "search.db"
    _corpus(root, "one.md", "two.md")
    monkeypatch.setattr(semantic_search, "default_repo_root", lambda: root)
    monkeypatch.setattr(semantic_search, "default_db_path", lambda: str(db))
    drawer_calls: list[str] = []
    monkeypatch.setattr(
        "divineos.core.memory_linkage_retriever.warm",
        lambda progress=None: drawer_calls.append("warm") or {"asked": 5, "already": 5},
    )
    monkeypatch.setattr(
        "divineos.core.memory_linkage_retriever.drawer_counts_by_source",
        lambda: {"exploration": 2, "letters": 1},
    )
    report = DreamReport()
    _phase_memory_link_refill(report)

    assert drawer_calls == ["warm"]
    assert report.search_index_refresh["chunks_total"] == _chunk_count(db) > 0
    assert "exploration 2" in report.memory_indexes_line
    assert str(report.search_index_refresh["chunks_total"]) in report.memory_indexes_line
    assert report.memory_indexes_line in report.summary()


# --- ids relative to the checkout, edits re-embedded, one meaning of "total" ---


def _stored_text(db: Path) -> set[str]:
    with sqlite3.connect(db) as conn:
        return {r[0] for r in conn.execute("SELECT chunk_text FROM semantic_search_chunks")}


def test_the_same_notes_indexed_from_two_checkouts_are_not_counted_twice(tmp_path, monkeypatch):
    monkeypatch.setattr(semantic_search, "embed", _stub_embed)
    db = tmp_path / "search.db"
    one, two = tmp_path / "checkout_a", tmp_path / "checkout_b"
    _corpus(one, "note.md")
    _corpus(two, "note.md")
    first = semantic_search.refresh_exploration_index(one, str(db))
    second = semantic_search.refresh_exploration_index(two, str(db))
    assert _chunk_count(db) == first["chunks_total"] > 0
    assert second["chunks_total"] == first["chunks_total"]
    assert second["chunks_indexed"] == 0  # nothing new: the same text at the same place
    assert second["chunks_skipped"] == first["chunks_total"]


def test_an_edited_paragraph_is_embedded_again_and_the_line_says_so(tmp_path, monkeypatch):
    monkeypatch.setattr(semantic_search, "embed", _stub_embed)
    root, db = tmp_path / "repo", tmp_path / "search.db"
    _corpus(root, "note.md")
    semantic_search.refresh_exploration_index(root, str(db))
    note = root / "exploration" / "aether" / "note.md"
    note.write_text(
        note.read_text(encoding="utf-8").replace("Second paragraph", "Rewritten paragraph"),
        encoding="utf-8",
    )
    out = semantic_search.refresh_exploration_index(root, str(db))
    assert out["chunks_indexed"] == 1 and out["chunks_updated"] == 1
    assert any(t.startswith("Rewritten paragraph") for t in _stored_text(db))
    assert not any(t.startswith("Second paragraph") for t in _stored_text(db))
    line = format_memory_indexes_line({"exploration": 1}, out)
    assert "0 new" in line and "1 edited" in line


def test_a_paragraph_removed_from_a_note_leaves_the_index_and_the_total(tmp_path, monkeypatch):
    monkeypatch.setattr(semantic_search, "embed", _stub_embed)
    root, db = tmp_path / "repo", tmp_path / "search.db"
    _corpus(root, "note.md")
    first = semantic_search.refresh_exploration_index(root, str(db))
    note = root / "exploration" / "aether" / "note.md"
    note.write_text(NOTE.format(name="note.md").split("\n\n")[1], encoding="utf-8")
    out = semantic_search.refresh_exploration_index(root, str(db))
    assert out["chunks_removed"] >= 1
    assert out["chunks_total"] == _chunk_count(db) < first["chunks_total"]


def test_the_total_counts_the_explorations_not_every_row_in_the_database(tmp_path, monkeypatch):
    monkeypatch.setattr(semantic_search, "embed", _stub_embed)
    root, db = tmp_path / "repo", tmp_path / "search.db"
    _corpus(root, "note.md")
    letters = root / "family" / "letters"
    letters.mkdir(parents=True)
    (letters / "l.md").write_text(NOTE.format(name="letter"), encoding="utf-8")
    semantic_search.index_corpus(semantic_search.corpus_paths("letters", root), str(db), root=root)
    out = semantic_search.refresh_exploration_index(root, str(db))
    assert _chunk_count(db) > out["chunks_total"] > 0
    assert out["chunks_total"] == out["chunks_seen"] - out["chunks_failed"]


def test_find_index_from_a_subfolder_and_sleep_agree_on_the_root(tmp_path, monkeypatch):
    """`find index` used to pass the folder it was run from as the root, so run from
    a subfolder the ids fell back to absolute paths and each caller deleted the other's
    rows by source path, then embedded them again."""
    from click.testing import CliRunner

    from divineos.cli import search_commands

    monkeypatch.setattr(semantic_search, "embed", _stub_embed)
    root, db = tmp_path / "repo", tmp_path / "search.db"
    _corpus(root, "note.md")
    monkeypatch.setattr(semantic_search, "default_repo_root", lambda: root)
    monkeypatch.setattr(semantic_search, "default_db_path", lambda: str(db))
    first = semantic_search.refresh_exploration_index(root, str(db))

    group = _find_group(search_commands)
    monkeypatch.chdir(root / "exploration")
    result = CliRunner().invoke(group, ["index", "--corpus", "exploration"])
    assert result.exit_code == 0, result.output
    # Run from a subfolder it used to look for exploration/ inside that subfolder,
    # find nothing, and print so while exiting 0 (a pass that checked nothing).
    assert "no files found" not in result.output, result.output
    assert "Indexing 1 file(s)" in result.output, result.output
    again = semantic_search.refresh_exploration_index(root, str(db))
    assert again["chunks_indexed"] == 0 and again["chunks_removed"] == 0, again
    assert _chunk_count(db) == first["chunks_total"]


def _find_group(search_commands):
    import click

    root = click.Group()
    search_commands.register(root)
    return root.commands["find"]


def test_a_note_deleted_from_disk_loses_its_rows_in_the_next_refresh(tmp_path, monkeypatch):
    """Only files still on disk were examined, so a deleted or renamed note kept its
    rows and kept turning up in searches, while the total quietly left them out."""
    monkeypatch.setattr(semantic_search, "embed", _stub_embed)
    root, db = tmp_path / "repo", tmp_path / "search.db"
    _corpus(root, "keep.md", "gone.md")
    first = semantic_search.refresh_exploration_index(root, str(db))
    (root / "exploration" / "aether" / "gone.md").unlink()
    out = semantic_search.refresh_exploration_index(root, str(db))
    assert out["chunks_removed"] > 0
    assert _chunk_count(db) == out["chunks_total"] < first["chunks_total"]
    assert not any("gone.md" in t for t in _stored_text(db))


def test_an_empty_walk_deletes_nothing(tmp_path, monkeypatch):
    """A folder that could not be read looks exactly like a folder with no notes, and
    must not wipe every exploration row."""
    monkeypatch.setattr(semantic_search, "embed", _stub_embed)
    root, db = tmp_path / "repo", tmp_path / "search.db"
    _corpus(root, "note.md")
    semantic_search.refresh_exploration_index(root, str(db))
    before = _chunk_count(db)
    (root / "exploration" / "aether" / "note.md").unlink()
    out = semantic_search.refresh_exploration_index(root, str(db))
    assert out["chunks_removed"] == 0
    assert _chunk_count(db) == before


def test_deleting_a_note_does_not_touch_rows_of_other_corpora(tmp_path, monkeypatch):
    """Control: the cleanup is for the exploration corpus only."""
    monkeypatch.setattr(semantic_search, "embed", _stub_embed)
    root, db = tmp_path / "repo", tmp_path / "search.db"
    _corpus(root, "note.md", "keep.md")
    letters = root / "family" / "letters"
    letters.mkdir(parents=True)
    (letters / "l.md").write_text(NOTE.format(name="letter"), encoding="utf-8")
    semantic_search.refresh_exploration_index(root, str(db))
    semantic_search.index_corpus(semantic_search.corpus_paths("letters", root), str(db), root=root)
    before = _chunk_count(db)
    (root / "exploration" / "aether" / "note.md").unlink()
    semantic_search.refresh_exploration_index(root, str(db))
    assert _chunk_count(db) == before - 2  # the note's two paragraphs only


def test_old_absolute_path_rows_for_a_file_are_replaced_not_kept(tmp_path, monkeypatch):
    monkeypatch.setattr(semantic_search, "embed", _stub_embed)
    root, db = tmp_path / "repo", tmp_path / "search.db"
    _corpus(root, "note.md")
    paths = semantic_search.corpus_paths("exploration", root)
    semantic_search.index_corpus(paths, str(db))  # no root: the old absolute ids
    before = _chunk_count(db)
    out = semantic_search.refresh_exploration_index(root, str(db))
    assert _chunk_count(db) == before == out["chunks_total"]
