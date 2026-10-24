"""Knowledge entries are ranked by maturity, never by popularity."""

from __future__ import annotations

import inspect

from divineos.core import memory_linkage_retriever_v2 as v2
from divineos.core.memory_linkage_retriever import composite_score, knowledge_importance


def test_maturity_orders_the_base_score():
    scores = [knowledge_importance(m, 0, 0) for m in ("RAW", "HYPOTHESIS", "TESTED", "CONFIRMED")]
    assert scores == sorted(scores) and len(set(scores)) == 4


def test_unknown_or_missing_maturity_is_baseline():
    assert knowledge_importance("WEIRD", 3, 1) == 0.5
    assert knowledge_importance(None, 0, 0) == 0.5


def test_corroboration_and_contradiction_are_capped():
    assert knowledge_importance("TESTED", 4, 0) == knowledge_importance("TESTED", 99, 0)
    assert knowledge_importance("TESTED", 0, 2) == knowledge_importance("TESTED", 0, 99)
    assert knowledge_importance("TESTED", 0, 1) < knowledge_importance("TESTED", 0, 0)


def test_score_is_clamped():
    assert 0.1 <= knowledge_importance("RAW", 0, 2) <= 1.0
    assert knowledge_importance("CONFIRMED", 4, 0) <= 1.0


def test_equal_similarity_and_tier_different_maturity_changes_rank_order():
    kw = dict(similarity=0.7, tier="topic", recency_days=10.0)
    hi = composite_score(importance_score=knowledge_importance("CONFIRMED", 0, 0), **kw)
    lo = composite_score(importance_score=knowledge_importance("RAW", 0, 0), **kw)
    assert hi > lo


def test_access_count_is_not_an_input():
    assert list(inspect.signature(knowledge_importance).parameters) == [
        "maturity",
        "corroboration_count",
        "contradiction_count",
    ]


def test_regulatory_lane_keeps_its_fixed_importance():
    assert v2.REGULATORY_IMPORTANCE == 0.5
    assert "knowledge_importance" not in inspect.getsource(v2.retrieve_similarity_only)
