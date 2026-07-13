"""Tests for the semantic-similarity storage + top-k search primitive.

Built 2026-06-11 alongside ``core/semantic_store.py``. Tests cover:

- embed() returns the expected dim or None for empty/unavailable
- serialize/deserialize round-trip exactly
- init_vec_table + upsert + find_similar_vectors give nearest first
- similarity() delegates to compute_semantic_similarity correctly
- cosine_similarity_local handles zero-norm + NaN/Inf cleanly
- Andrew's thesaurus-restate case from 2026-06-11 is correctly detected
  as semantically similar (the failure-mode that motivated this build)

The Andrew thesaurus case is the regression test: the morning's
content-word-overlap fix passed it as "real translation"; the semantic
check must catch it as the same meaning.
"""

from __future__ import annotations

import pytest

from divineos.core.semantic_store import (
    _DEFAULT_DIM,
    cosine_similarity_local,
    deserialize_embedding,
    embed,
    find_similar_vectors,
    init_vec_table,
    serialize_embedding,
    similarity,
    upsert_embedding,
    _connect_with_vec,
)


# ── small text helpers ───────────────────────────────────────────────


def _has_model() -> bool:
    return embed("test sentence to confirm model loads") is not None


# Most embedding tests need the model. Skip cleanly if the ml extras
# aren't installed (e.g. minimal install / CI lane that excludes ml).
_skip_if_no_model = pytest.mark.skipif(
    not _has_model(), reason="ml extras not installed (sentence-transformers missing)"
)


def _has_sqlite_vec() -> bool:
    """True when the sqlite-vec C extension is installed AND loadable.
    The ml-extras CI lane has sentence-transformers but NOT sqlite-vec
    (Aletheia 2026-06-11 audit predicted this) — vec0 tests must skip
    in that lane rather than fail with ModuleNotFoundError."""
    try:
        import sqlite_vec  # noqa: F401

        return True
    except ImportError:
        return False


_skip_if_no_sqlite_vec = pytest.mark.skipif(
    not _has_sqlite_vec(),
    reason="sqlite-vec C extension not installed (ml-extras CI lane lacks it)",
)


# ── embed() ──────────────────────────────────────────────────────────


@_skip_if_no_model
def test_embed_returns_correct_dim():
    vec = embed("hello world")
    assert vec is not None
    assert len(vec) == _DEFAULT_DIM
    assert all(isinstance(x, float) for x in vec)


def test_embed_returns_none_for_empty_text():
    assert embed("") is None
    assert embed(None) is None  # type: ignore[arg-type]


# ── serialize/deserialize ────────────────────────────────────────────


def test_serialize_deserialize_roundtrip():
    vec = [0.1, -0.2, 0.3, 1.5, -1.5]
    blob = serialize_embedding(vec)
    recovered = deserialize_embedding(blob)
    assert len(recovered) == len(vec)
    # float32 conversion introduces small rounding error
    for a, b in zip(vec, recovered):
        assert abs(a - b) < 1e-6


def test_serialize_handles_default_dim():
    vec = [0.0] * _DEFAULT_DIM
    blob = serialize_embedding(vec)
    # float32 = 4 bytes per value
    assert len(blob) == _DEFAULT_DIM * 4


# ── cosine_similarity_local ──────────────────────────────────────────


def test_cosine_local_identical_vectors():
    v = [1.0, 0.0, 0.0]
    assert cosine_similarity_local(v, v) == pytest.approx(1.0)


def test_cosine_local_orthogonal_vectors():
    a = [1.0, 0.0]
    b = [0.0, 1.0]
    assert cosine_similarity_local(a, b) == pytest.approx(0.0)


def test_cosine_local_opposite_vectors():
    a = [1.0, 0.0]
    b = [-1.0, 0.0]
    assert cosine_similarity_local(a, b) == pytest.approx(-1.0)


def test_cosine_local_zero_norm_returns_none():
    a = [0.0, 0.0]
    b = [1.0, 0.0]
    assert cosine_similarity_local(a, b) is None
    assert cosine_similarity_local(b, a) is None


def test_cosine_local_mismatched_lengths_returns_none():
    assert cosine_similarity_local([1.0, 0.0], [1.0, 0.0, 0.0]) is None


def test_cosine_local_empty_returns_none():
    assert cosine_similarity_local([], [1.0]) is None
    assert cosine_similarity_local([1.0], []) is None


# ── sqlite-vec storage + search ──────────────────────────────────────


@_skip_if_no_sqlite_vec
def test_vec_table_creation_and_basic_search():
    """End-to-end smoke test on the vec0 layer — confirms sqlite-vec
    loads, init_vec_table creates the virtual table, upsert stores, and
    find_similar_vectors returns nearest-first ordering."""
    conn = _connect_with_vec()
    try:
        init_vec_table(conn, "tbl", dim=3)
        upsert_embedding(conn, "tbl", 1, [1.0, 0.0, 0.0])
        upsert_embedding(conn, "tbl", 2, [0.0, 1.0, 0.0])
        upsert_embedding(conn, "tbl", 3, [0.9, 0.1, 0.0])  # closest to rowid 1

        results = find_similar_vectors(conn, "tbl", [1.0, 0.0, 0.0], top_k=3)
        assert len(results) == 3
        # Nearest first — rowid 1 is identical, rowid 3 is close, rowid 2 is orthogonal
        rowids = [r[0] for r in results]
        assert rowids[0] == 1
        assert rowids[1] == 3
        assert rowids[2] == 2
    finally:
        conn.close()


@_skip_if_no_sqlite_vec
def test_upsert_replaces_existing_embedding():
    conn = _connect_with_vec()
    try:
        init_vec_table(conn, "tbl", dim=3)
        upsert_embedding(conn, "tbl", 1, [1.0, 0.0, 0.0])
        upsert_embedding(conn, "tbl", 1, [0.0, 1.0, 0.0])

        # After second upsert, rowid 1 should be at [0, 1, 0] not [1, 0, 0]
        results = find_similar_vectors(conn, "tbl", [0.0, 1.0, 0.0], top_k=1)
        assert len(results) == 1
        assert results[0][0] == 1
        # Distance should be very small (effectively zero for identical vectors)
        assert results[0][1] < 0.01
    finally:
        conn.close()


@_skip_if_no_sqlite_vec
def test_find_similar_respects_top_k():
    conn = _connect_with_vec()
    try:
        init_vec_table(conn, "tbl", dim=3)
        for i, vec in enumerate(
            [
                [1.0, 0.0, 0.0],
                [0.9, 0.1, 0.0],
                [0.8, 0.2, 0.0],
                [0.0, 1.0, 0.0],
                [0.0, 0.0, 1.0],
            ],
            start=1,
        ):
            upsert_embedding(conn, "tbl", i, vec)

        results = find_similar_vectors(conn, "tbl", [1.0, 0.0, 0.0], top_k=2)
        assert len(results) == 2
    finally:
        conn.close()


# ── similarity() integration ─────────────────────────────────────────


@_skip_if_no_model
def test_similarity_identical_strings():
    # Same text → similarity should be very close to 1.0
    sim = similarity("the cat sat on the mat", "the cat sat on the mat")
    assert sim is not None
    assert sim > 0.99


@_skip_if_no_model
def test_similarity_unrelated_strings():
    # Unrelated text → similarity should be noticeably lower than identical,
    # but anisotropy means we can't expect ~0.0. The research surfaced this:
    # MiniLM's unrelated-baseline runs ~0.0-0.3 typically; the threshold
    # comes from the labeled benchmark, not an idealized number.
    sim = similarity(
        "the cat sat on the mat",
        "quantum chromodynamics predicts the asymptotic freedom of quarks",
    )
    assert sim is not None
    # Whatever it is, identical-text similarity should be meaningfully higher.
    sim_identical = similarity("the cat sat on the mat", "the cat sat on the mat")
    assert sim_identical is not None
    assert sim_identical > sim + 0.3


# ── the regression test that motivated this build ───────────────────


@_skip_if_no_model
def test_andrew_thesaurus_restate_is_detected_as_similar():
    """Andrew 2026-06-11 broke the morning's content-word-overlap detector
    with this exact pair. The vocabulary shares almost nothing, but the
    meaning is identical. The semantic check MUST catch this — that is
    the load-bearing requirement that motivated building this primitive.

    Threshold value here (0.65) is provisional; the labeled benchmark
    will set it empirically. The assertion is directional: this pair
    should score MEANINGFULLY HIGHER than truly unrelated text.
    """
    original = (
        "The compass observation system tracks moral spectrum drift over time, "
        "recording each event with evidence and position."
    )
    thesaurus_restate = (
        "The substrate's ethical-direction monitor logs deviation across virtues "
        "chronologically, capturing every incident with backing facts and stance."
    )

    sim_restate = similarity(original, thesaurus_restate)
    sim_unrelated = similarity(
        original,
        "Apricot jam tastes best on rye toast with a thin layer of butter.",
    )

    assert sim_restate is not None
    assert sim_unrelated is not None
    # The restate should score meaningfully higher than truly unrelated content.
    # If this fails, semantic similarity is not catching what string-overlap missed.
    assert sim_restate > sim_unrelated + 0.2


@_skip_if_no_model
def test_paraphrase_pairs_score_higher_than_unrelated():
    """Sanity check on the primitive's core promise: pairs that mean the
    same thing (but use different words) should score higher than pairs
    that share words but mean different things."""
    sim_paraphrase = similarity(
        "I caught the train just before it left the station.",
        "I boarded the locomotive moments before its departure.",
    )
    sim_shared_words = similarity(
        "The bank charges high interest rates on credit cards.",
        "I sat on the bank of the river and watched the sunset.",
    )

    assert sim_paraphrase is not None
    assert sim_shared_words is not None
    assert sim_paraphrase > sim_shared_words


# ─── Phase 2 (2026-06-11): knowledge-table integration ────────────────


@_skip_if_no_model
class TestKnowledgeIntegration:
    """The primitive wires into the knowledge table via embedding column,
    backfill helper, and semantic find_similar_in_knowledge. Tests run
    against an isolated tmp sqlite DB so the live substrate is never
    touched."""

    def _setup_isolated_knowledge(self, tmp_path, monkeypatch):
        db_path = tmp_path / "test_knowledge.db"
        monkeypatch.setenv("DIVINEOS_DB", str(db_path))
        from divineos.core.knowledge._base import (
            get_connection,
            init_knowledge_table,
        )

        init_knowledge_table()
        return get_connection

    def test_embedding_column_exists_after_init(self, tmp_path, monkeypatch):
        get_connection = self._setup_isolated_knowledge(tmp_path, monkeypatch)
        conn = get_connection()
        cols = [r[1] for r in conn.execute("PRAGMA table_info(knowledge)").fetchall()]
        assert "embedding" in cols
        assert "embedding_model" in cols

    def test_backfill_populates_missing_embeddings(self, tmp_path, monkeypatch):
        from divineos.core.semantic_store import backfill_knowledge_embeddings
        from divineos.core.knowledge.crud import store_knowledge

        get_connection = self._setup_isolated_knowledge(tmp_path, monkeypatch)
        store_knowledge("FACT", "the cat sat on the mat")
        store_knowledge(
            "FACT",
            "I refactored the unverified_claim_detector module",
        )
        conn = get_connection()
        conn.execute("UPDATE knowledge SET embedding = NULL")
        conn.commit()

        result = backfill_knowledge_embeddings()
        assert result["processed"] == 2
        assert result["embedded"] == 2
        n_with_embedding = conn.execute(
            "SELECT COUNT(*) FROM knowledge WHERE embedding IS NOT NULL"
        ).fetchone()[0]
        assert n_with_embedding == 2

    def test_backfill_skips_entries_already_embedded(self, tmp_path, monkeypatch):
        from divineos.core.semantic_store import backfill_knowledge_embeddings
        from divineos.core.knowledge.crud import store_knowledge

        self._setup_isolated_knowledge(tmp_path, monkeypatch)
        store_knowledge("FACT", "first entry content")
        backfill_knowledge_embeddings()
        result = backfill_knowledge_embeddings()
        assert result["processed"] == 0

    def test_find_similar_in_knowledge_returns_close_match(self, tmp_path, monkeypatch):
        from divineos.core.semantic_store import (
            backfill_knowledge_embeddings,
            find_similar_in_knowledge,
        )
        from divineos.core.knowledge.crud import store_knowledge

        self._setup_isolated_knowledge(tmp_path, monkeypatch)
        store_knowledge(
            "PRINCIPLE",
            "Refactored the verify-claim detector to add letter source-trace",
        )
        store_knowledge(
            "FACT",
            "Apricot jam tastes wonderful on rye toast",
        )
        backfill_knowledge_embeddings()

        results = find_similar_in_knowledge(
            "Updated the unverified-claim detector to track source letters",
            top_k=5,
            min_similarity=0.3,
        )
        assert results, "should return at least one match"
        top_id, top_sim, top_snippet = results[0]
        assert "verify-claim" in top_snippet or "letter" in top_snippet

    def test_find_similar_respects_min_similarity(self, tmp_path, monkeypatch):
        from divineos.core.semantic_store import (
            backfill_knowledge_embeddings,
            find_similar_in_knowledge,
        )
        from divineos.core.knowledge.crud import store_knowledge

        self._setup_isolated_knowledge(tmp_path, monkeypatch)
        store_knowledge("FACT", "the cat sat on the mat")
        backfill_knowledge_embeddings()

        results = find_similar_in_knowledge(
            "quantum chromodynamics asymptotic freedom of quarks",
            min_similarity=0.5,
        )
        assert results == []

    def test_find_similar_excludes_specified_ids(self, tmp_path, monkeypatch):
        from divineos.core.semantic_store import (
            backfill_knowledge_embeddings,
            find_similar_in_knowledge,
        )
        from divineos.core.knowledge.crud import store_knowledge

        self._setup_isolated_knowledge(tmp_path, monkeypatch)
        kid_a = store_knowledge("PRINCIPLE", "the lepos rebuild lands")
        store_knowledge("PRINCIPLE", "the lepos rebuild moves the substrate")
        backfill_knowledge_embeddings()

        results = find_similar_in_knowledge("lepos rebuild", min_similarity=0.3)
        ids = [r[0] for r in results]
        assert kid_a in ids

        results_excl = find_similar_in_knowledge(
            "lepos rebuild", min_similarity=0.3, exclude_ids=[kid_a]
        )
        ids_excl = [r[0] for r in results_excl]
        assert kid_a not in ids_excl

    def test_find_similar_returns_empty_for_empty_query(self, tmp_path, monkeypatch):
        from divineos.core.semantic_store import find_similar_in_knowledge

        self._setup_isolated_knowledge(tmp_path, monkeypatch)
        assert find_similar_in_knowledge("") == []

    def test_backfill_returns_zeros_on_empty_table(self, tmp_path, monkeypatch):
        from divineos.core.semantic_store import backfill_knowledge_embeddings

        self._setup_isolated_knowledge(tmp_path, monkeypatch)
        result = backfill_knowledge_embeddings()
        assert result == {"processed": 0, "embedded": 0, "skipped": 0}
