"""Adapter + Q2-assertion tests for Aria's retriever v1 — Aria's half of the split.

Per pass-3 tests-split-C: Aether wrote the math (composite_score,
tier_weight, recency_multiplier, compute_threshold). This file covers:

1. Q2 assertion enforcement — _downweight_importance MUST raise on
   constraint-tier items. Aletheia's audit block lives here as code;
   removing the assertion is the exact failure mode this test guards.
2. Source-adapter invariants — tier assignment per §Q4, defensive
   fallbacks on load errors, and the specific parsing/dedup logic
   each adapter owns.

Tests use monkeypatch to swap the store boundary — real substrate state
is volatile session-to-session, so we mock the underlying store call
(NOT the code under test) and verify the adapter's own logic.
Filesystem-based adapters use tmp_path fixtures.
"""

from __future__ import annotations

import sqlite3

import numpy as np
import pytest

from divineos.core import memory_linkage_retriever as mlr


# ---------------------------------------------------------------------------
# Q2 assertion — Aletheia's audit block enforced at code level
# ---------------------------------------------------------------------------


def test_downweight_importance_raises_on_constraint_tier():
    """§Q2 exemption: constraint-tier items are boost-only. Any caller
    attempting to downweight a constraint must trip loudly. Removing
    the assertion is the exact failure mode this test guards against."""
    with pytest.raises(AssertionError, match="§Q2 EXEMPTION VIOLATED"):
        mlr._downweight_importance("some-constraint-id", "constraint", -0.1)


def test_downweight_importance_allowed_on_topic_tier():
    """Topic-tier is full-loop per §Q2 — downweight on ignore is
    permitted. If this test fails, §Q2 got over-applied."""
    mlr._downweight_importance("some-topic-id", "topic", -0.1)  # no raise


def test_downweight_importance_message_names_the_item():
    """The assertion diagnostic must name the offending item_id so a
    future debugger sees WHICH item tripped the exemption, not just
    that one did."""
    with pytest.raises(AssertionError) as exc_info:
        mlr._downweight_importance("correction-42-1700000000", "constraint", -0.5)
    assert "correction-42-1700000000" in str(exc_info.value)


# ---------------------------------------------------------------------------
# _load_corrections — tier=constraint per §Q4, defensive fallbacks
# ---------------------------------------------------------------------------


def test_load_corrections_returns_empty_when_import_fails(monkeypatch):
    """If divineos.core.corrections is unavailable, adapter returns []
    rather than crashing. Behavior-neutral fallback per the source-
    adapter defensive pattern."""

    # Break the import path
    import sys as _sys

    monkeypatch.setitem(_sys.modules, "divineos.core.corrections", None)
    result = mlr._load_corrections()
    assert result == []


def test_load_corrections_skips_empty_text(monkeypatch):
    """Corrections with empty or whitespace-only text are skipped —
    embedding an empty string produces a degenerate vector and would
    surface as noise."""

    def fake_corrections():
        return [
            {"text": "", "timestamp": 1700000000.0},
            {"text": "   ", "timestamp": 1700000001.0},
            {"text": "real correction content", "timestamp": 1700000002.0},
        ]

    import divineos.core.corrections as cmod

    monkeypatch.setattr(cmod, "corrections_with_status", fake_corrections)
    # Also stub embedding so the test doesn't require sentence-transformers.
    monkeypatch.setattr(mlr, "_embed_text_impl", lambda text: np.ones(4, dtype=np.float32))

    result = mlr._load_corrections()
    assert len(result) == 1
    assert result[0].content == "real correction content"


def test_load_corrections_assigns_constraint_tier(monkeypatch):
    """All corrections are Andrew-corrections by construction (per
    correction_commands.py) — default tier is constraint per §Q4."""

    def fake_corrections():
        return [{"text": "test correction", "timestamp": 1700000000.0}]

    import divineos.core.corrections as cmod

    monkeypatch.setattr(cmod, "corrections_with_status", fake_corrections)
    monkeypatch.setattr(mlr, "_embed_text_impl", lambda text: np.ones(4, dtype=np.float32))

    result = mlr._load_corrections()
    assert len(result) == 1
    assert result[0].tier == "constraint"
    assert result[0].source == "correction"


def test_load_corrections_skips_items_with_failed_embedding(monkeypatch):
    """If _embed_text_impl returns None (model load failure), the item
    is skipped rather than the whole load crashing."""

    def fake_corrections():
        return [
            {"text": "will fail", "timestamp": 1700000000.0},
            {"text": "will succeed", "timestamp": 1700000001.0},
        ]

    import divineos.core.corrections as cmod

    monkeypatch.setattr(cmod, "corrections_with_status", fake_corrections)

    embed_calls = {"n": 0}

    def flaky_embed(text: str):
        embed_calls["n"] += 1
        return None if "fail" in text else np.ones(4, dtype=np.float32)

    monkeypatch.setattr(mlr, "_embed_text_impl", flaky_embed)

    result = mlr._load_corrections()
    assert embed_calls["n"] == 2
    assert len(result) == 1
    assert "succeed" in result[0].content


# ---------------------------------------------------------------------------
# _load_knowledge — tier per §Q4, pre-stored embedding reuse
# ---------------------------------------------------------------------------


def _make_fake_knowledge_conn(rows):
    """Build an in-memory sqlite connection whose knowledge query returns
    the supplied rows. Rows are 6-tuples matching the adapter's SELECT."""
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE knowledge ("
        "knowledge_id TEXT, knowledge_type TEXT, content TEXT, "
        "created_at REAL, embedding BLOB, embedding_model TEXT, "
        "superseded_by TEXT)"
    )
    for row in rows:
        conn.execute(
            "INSERT INTO knowledge VALUES (?, ?, ?, ?, ?, ?, NULL)",
            row,
        )
    conn.commit()
    return conn


@pytest.mark.parametrize(
    "ktype,expected_tier",
    [
        ("PRINCIPLE", "constraint"),
        ("DIRECTIVE", "constraint"),
        ("BOUNDARY", "constraint"),
        ("DIRECTION", "constraint"),
        ("FACT", "topic"),
        ("OBSERVATION", "topic"),
        ("PATTERN", "topic"),
        ("INSTRUCTION", "topic"),
        ("EPISODE", "topic"),
        ("MISTAKE", "topic"),
        ("PREFERENCE", "topic"),
        ("PROCEDURE", "topic"),
    ],
)
def test_load_knowledge_tier_assignment_per_q4(monkeypatch, ktype, expected_tier):
    """Per §Q4: PRINCIPLE / DIRECTIVE / BOUNDARY / DIRECTION are
    identity-shaping / optimizer-guardrail → constraint tier. All other
    types are informational → topic tier. Drift on this mapping would
    break the whole tier-weighted ranking."""
    fake_conn = _make_fake_knowledge_conn(
        [("kid-1", ktype, "some content", 1700000000.0, None, None)]
    )

    import divineos.core.knowledge._base as kbase

    monkeypatch.setattr(kbase, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(mlr, "_embed_text_impl", lambda text: np.ones(4, dtype=np.float32))

    result = mlr._load_knowledge()
    assert len(result) == 1
    assert result[0].tier == expected_tier
    assert result[0].source == "knowledge"


def test_load_knowledge_reuses_prestored_embedding_when_model_matches(monkeypatch):
    """When a knowledge row has a pre-stored embedding and the
    embedding_model matches ours (all-MiniLM-L6-v2), the adapter must
    reuse it rather than re-embed. This is a load-time performance
    invariant — with 84/209 rows pre-embedded, doubling that work
    would double load time."""
    known_vec = np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float32)
    fake_conn = _make_fake_knowledge_conn(
        [
            (
                "kid-1",
                "FACT",
                "content",
                1700000000.0,
                known_vec.tobytes(),
                "all-MiniLM-L6-v2",
            )
        ]
    )

    import divineos.core.knowledge._base as kbase

    monkeypatch.setattr(kbase, "get_connection", lambda: fake_conn)

    def should_not_be_called(text: str):
        pytest.fail("_embed_text_impl should not be called when pre-stored embedding is present")

    monkeypatch.setattr(mlr, "_embed_text_impl", should_not_be_called)

    result = mlr._load_knowledge()
    assert len(result) == 1
    np.testing.assert_array_equal(result[0].embedding, known_vec)


def test_load_knowledge_reembeds_when_model_mismatches(monkeypatch):
    """If the pre-stored embedding is from a different model, the
    adapter must re-embed with OUR model — cross-model cosine similarity
    is meaningless. Silent reuse would produce nonsense rankings."""
    other_vec = np.array([5.0, 6.0, 7.0, 8.0], dtype=np.float32)
    fake_conn = _make_fake_knowledge_conn(
        [
            (
                "kid-1",
                "FACT",
                "content",
                1700000000.0,
                other_vec.tobytes(),
                "different-model",
            )
        ]
    )

    import divineos.core.knowledge._base as kbase

    monkeypatch.setattr(kbase, "get_connection", lambda: fake_conn)
    our_vec = np.array([9.0, 9.0, 9.0, 9.0], dtype=np.float32)
    monkeypatch.setattr(mlr, "_embed_text_impl", lambda text: our_vec)

    result = mlr._load_knowledge()
    assert len(result) == 1
    np.testing.assert_array_equal(result[0].embedding, our_vec)


def test_load_knowledge_returns_empty_when_base_import_fails(monkeypatch):
    """Behavior-neutral fallback pattern — if the knowledge module
    isn't importable, adapter returns [] rather than crashing."""
    import sys as _sys

    monkeypatch.setitem(_sys.modules, "divineos.core.knowledge._base", None)
    assert mlr._load_knowledge() == []


# ---------------------------------------------------------------------------
# _load_exploration — filesystem walk, topic tier, tmp_path fixtures
# ---------------------------------------------------------------------------


def test_load_exploration_walks_tree_and_embeds(monkeypatch, tmp_path):
    """Adapter must recursively walk exploration/**/*.md and produce
    one _CachedItem per file. Subdirectory nesting must not be lost."""
    root = tmp_path / "exploration"
    root.mkdir()
    (root / "01_first.md").write_text("first content", encoding="utf-8")
    subdir = root / "aria"
    subdir.mkdir()
    (subdir / "02_nested.md").write_text("nested content", encoding="utf-8")

    monkeypatch.setattr(mlr, "_find_exploration_root", lambda: root)
    monkeypatch.setattr(mlr, "_embed_text_impl", lambda text: np.ones(4, dtype=np.float32))

    result = mlr._load_exploration()
    contents = sorted(item.content for item in result)
    assert contents == ["first content", "nested content"]
    assert all(item.tier == "topic" for item in result)
    assert all(item.source == "exploration" for item in result)


def test_load_exploration_returns_empty_when_root_missing(monkeypatch):
    """If exploration/ doesn't exist on any known project root,
    adapter returns [] cleanly rather than raising."""
    monkeypatch.setattr(mlr, "_find_exploration_root", lambda: None)
    assert mlr._load_exploration() == []


def test_load_exploration_skips_empty_files(monkeypatch, tmp_path):
    """Empty markdown files (created but never written) must be skipped
    to avoid degenerate embeddings entering the cache."""
    root = tmp_path / "exploration"
    root.mkdir()
    (root / "empty.md").write_text("", encoding="utf-8")
    (root / "real.md").write_text("real content", encoding="utf-8")

    monkeypatch.setattr(mlr, "_find_exploration_root", lambda: root)
    monkeypatch.setattr(mlr, "_embed_text_impl", lambda text: np.ones(4, dtype=np.float32))

    result = mlr._load_exploration()
    assert len(result) == 1
    assert result[0].content == "real content"


# ---------------------------------------------------------------------------
# _load_letters — cross-worktree dedup by resolved path
# ---------------------------------------------------------------------------


def test_load_letters_dedupes_across_roots(monkeypatch, tmp_path):
    """When multiple worktrees expose the same letter dir via different
    _PROJECT_ROOTS entries, resolved-path dedup must prevent the same
    file from being loaded twice. Otherwise the cache would double-count
    every letter and the composite ranking would be skewed."""
    shared = tmp_path / "shared_letters"
    shared.mkdir()
    (shared / "letter.md").write_text("shared letter", encoding="utf-8")

    monkeypatch.setattr(mlr, "_find_letters_roots", lambda: [shared, shared])
    monkeypatch.setattr(mlr, "_embed_text_impl", lambda text: np.ones(4, dtype=np.float32))

    result = mlr._load_letters()
    assert len(result) == 1
    assert result[0].content == "shared letter"


def test_load_letters_returns_empty_when_no_roots(monkeypatch):
    """If no letter directories exist on any known project root,
    adapter returns [] rather than crashing."""
    monkeypatch.setattr(mlr, "_find_letters_roots", lambda: [])
    assert mlr._load_letters() == []


# ---------------------------------------------------------------------------
# _load_wall — heading split, curation-boost importance
# ---------------------------------------------------------------------------


def test_load_wall_splits_on_heading(monkeypatch, tmp_path):
    """Wall file is split on '\\n## ' — each heading becomes one item.
    Preamble before the first heading must NOT become an item."""
    wall = tmp_path / "MEMORY.md"
    wall.write_text(
        "# Wall preamble\n\nThis is intro text.\n\n"
        "## Entry one\n\nBody of first entry.\n\n"
        "## Entry two\n\nBody of second entry.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(mlr, "_find_wall_path", lambda: wall)
    monkeypatch.setattr(mlr, "_embed_text_impl", lambda text: np.ones(4, dtype=np.float32))

    result = mlr._load_wall()
    titles = sorted(item.title for item in result)
    assert titles == ["Entry one", "Entry two"]


def test_load_wall_applies_curation_boost(monkeypatch, tmp_path):
    """Wall entries get importance_score=0.6 (vs the 0.5 baseline
    other sources use) because the wall is a curated surface. Losing
    the boost would make wall entries compete equally with raw content
    — defeating the curation."""
    wall = tmp_path / "MEMORY.md"
    wall.write_text(
        "# Wall preamble\n\nIntro.\n\n## Just one\n\nBody.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(mlr, "_find_wall_path", lambda: wall)
    monkeypatch.setattr(mlr, "_embed_text_impl", lambda text: np.ones(4, dtype=np.float32))

    result = mlr._load_wall()
    assert len(result) == 1
    assert result[0].importance_score == 0.6
    assert result[0].tier == "topic"
    assert result[0].source == "wall"


def test_load_wall_returns_empty_when_file_missing(monkeypatch):
    """No wall file on any known project root → [] fallback."""
    monkeypatch.setattr(mlr, "_find_wall_path", lambda: None)
    assert mlr._load_wall() == []
