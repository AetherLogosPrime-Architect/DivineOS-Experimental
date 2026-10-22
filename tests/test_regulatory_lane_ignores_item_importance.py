"""The regulatory lane must not be steered by an item's importance.

Aria, 2026-10-16, on #675: the earlier test only checked that a constant is 0.5
and that a name does not appear in the lane's source. That passes if the lane
reads ``item.importance_score`` by any other route, and it never runs the lane.

This runs it. Two items identical in everything but importance (0.3 and 0.8) go
through ``retrieve_similarity_only``; their ranks must be equal. The control
that the instrument can find a difference: the same two items through the
ordinary composite DO rank apart.
"""

from __future__ import annotations

import math
import time

import numpy as np
import pytest

from divineos.core import memory_linkage_retriever_v2 as v2
from divineos.core.memory_linkage_retriever import _CachedItem, composite_score


def _unit(angle_deg: float) -> np.ndarray:
    a = math.radians(angle_deg)
    return np.array([math.cos(a), math.sin(a)], dtype=float)


def _item(item_id: str, importance: float, angle: float) -> _CachedItem:
    return _CachedItem(
        id=item_id,
        source="knowledge",  # type: ignore[arg-type]
        tier="topic",  # type: ignore[arg-type]
        title=item_id,
        content=f"content {item_id}",
        path="",
        filed_at_unix=time.time() - 86400,
        importance_score=importance,
        embedding=_unit(angle),
    )


@pytest.fixture(autouse=True)
def _clean():
    v2._reset_v2_state_for_tests()
    yield
    v2._reset_v2_state_for_tests()


def test_the_regulatory_lane_ranks_equal_items_equally_whatever_their_importance(monkeypatch):
    low, high = _item("low", 0.3, 0.0), _item("high", 0.8, 0.0)
    distractors = [_item(f"d{i}", 0.5, 40 + i * 25) for i in range(8)]
    v2._inject_test_cache({"knowledge": [low, high, *distractors]})
    monkeypatch.setattr(v2, "synthesize_topic", lambda prompt, recent: "topic")
    monkeypatch.setattr(v2, "_embed_topic", lambda topic: _unit(0.0))

    out = {p.id: p for p in v2.retrieve_similarity_only("anything")}

    assert "low" in out and "high" in out, "control: both test items must pass the threshold"
    assert out["low"].composite_rank == out["high"].composite_rank
    assert out["low"].importance_score == out["high"].importance_score == v2.REGULATORY_IMPORTANCE


def test_the_ordinary_composite_does_separate_them():
    # The control for the pair above: a difference in importance is visible to the
    # instrument, so equal ranks in the regulatory lane mean something.
    common = dict(similarity=0.7, tier="topic", recency_days=1.0)
    assert composite_score(importance_score=0.8, **common) > composite_score(
        importance_score=0.3, **common
    )
