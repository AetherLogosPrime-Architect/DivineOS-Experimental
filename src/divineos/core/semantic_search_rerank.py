"""Cross-encoder rerank pass for ``semantic_search`` results.

The first-pass `search()` returns hits sorted by cosine-similarity of
query and chunk embeddings — fast and good-enough for surfacing
candidates, but bi-encoder similarity often mis-ranks near-tie cases
where two chunks both embed similarly to the query but one is
substantively more relevant.

A cross-encoder reads (query, chunk) as a single sequence and produces
a single relevance score. It's slower per pair than embedding lookup
but reads BOTH sides jointly, so it's better at "which of these
embedding-similar chunks actually answers the question." Standard
two-stage IR pattern: bi-encoder recalls a large candidate pool,
cross-encoder ranks the top of it.

## Pattern

    from divineos.core.semantic_search import search
    from divineos.core.semantic_search_rerank import rerank

    # Fetch a wider pool from the first pass so the reranker has
    # candidates to choose from. Reranking the same top_k it was
    # going to return wastes the cross-encoder's lift.
    candidates = search(query, db_path, top_k=25)
    reranked = rerank(query, candidates)
    # `reranked` is sorted by descending rerank_score; len == len(candidates)
    # unless `top_k` is passed.
    top_5 = reranked[:5]

## Model

Default is ``cross-encoder/ms-marco-MiniLM-L-6-v2`` — small (~80MB),
fast, well-tested. Trained on MS MARCO passage-ranking which is a
reasonable proxy for "which paragraph answers this question." Can be
overridden via the ``model_name`` argument.

## Device

Uses ``divineos.core._embedding_device.select_device()`` for GPU
routing. Same plumbing as embeddings; honors the same env override.

## Failure shape

If sentence-transformers / torch isn't installed or the model fails
to load, ``rerank()`` returns the input list UNCHANGED (with
``rerank_score`` left as None). Fail-soft: a rerank that can't run
should not lose results, just leave them on first-pass ordering.

## Tests

See ``tests/test_semantic_search_rerank.py``. The CrossEncoder
``predict`` call is mocked there so tests don't pull the model.
"""

from __future__ import annotations

import logging
from typing import Any

from divineos.core.semantic_search import SearchHit

logger = logging.getLogger(__name__)

# Default model. Small enough to load on CPU, accurate enough for
# paragraph-relevance ranking, well-supported by sentence-transformers.
DEFAULT_RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


def _load_cross_encoder(model_name: str) -> Any | None:
    """Load the cross-encoder model, routing to GPU when available.

    Returns the loaded model or None on any import/load failure.
    Failure paths covered:
      - sentence-transformers not installed
      - torch not installed
      - model download fails (offline, network error)
      - device-resolution import fails
    """
    try:
        from sentence_transformers import CrossEncoder
    except ImportError:
        logger.info("sentence-transformers not installed; rerank pass is a no-op.")
        return None
    try:
        from divineos.core._embedding_device import select_device

        device = select_device()
    except Exception:  # noqa: BLE001 — fall back to letting torch pick
        device = None
    try:
        if device:
            return CrossEncoder(model_name, device=device)
        return CrossEncoder(model_name)
    except Exception as exc:  # noqa: BLE001 — broad catch at model-load boundary
        logger.warning("CrossEncoder load failed for %s: %s", model_name, exc)
        return None


def rerank(
    query: str,
    hits: list[SearchHit],
    *,
    model_name: str = DEFAULT_RERANK_MODEL,
    top_k: int | None = None,
) -> list[SearchHit]:
    """Re-rank ``hits`` by cross-encoder relevance to ``query``.

    Returns a NEW list of ``SearchHit`` objects (the originals are not
    mutated) with the ``rerank_score`` field populated and sorted by
    descending rerank_score. If ``top_k`` is set, truncates to that
    many results.

    Empty hits, empty query, or model unavailable → returns the input
    list unchanged (with rerank_score still None). Fail-soft.
    """
    if not hits or not query.strip():
        return list(hits)
    model = _load_cross_encoder(model_name)
    if model is None:
        return list(hits)
    pairs = [(query, h.text) for h in hits]
    try:
        scores = model.predict(pairs)
    except Exception as exc:  # noqa: BLE001 — model-call boundary
        logger.warning("CrossEncoder predict failed: %s", exc)
        return list(hits)
    rescored: list[SearchHit] = []
    for hit, score in zip(hits, scores, strict=False):
        rescored.append(
            SearchHit(
                source_path=hit.source_path,
                paragraph_index=hit.paragraph_index,
                text=hit.text,
                similarity=hit.similarity,
                rerank_score=float(score),
            )
        )
    rescored.sort(
        key=lambda h: h.rerank_score if h.rerank_score is not None else float("-inf"),
        reverse=True,
    )
    if top_k is not None:
        rescored = rescored[:top_k]
    return rescored


__all__ = ["DEFAULT_RERANK_MODEL", "rerank"]
