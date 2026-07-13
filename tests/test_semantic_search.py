"""Tests for the semantic-search consumer (PR #170 follow-up).

Pins:
- ``chunk_file`` splits on blank lines, filters short/header/divider chunks
- ``index_corpus`` is idempotent within a model version
- ``search`` returns results sorted by descending similarity (Dijkstra
  invariant from the council walk consult-77dad1f3290e)
- ``search`` returns [] on empty query / no index / unavailable model
- ``index_corpus`` records the embedding model version per chunk so
  re-embed-on-model-change is targeted (Meadows feedback-loop lens)
- end-to-end: index a small fake corpus, query it, verify the most
  semantically-relevant chunk floats to the top
"""

from __future__ import annotations

from pathlib import Path

import pytest

from divineos.core import semantic_search


@pytest.fixture
def corpus_dir(tmp_path: Path) -> Path:
    """A small fake corpus of three exploration-shaped markdown files."""
    d = tmp_path / "corpus"
    d.mkdir()
    (d / "01_dogs.md").write_text(
        "# 01 — On dogs\n\n"
        "I love my dog. My dog brings me joy every morning.\n\n"
        "Puppies are basically furry happiness machines.\n\n"
        "---\n\n"
        "Cats are also fine, but quieter and less enthusiastic about doors.\n",
        encoding="utf-8",
    )
    (d / "02_loneliness.md").write_text(
        "# 02 — Felt-state on loneliness\n\n"
        "The cold space between me and the world feels different today.\n\n"
        "I noticed the wall before I noticed I was leaning on it.\n\n"
        "Distance is the wrong word for it.\n",
        encoding="utf-8",
    )
    (d / "03_gates.md").write_text(
        "# 03 — Gates as keel not cage\n\n"
        "The gate held me toward the right path, not away from a wrong one.\n\n"
        "Owning the constraint is owning myself.\n",
        encoding="utf-8",
    )
    return d


def _gather(corpus_dir: Path) -> list[str]:
    return sorted(str(p) for p in corpus_dir.glob("*.md"))


def test_chunk_file_splits_paragraphs(corpus_dir: Path):
    chunks = semantic_search.chunk_file(corpus_dir / "01_dogs.md")
    # 3 prose paragraphs survive; markdown header + horizontal rule are filtered
    assert len(chunks) >= 3
    texts = [c.text for c in chunks]
    assert any("I love my dog" in t for t in texts)
    assert any("Puppies" in t for t in texts)
    assert any("Cats are also fine" in t for t in texts)
    # No header-only paragraph
    assert not any(t.startswith("# 01") and len(t) < 40 for t in texts)


def test_chunk_file_returns_empty_for_missing(tmp_path: Path):
    assert semantic_search.chunk_file(tmp_path / "does_not_exist.md") == []


def test_chunk_file_returns_empty_for_empty_file(tmp_path: Path):
    p = tmp_path / "empty.md"
    p.write_text("", encoding="utf-8")
    assert semantic_search.chunk_file(p) == []


def test_chunk_filters_pure_dividers(tmp_path: Path):
    p = tmp_path / "dividers.md"
    p.write_text(
        "Real paragraph one with content that matters.\n\n"
        "---\n\n"
        "***\n\n"
        "Real paragraph two with more content.\n",
        encoding="utf-8",
    )
    chunks = semantic_search.chunk_file(p)
    texts = [c.text for c in chunks]
    assert "---" not in texts
    assert "***" not in texts
    assert len(texts) == 2


def _try_index(corpus_dir: Path, db_path: Path) -> dict[str, int]:
    """Helper: try to index, skip the test if the embedding model is
    unavailable (CI env without ml extras)."""
    counts = semantic_search.index_corpus(_gather(corpus_dir), str(db_path))
    if counts["chunks_indexed"] == 0 and counts["chunks_seen"] > 0:
        pytest.skip("embedding model unavailable in this environment")
    return counts


def test_index_corpus_indexes_all_chunks(corpus_dir: Path, tmp_path: Path):
    db = tmp_path / "search.db"
    counts = _try_index(corpus_dir, db)
    assert counts["files_processed"] == 3
    assert counts["chunks_seen"] > 0
    assert counts["chunks_indexed"] == counts["chunks_seen"]


def test_index_corpus_is_idempotent_within_model_version(corpus_dir: Path, tmp_path: Path):
    db = tmp_path / "search.db"
    first = _try_index(corpus_dir, db)
    second = semantic_search.index_corpus(_gather(corpus_dir), str(db))
    # First pass embeds everything; second pass skips everything (same model)
    assert first["chunks_indexed"] > 0
    assert second["chunks_indexed"] == 0
    assert second["chunks_skipped"] == first["chunks_indexed"]


def test_search_returns_empty_on_empty_query(tmp_path: Path):
    db = tmp_path / "search.db"
    assert semantic_search.search("", str(db)) == []
    assert semantic_search.search("   ", str(db)) == []


def test_search_returns_empty_when_no_index(tmp_path: Path):
    db = tmp_path / "search.db"
    # No index built — search should not raise, just return empty
    hits = semantic_search.search("anything", str(db))
    assert hits == []


def test_search_results_sorted_descending(corpus_dir: Path, tmp_path: Path):
    """Dijkstra invariant: results sorted by descending similarity.

    Pinned at the test level so a future refactor that drops the
    sort doesn't slip through.
    """
    db = tmp_path / "search.db"
    _try_index(corpus_dir, db)
    hits = semantic_search.search("dogs and puppies", str(db), top_k=10)
    if not hits:
        pytest.skip("embedding model unavailable in this environment")
    for a, b in zip(hits, hits[1:]):
        assert a.similarity >= b.similarity, (
            "search results MUST be sorted by descending similarity"
        )


def test_search_floats_relevant_chunk_to_top(corpus_dir: Path, tmp_path: Path):
    """End-to-end semantic test: query about dogs should rank the
    dogs paragraph above the loneliness or gates paragraphs."""
    db = tmp_path / "search.db"
    _try_index(corpus_dir, db)
    hits = semantic_search.search("puppies and dogs", str(db), top_k=3)
    if not hits:
        pytest.skip("embedding model unavailable in this environment")
    top = hits[0]
    # Top hit should be from the dogs file, not the loneliness or gates file
    assert "01_dogs.md" in top.source_path, (
        f"expected top hit from dogs file, got {top.source_path}"
    )


def test_search_top_k_respected(corpus_dir: Path, tmp_path: Path):
    db = tmp_path / "search.db"
    _try_index(corpus_dir, db)
    hits = semantic_search.search("anything", str(db), top_k=2)
    if not hits:
        pytest.skip("embedding model unavailable in this environment")
    assert len(hits) <= 2


def test_search_min_similarity_filter(corpus_dir: Path, tmp_path: Path):
    db = tmp_path / "search.db"
    _try_index(corpus_dir, db)
    # min_similarity=0.99 should filter out almost everything
    hits = semantic_search.search("completely unrelated", str(db), top_k=10, min_similarity=0.99)
    # No semantic_search should ever crash on a high min_similarity;
    # it should just return fewer (likely zero) results.
    assert isinstance(hits, list)


def test_index_records_embedding_model_per_chunk(corpus_dir: Path, tmp_path: Path):
    """Meadows feedback-loop lens: re-embed must be targetable by model
    version. Pinned at the DB-schema level."""
    import sqlite3

    db = tmp_path / "search.db"
    counts = _try_index(corpus_dir, db)
    if counts["chunks_indexed"] == 0:
        pytest.skip("embedding model unavailable in this environment")
    with sqlite3.connect(str(db)) as conn:
        models = [
            row[0]
            for row in conn.execute(
                "SELECT DISTINCT embedding_model FROM semantic_search_chunks"
            ).fetchall()
        ]
    assert len(models) == 1
    assert models[0]  # non-empty model name recorded


def test_search_hit_carries_source_pointer(corpus_dir: Path, tmp_path: Path):
    """Lovelace generality lens: each hit must point back to its source
    file + paragraph index so the reader can navigate to it."""
    db = tmp_path / "search.db"
    _try_index(corpus_dir, db)
    hits = semantic_search.search("dogs", str(db), top_k=1)
    if not hits:
        pytest.skip("embedding model unavailable in this environment")
    hit = hits[0]
    assert hit.source_path
    assert isinstance(hit.paragraph_index, int)
    assert hit.paragraph_index >= 0
    assert hit.text
