"""Tests for ``semantic_search_rerank.rerank``.

The CrossEncoder ``predict`` call is mocked throughout so tests don't
need to pull the actual model — fast and isolation-safe.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from divineos.core.semantic_search import SearchHit
from divineos.core.semantic_search_rerank import rerank


def _hit(text: str, similarity: float = 0.5, source: str = "doc.md", idx: int = 0) -> SearchHit:
    return SearchHit(
        source_path=source,
        paragraph_index=idx,
        text=text,
        similarity=similarity,
    )


def test_rerank_empty_hits_returns_empty():
    assert rerank("query", []) == []


def test_rerank_empty_query_returns_input_unchanged():
    hits = [_hit("alpha", similarity=0.9), _hit("beta", similarity=0.8)]
    out = rerank("", hits)
    assert [h.text for h in out] == ["alpha", "beta"]
    assert all(h.rerank_score is None for h in out)


def test_rerank_model_unavailable_returns_input_unchanged():
    """If the cross-encoder fails to load, results pass through
    untouched. Fail-soft contract."""
    hits = [_hit("alpha", similarity=0.9), _hit("beta", similarity=0.8)]
    with patch(
        "divineos.core.semantic_search_rerank._load_cross_encoder",
        return_value=None,
    ):
        out = rerank("query", hits)
    assert [h.text for h in out] == ["alpha", "beta"]
    assert all(h.rerank_score is None for h in out)


def test_rerank_reorders_by_score():
    """When the cross-encoder gives higher scores to lower-similarity
    hits, the reranked order reflects the cross-encoder verdict."""
    # First-pass order: alpha (0.95), beta (0.90), gamma (0.85)
    hits = [
        _hit("alpha", similarity=0.95),
        _hit("beta", similarity=0.90),
        _hit("gamma", similarity=0.85),
    ]
    # Cross-encoder thinks gamma is most relevant, alpha least.
    model = MagicMock()
    model.predict.return_value = [0.1, 0.5, 0.9]  # alpha, beta, gamma
    with patch(
        "divineos.core.semantic_search_rerank._load_cross_encoder",
        return_value=model,
    ):
        out = rerank("query", hits)
    assert [h.text for h in out] == ["gamma", "beta", "alpha"]
    # Original similarity preserved on each
    assert out[0].similarity == 0.85
    assert out[1].similarity == 0.90
    assert out[2].similarity == 0.95
    # Rerank scores populated
    assert out[0].rerank_score == 0.9
    assert out[1].rerank_score == 0.5
    assert out[2].rerank_score == 0.1


def test_rerank_top_k_truncates():
    """top_k truncation is applied AFTER reranking, so the post-rerank
    top-K reflects the cross-encoder's ranking, not the first-pass."""
    hits = [
        _hit("a", similarity=0.95),
        _hit("b", similarity=0.90),
        _hit("c", similarity=0.85),
        _hit("d", similarity=0.80),
    ]
    model = MagicMock()
    model.predict.return_value = [0.1, 0.5, 0.9, 0.3]
    with patch(
        "divineos.core.semantic_search_rerank._load_cross_encoder",
        return_value=model,
    ):
        out = rerank("query", hits, top_k=2)
    assert len(out) == 2
    assert [h.text for h in out] == ["c", "b"]  # top-2 by rerank score


def test_rerank_predict_failure_returns_input_unchanged():
    """If predict() raises (model OOM, NaN inputs, etc.), the rerank
    passes through untouched. Fail-soft contract."""
    hits = [_hit("alpha", similarity=0.9), _hit("beta", similarity=0.8)]
    model = MagicMock()
    model.predict.side_effect = RuntimeError("CUDA OOM")
    with patch(
        "divineos.core.semantic_search_rerank._load_cross_encoder",
        return_value=model,
    ):
        out = rerank("query", hits)
    assert [h.text for h in out] == ["alpha", "beta"]
    assert all(h.rerank_score is None for h in out)


def test_rerank_does_not_mutate_input():
    """The input list and its hits are not modified — pure function."""
    hits = [_hit("alpha", similarity=0.9), _hit("beta", similarity=0.8)]
    model = MagicMock()
    model.predict.return_value = [0.1, 0.5]
    with patch(
        "divineos.core.semantic_search_rerank._load_cross_encoder",
        return_value=model,
    ):
        rerank("query", hits)
    assert hits[0].rerank_score is None
    assert hits[1].rerank_score is None


def test_rerank_query_strip_is_what_counts():
    """A query of just whitespace is treated as empty."""
    hits = [_hit("alpha", similarity=0.9)]
    out = rerank("   \t  ", hits)
    assert [h.text for h in out] == ["alpha"]
    assert out[0].rerank_score is None
