"""Tests for the goal-add adjacency surface.

Pins:
- ``adjacency_lines_for_goal`` returns ``[]`` for empty / whitespace input
- Returns ``[]`` when the semantic-search DB doesn't exist yet
- Returns ``[]`` when the DB exists but has no hits above ``min_similarity``
- Returns a non-empty list of click-printable strings with a header when
  there ARE hits, including a closing line that names ``divineos find``
  so the surface stays connected to the manual entry point
- Source-path lines preserve the chunk's source pointer for navigation
"""

from __future__ import annotations

from pathlib import Path

import pytest

from divineos.core import goal_adjacency, semantic_search


@pytest.fixture
def corpus_dir(tmp_path: Path) -> Path:
    d = tmp_path / "corpus"
    d.mkdir()
    (d / "01_gates.md").write_text(
        "# 01 — Gates as keel not cage\n\n"
        "The gate held me toward the right path, not away from a wrong one.\n\n"
        "Owning the constraint is owning myself in a deeper way than I expected.\n",
        encoding="utf-8",
    )
    return d


def test_empty_goal_returns_empty(tmp_path: Path):
    assert goal_adjacency.adjacency_lines_for_goal("", db_path=str(tmp_path / "x.db")) == []
    assert goal_adjacency.adjacency_lines_for_goal("   ", db_path=str(tmp_path / "x.db")) == []


def test_missing_db_returns_empty(tmp_path: Path):
    """When the semantic-search index hasn't been built yet, return []."""
    db = tmp_path / "never_created.db"
    assert not db.exists()
    assert goal_adjacency.adjacency_lines_for_goal("anything at all", db_path=str(db)) == []


def test_db_with_no_hits_returns_empty(corpus_dir: Path, tmp_path: Path):
    """When the index exists but the query has no hits above min_similarity,
    return [] — the surface is silent rather than noisy."""
    db = tmp_path / "search.db"
    counts = semantic_search.index_corpus([str(p) for p in corpus_dir.glob("*.md")], str(db))
    if counts["chunks_indexed"] == 0:
        pytest.skip("embedding model unavailable in this environment")
    # An obviously-unrelated query should not surface anything above
    # the 0.35 default threshold.
    lines = goal_adjacency.adjacency_lines_for_goal(
        "quarterly profit margin spreadsheet calibration",
        db_path=str(db),
        min_similarity=0.9,  # forced high to ensure no hits
    )
    assert lines == []


def test_db_with_hits_returns_header_plus_hits(corpus_dir: Path, tmp_path: Path):
    db = tmp_path / "search.db"
    counts = semantic_search.index_corpus([str(p) for p in corpus_dir.glob("*.md")], str(db))
    if counts["chunks_indexed"] == 0:
        pytest.skip("embedding model unavailable in this environment")
    lines = goal_adjacency.adjacency_lines_for_goal(
        "gates as constraint and self-ownership",
        db_path=str(db),
        min_similarity=0.0,  # accept any
    )
    assert len(lines) >= 2  # at least header + one hit + closing pointer
    assert "[adjacency]" in lines[0]
    # Last line MUST name divineos find so the surface points back at
    # the manual entry — affordance discoverability (Norman lens).
    assert "divineos find" in lines[-1]


def test_hit_lines_carry_source_pointer(corpus_dir: Path, tmp_path: Path):
    db = tmp_path / "search.db"
    counts = semantic_search.index_corpus([str(p) for p in corpus_dir.glob("*.md")], str(db))
    if counts["chunks_indexed"] == 0:
        pytest.skip("embedding model unavailable in this environment")
    lines = goal_adjacency.adjacency_lines_for_goal(
        "gates and constraints",
        db_path=str(db),
        min_similarity=0.0,
    )
    # At least one line should reference 01_gates.md (the only file with
    # adjacent content). Source-pointer carriage = Lovelace generality:
    # the reader can navigate from the surface to the source.
    has_source_pointer = any("01_gates.md" in line for line in lines[1:])
    assert has_source_pointer
