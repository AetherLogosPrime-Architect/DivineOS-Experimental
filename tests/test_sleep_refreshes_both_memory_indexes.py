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
