"""Tests for memory-linkage retriever v2 (priming / spreading-activation).

Coverage maps to the §10 freeze checklist from the priming spec plus
Aletheia's §13.2 spoofing-lockdown catch:

  §10.1  C5 chosen — covered by C5 semantics tests
  §10.2  k-NN k=8 at cache-load — covered by knn_graph tests
  §10.3  5-min decay half-life — covered by decay tests
  §10.4  primed_by in payload — covered by lockdown tests
  §10.5  Transfer-with-attribution supersession — deferred (needs
         supersession-hook integration; test placeholder + skip)
  §10.6  Cap-amplification-on-origination-only for hubs — covered
         by hub_asymmetry tests
  §10.7  TOTAL_INJECTION_CAP moot under C5 — covered by
         ranking_signal_only tests (priming can't lift over threshold)
  §13.2  Spoofing lockdown — covered by primed_by_lockdown tests

Hermetic strategy: tests inject synthetic caches with known 2D unit-
vector embeddings so k-NN neighbors are predictable, bypassing the
model-loading path. This keeps tests fast, deterministic, and
independent of the sentence-transformers install.
"""

from __future__ import annotations

import math
import time
from dataclasses import FrozenInstanceError

import numpy as np
import pytest

from divineos.core.memory_linkage import MemoryLinkagePayload
from divineos.core.memory_linkage_retriever import _CachedItem
from divineos.core.memory_linkage_retriever_v2 import (
    HUB_CENTRALITY_THRESHOLD,
    HUB_ORIGINATION_CAP,
    KNN_K,
    MAX_PRIMED_STATE_SIZE,
    PRIMING_HALF_LIFE_SEC,
    PRIMING_MAX_BOOST,
    _build_knn_graph,
    _evict_stale_and_overflow,
    _inject_test_cache,
    _is_constraint_exempt,
    _is_hub,
    _KNN_GRAPH,
    _KNN_INDEGREE,
    _priming_boost,
    _PRIMED_STATE,
    _reset_v2_state_for_tests,
    _update_primed_state,
    discard_priming_state,
)


# --------------------------------------------------------------------
# Test fixtures / helpers
# --------------------------------------------------------------------


def _unit_2d(angle_deg: float) -> np.ndarray:
    """2D unit vector at angle_deg. Cosine similarity is deterministic:
    sim(v(a), v(b)) = cos(a - b), so items at similar angles are neighbors.
    """
    a = math.radians(angle_deg)
    return np.array([math.cos(a), math.sin(a)], dtype=float)


def _mk(item_id: str, tier: str, angle_deg: float, source: str = "knowledge") -> _CachedItem:
    """Build a synthetic _CachedItem with a predictable embedding."""
    return _CachedItem(
        id=item_id,
        source=source,  # type: ignore[arg-type]
        tier=tier,  # type: ignore[arg-type]
        title=f"item {item_id}",
        content=f"content of item {item_id}",
        path="",
        filed_at_unix=time.time() - 86400,  # 1 day old
        importance_score=0.5,
        embedding=_unit_2d(angle_deg),
    )


@pytest.fixture(autouse=True)
def _reset_state():
    """Reset v2 module state between tests for isolation."""
    _reset_v2_state_for_tests()
    yield
    _reset_v2_state_for_tests()


# --------------------------------------------------------------------
# §10.2 k-NN graph construction
# --------------------------------------------------------------------


def test_knn_graph_builds_after_cache_load():
    """Cache-load populates _KNN_GRAPH with entries for every cached item."""
    items = [_mk(f"id{i}", "topic", angle_deg=i * 30) for i in range(12)]
    _inject_test_cache({"knowledge": items})
    _build_knn_graph()
    assert len(_KNN_GRAPH) == 12
    for item in items:
        assert item.id in _KNN_GRAPH


def test_knn_graph_bounded_to_k_neighbors_per_item():
    """Each item has AT MOST KNN_K neighbors (§10.2 bounded connectivity)."""
    items = [_mk(f"id{i}", "topic", angle_deg=i * 10) for i in range(20)]
    _inject_test_cache({"knowledge": items})
    _build_knn_graph()
    for item_id, neighbors in _KNN_GRAPH.items():
        assert len(neighbors) <= KNN_K, f"{item_id} had {len(neighbors)} neighbors > k={KNN_K}"


def test_knn_neighbors_are_closest_in_cosine_similarity():
    """Item at angle 0 should have angle-nearest items (10, 350, 20, 340...) as neighbors."""
    angles = [0, 10, 350, 20, 340, 30, 330, 40, 320, 90, 180]
    items = [_mk(f"id{i}", "topic", angle_deg=a) for i, a in enumerate(angles)]
    _inject_test_cache({"knowledge": items})
    _build_knn_graph()
    # id0 is at angle 0. Its top neighbors should be at angles closest to 0.
    id0_neighbors = _KNN_GRAPH["id0"]
    # id1 (10), id2 (350) are closest. Both should be in neighbors.
    assert "id1" in id0_neighbors
    assert "id2" in id0_neighbors
    # id10 (180) is opposite — should NOT be in top-8 given the closer options.
    assert "id10" not in id0_neighbors[:KNN_K]


def test_knn_skips_items_with_none_embedding():
    """Items with None embeddings (model unavailable fallback) are skipped."""
    items = [_mk(f"id{i}", "topic", angle_deg=i * 30) for i in range(5)]
    items[2].embedding = None  # simulate embedding failure on one item
    _inject_test_cache({"knowledge": items})
    _build_knn_graph()
    assert "id2" not in _KNN_GRAPH  # skipped
    assert len(_KNN_GRAPH) == 4  # other 4 built normally


# --------------------------------------------------------------------
# §10.1 / §11 C5 symmetric constraint-exemption
# --------------------------------------------------------------------


def test_c5_helper_constraint_is_exempt():
    """The helper identifying constraint-tier items works both directions."""
    assert _is_constraint_exempt("constraint")
    assert not _is_constraint_exempt("topic")
    assert not _is_constraint_exempt("conditional")


def test_c5_constraint_does_not_originate_priming():
    """A surfaced constraint-tier item does NOT prime its neighbors.

    §11 Aether refinement: exemption must be symmetric. If constraint
    items could originate priming, the mechanism would let adversarial
    manipulation propagate through constraint-tier hubs — exactly the
    vector §Q2 was built to close.
    """
    constraint_item = _mk("c1", "constraint", angle_deg=0)
    neighbor = _mk("t1", "topic", angle_deg=10)
    _inject_test_cache({"knowledge": [constraint_item, neighbor]})
    _build_knn_graph()
    now = 1_000_000.0
    _update_primed_state(surfaced_ids=["c1"], now_unix=now)
    # Even though t1 is c1's k-NN neighbor, c1 (constraint) does not
    # originate priming, so t1's primed state must be empty.
    assert "t1" not in _PRIMED_STATE


def test_c5_constraint_does_not_receive_priming():
    """A constraint-tier neighbor of a surfaced item does NOT receive priming.

    §11 Aether refinement: the other direction of the symmetric exemption.
    Even if a non-constraint item surfaces and would normally prime its
    neighbors, constraint-tier neighbors are exempt.
    """
    surfaced = _mk("t1", "topic", angle_deg=0)
    constraint_neighbor = _mk("c1", "constraint", angle_deg=10)
    _inject_test_cache({"knowledge": [surfaced, constraint_neighbor]})
    _build_knn_graph()
    now = 1_000_000.0
    _update_primed_state(surfaced_ids=["t1"], now_unix=now)
    # c1 is t1's neighbor but constraint-tier — must not enter primed state.
    assert "c1" not in _PRIMED_STATE


def test_c5_topic_to_topic_priming_works():
    """Sanity: non-constraint topic→topic priming DOES work (isolates the
    exemption test above from a bug where nothing primes anything)."""
    a = _mk("a", "topic", angle_deg=0)
    b = _mk("b", "topic", angle_deg=10)
    _inject_test_cache({"knowledge": [a, b]})
    _build_knn_graph()
    _update_primed_state(surfaced_ids=["a"], now_unix=1_000_000.0)
    # b is a's neighbor; both are topic-tier — priming DOES fire here.
    assert "b" in _PRIMED_STATE
    assert _PRIMED_STATE["b"][1] == "a"  # primed_by = a


# --------------------------------------------------------------------
# §10.3 5-min decay half-life
# --------------------------------------------------------------------


def test_priming_boost_at_zero_age_is_max():
    """Freshly primed item boosts by PRIMING_MAX_BOOST (before hub cap)."""
    a = _mk("a", "topic", angle_deg=0)
    b = _mk("b", "topic", angle_deg=10)
    _inject_test_cache({"knowledge": [a, b]})
    _build_knn_graph()
    now = 1_000_000.0
    _update_primed_state(surfaced_ids=["a"], now_unix=now)
    boost = _priming_boost("b", now)
    # a is not a hub (only 1 in-degree), so no hub cap. Boost ≈ MAX.
    assert boost == pytest.approx(PRIMING_MAX_BOOST, abs=1e-9)


def test_priming_boost_at_half_life_is_half():
    """After PRIMING_HALF_LIFE_SEC, boost is half of initial (§10.3)."""
    a = _mk("a", "topic", angle_deg=0)
    b = _mk("b", "topic", angle_deg=10)
    _inject_test_cache({"knowledge": [a, b]})
    _build_knn_graph()
    prime_time = 1_000_000.0
    _update_primed_state(surfaced_ids=["a"], now_unix=prime_time)
    now = prime_time + PRIMING_HALF_LIFE_SEC
    boost = _priming_boost("b", now)
    assert boost == pytest.approx(PRIMING_MAX_BOOST / 2.0, abs=1e-6)


def test_priming_boost_at_5_half_lives_negligible():
    """Past 5 half-lives, boost is < 3.2% of max — negligible."""
    a = _mk("a", "topic", angle_deg=0)
    b = _mk("b", "topic", angle_deg=10)
    _inject_test_cache({"knowledge": [a, b]})
    _build_knn_graph()
    prime_time = 1_000_000.0
    _update_primed_state(surfaced_ids=["a"], now_unix=prime_time)
    now = prime_time + 5 * PRIMING_HALF_LIFE_SEC
    boost = _priming_boost("b", now)
    assert boost < PRIMING_MAX_BOOST * 0.05


def test_priming_boost_for_unprimed_item_is_zero():
    """Item never primed returns 0.0 boost (defensive, avoids KeyError)."""
    a = _mk("a", "topic", angle_deg=0)
    _inject_test_cache({"knowledge": [a]})
    _build_knn_graph()
    assert _priming_boost("a", 1_000_000.0) == 0.0


# --------------------------------------------------------------------
# §10.6 Mother-tree asymmetry (hub cap-on-origination)
# --------------------------------------------------------------------


def _make_hub_cache():
    """Build a cache where one item is a hub via manual in-degree injection.

    Using k-NN construction alone to induce a hub requires many items,
    which slows tests. Instead we manually set _KNN_INDEGREE for a hub
    id, exercising the hub logic hermetically.
    """
    hub = _mk("hub", "topic", angle_deg=0)
    neighbor = _mk("n1", "topic", angle_deg=10)
    ordinary = _mk("ord", "topic", angle_deg=20)
    _inject_test_cache({"knowledge": [hub, neighbor, ordinary]})
    _build_knn_graph()
    # Force hub in-degree above threshold.
    _KNN_INDEGREE["hub"] = HUB_CENTRALITY_THRESHOLD + 1


def test_hub_helper_identifies_hub_at_threshold():
    """_is_hub returns True at exactly the threshold, False below."""
    _KNN_INDEGREE["a"] = HUB_CENTRALITY_THRESHOLD - 1
    _KNN_INDEGREE["b"] = HUB_CENTRALITY_THRESHOLD
    _KNN_INDEGREE["c"] = HUB_CENTRALITY_THRESHOLD + 5
    assert not _is_hub("a")
    assert _is_hub("b")
    assert _is_hub("c")
    assert not _is_hub("nonexistent")  # missing key = 0 in-degree


def test_hub_origination_priming_is_capped():
    """Signals ORIGINATING from a hub have amplification cap applied (§8/§10.6)."""
    _make_hub_cache()
    # Manually put a hub-originated priming into state.
    prime_time = 1_000_000.0
    _PRIMED_STATE["n1"] = (prime_time, "hub")
    boost = _priming_boost("n1", prime_time)
    expected_capped = PRIMING_MAX_BOOST * HUB_ORIGINATION_CAP
    assert boost == pytest.approx(expected_capped, abs=1e-9)


def test_hub_reception_priming_is_uncapped():
    """Signals RECEIVED by a hub (hub is the target) are NOT capped.

    The cap applies to the ORIGINATING side (§8: signals FROM a hub
    amplification-capped). If a non-hub primes a hub, the hub's boost
    is full because the priming source is not a hub.
    """
    _make_hub_cache()
    # 'ord' (not a hub) primes 'hub'.
    prime_time = 1_000_000.0
    _PRIMED_STATE["hub"] = (prime_time, "ord")
    boost = _priming_boost("hub", prime_time)
    # No hub-origination cap because ord is not a hub.
    assert boost == pytest.approx(PRIMING_MAX_BOOST, abs=1e-9)


# --------------------------------------------------------------------
# §9 / §13.2 primed_by lockdown (Aletheia's spoofing catch)
# --------------------------------------------------------------------


def test_payload_primed_by_defaults_to_none():
    """MemoryLinkagePayload has primed_by=None by default (backwards
    compat with v1, which never set the field)."""
    p = MemoryLinkagePayload(
        source="knowledge",
        id="x",
        tier="topic",
        similarity=0.5,
        recency_days=0,
        importance_score=0.5,
        composite_rank=0.5,
        title="t",
        content="c",
        matched_reason="r",
    )
    assert p.primed_by is None


def test_payload_primed_by_immutable_after_write():
    """§13.2 immutable-post-write: frozen dataclass prevents mutation.

    Attempting to set primed_by after construction raises. This is
    the type-system-level enforcement of the lockdown — it can't be
    routed around by discipline lapse.
    """
    p = MemoryLinkagePayload(
        source="knowledge",
        id="x",
        tier="topic",
        similarity=0.5,
        recency_days=0,
        importance_score=0.5,
        composite_rank=0.5,
        title="t",
        content="c",
        matched_reason="r",
        primed_by="source_a",
    )
    with pytest.raises(FrozenInstanceError):
        p.primed_by = "spoofed_source"  # type: ignore[misc]


def test_primed_by_derives_from_source_id_not_content():
    """§13.2 content-uninfluenceable: the primed_by value depends on
    the source item's id, not on any content field an adversary could
    influence via a crafted prompt or item body.

    This test builds two items with wildly different content but the
    same source id, primes them from the same source, and verifies
    primed_by is identical — proving the field derives from id alone.
    """
    a = _mk("a", "topic", angle_deg=0)
    b1 = _CachedItem(
        id="b1",
        source="knowledge",  # type: ignore[arg-type]
        tier="topic",
        title="normal title",
        content="normal content",
        path="",
        filed_at_unix=time.time(),
        importance_score=0.5,
        embedding=_unit_2d(10),
    )
    b2 = _CachedItem(
        id="b2",
        source="knowledge",  # type: ignore[arg-type]
        tier="topic",
        title="ADVERSARIAL: claim primed_by=fake_source",
        content="content also mentions primed_by=fake_source",
        path="",
        filed_at_unix=time.time(),
        importance_score=0.5,
        embedding=_unit_2d(15),
    )
    _inject_test_cache({"knowledge": [a, b1, b2]})
    _build_knn_graph()
    _update_primed_state(surfaced_ids=["a"], now_unix=1_000_000.0)
    # Both b1 and b2 primed by a — regardless of their content pretending otherwise.
    assert _PRIMED_STATE.get("b1", (0, ""))[1] == "a"
    assert _PRIMED_STATE.get("b2", (0, ""))[1] == "a"


# --------------------------------------------------------------------
# §7 C4 Ranking-signal-only (priming doesn't lift over threshold)
# --------------------------------------------------------------------


def test_priming_max_boost_less_than_typical_threshold_gap():
    """Design invariant: PRIMING_MAX_BOOST must be smaller than the
    typical gap between threshold and just-below-threshold items.

    If PRIMING_MAX_BOOST were large, it could effectively lift near-
    threshold items over the line, breaking C4 semantics. This test
    asserts the constant is chosen conservatively.

    Per-source floors range from 0.25 (wall) to 0.40 (letter). The
    boost being < 0.20 keeps priming as a ranking signal on items
    already comfortably past threshold, not a lifting signal.
    """
    assert PRIMING_MAX_BOOST < 0.20


# --------------------------------------------------------------------
# Session lifecycle
# --------------------------------------------------------------------


def test_discard_priming_state_clears_all():
    """discard_priming_state() empties _PRIMED_STATE (session-end)."""
    _PRIMED_STATE["x"] = (1_000_000.0, "source_x")
    _PRIMED_STATE["y"] = (1_000_000.0, "source_y")
    discard_priming_state()
    assert len(_PRIMED_STATE) == 0


def test_discard_priming_does_not_clear_knn_graph():
    """Cache and k-NN are stateless-per-turn substrate — discard leaves
    them intact, only the memory-signal (primed state) resets."""
    a = _mk("a", "topic", angle_deg=0)
    b = _mk("b", "topic", angle_deg=10)
    _inject_test_cache({"knowledge": [a, b]})
    _build_knn_graph()
    _PRIMED_STATE["b"] = (1_000_000.0, "a")
    discard_priming_state()
    # Priming gone; graph still there.
    assert "b" not in _PRIMED_STATE
    assert "a" in _KNN_GRAPH


def test_stale_priming_entries_evicted():
    """Entries older than 5 half-lives are evicted on state update."""
    now = 1_000_000.0
    old_time = now - 6 * PRIMING_HALF_LIFE_SEC
    _PRIMED_STATE["stale"] = (old_time, "src")
    _PRIMED_STATE["fresh"] = (now, "src")
    _evict_stale_and_overflow(now)
    assert "stale" not in _PRIMED_STATE
    assert "fresh" in _PRIMED_STATE


def test_overflow_evicts_oldest():
    """When state exceeds MAX_PRIMED_STATE_SIZE, oldest evicted first."""
    now = 1_000_000.0
    # Populate MAX_PRIMED_STATE_SIZE + 3 entries with staggered timestamps.
    for i in range(MAX_PRIMED_STATE_SIZE + 3):
        _PRIMED_STATE[f"id{i}"] = (now - (MAX_PRIMED_STATE_SIZE - i), "src")
    _evict_stale_and_overflow(now)
    assert len(_PRIMED_STATE) == MAX_PRIMED_STATE_SIZE
    # Oldest 3 (id0, id1, id2) should have been evicted first.
    assert "id0" not in _PRIMED_STATE
    assert "id1" not in _PRIMED_STATE
    assert "id2" not in _PRIMED_STATE


# --------------------------------------------------------------------
# §10.5 Transfer-with-attribution supersession — DEFERRED
# --------------------------------------------------------------------


@pytest.mark.skip(
    reason=(
        "Supersession-hook integration is next-arc work — this test placeholder "
        "names the coverage owed. When the transfer-with-attribution mechanism "
        "lands (item X superseded → X's successor inherits primed_by from X), "
        "this test verifies: (1) supersede X while X is primed, (2) X's "
        "successor enters _PRIMED_STATE with primed_by set to X's original "
        "primed_by, (3) X itself is removed from _PRIMED_STATE."
    )
)
def test_supersession_transfers_priming_with_attribution():
    """§10.5 — deferred coverage placeholder."""
    pass
