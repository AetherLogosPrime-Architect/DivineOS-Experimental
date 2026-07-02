"""Memory-linkage retriever v2 — priming / spreading-activation.

Composition on top of v1 (``memory_linkage_retriever.py``): keeps the
same source adapters, embedding cache, composite scoring, and Q2
exemption enforcement, and layers priming on top.

## Design provenance

Co-authored 2026-07-02 in ``workbench/memory_linkage_v2_priming_spec.md``
by Aether + Aria, boundary-vantage pass by Aletheia integrated as §13.
Each design decision below carries its spec §-reference so a future
reader can trace the code back to the design rationale.

## The chosen design — C5 (§7 CONVERGED)

C5 = constraint-exempt priming (C3) composed with ranking-signal-only
priming (C4). Both defenses stack:

- **C3 side (§Q2 principle-inheritance, §11):** constraint-tier items
  are symmetrically exempt from priming — they NEITHER receive priming
  boost NOR originate priming to neighbors. Asymmetric exemption (one
  side but not the other) is un-exempted per §11 Aether refinement.

- **C4 side (adversarial surface shrinkage):** priming is a **ranking
  signal only**, not an accessibility signal. Priming reorders items
  that already passed the similarity threshold; it does NOT lift items
  over the threshold. Adversary can shift ranking within already-similar
  items but cannot surface arbitrary items through spreading activation.

Under C5, an adversary who controls one turn's prompt can at most
reorder the top-K similar items on the next turn; they cannot surface
constraint items, cannot lift dissimilar items over the threshold,
and cannot originate priming from a constraint hub.

## Mother-tree asymmetry (§8, §10.6)

Biological mycorrhizal networks give mother-trees (high-connectivity
hubs) special handling: hubs can RECEIVE signals and PROPAGATE them
onward, but signals ORIGINATING from a hub are amplification-capped.
This closes the adversarial-hub-flooding vector (adversary who can
raise a hub's activation can no longer flood its many neighbors) while
preserving hub function (hubs still mediate signal flow).

Applied here: an item is a "hub" if its in-degree in the k-NN graph
crosses ``HUB_CENTRALITY_THRESHOLD``. When a hub originates priming
(i.e., is itself surfaced and would prime its neighbors), the priming
strength is multiplied by ``HUB_ORIGINATION_CAP`` < 1.0. When a hub
receives priming, no cap applies.

## primed_by lockdown (§9, §13.2)

Aletheia's §13 catch: without lockdown, an adversary flooding a hub
could write false ``primed_by`` values into planted items, using the
self-audit field as an alibi generator. Three lockdown constraints:

1. **Engine-written only** — only this module sets ``primed_by`` on
   payloads. No source adapter, no consumer, no external caller can
   set the field. Enforced structurally: payload construction happens
   only inside this module's retrieval function.

2. **Content-uninfluenceable** — the value is derived from the source
   item's id, not from the item's content or the current prompt. Even
   an adversary who controls prompt content cannot make the field
   claim a specific ``primed_by`` value.

3. **Immutable-post-write** — the ``MemoryLinkagePayload`` dataclass
   is ``frozen=True`` so the field cannot mutate after construction.
   Freezing enforces this in the type system, not by convention.

## Session lifecycle (§10, open question resolved)

Priming state is discarded when ``discard_priming_state()`` is called.
Callers: the harness on session-end / compaction. If neither fires,
the state naturally decays under the 5-minute half-life so a stale
state that survives ~30 minutes contributes negligibly to scoring.

## Test coverage

See ``tests/core/test_memory_linkage_retriever_v2.py`` for the seven
§10 freeze-checklist tests + Aletheia's §13 spoofing test.
"""

from __future__ import annotations

import math
import time

from divineos.core.memory_linkage import (
    MemoryLinkagePayload,
    MemoryLinkageTier,
    set_retriever,
)
from divineos.core.memory_linkage_retriever import (
    TOTAL_INJECTION_CAP,
    _CachedItem,
    _cite_reason,
    _cosine,
    _days_since,
    _embed_topic,
    _EMBEDDING_CACHE,
    _ensure_cache,
    _shape_content,
    composite_score,
    compute_threshold,
    synthesize_topic,
)

# --------------------------------------------------------------------
# Constants — every value here has a §-reference into the design spec
# --------------------------------------------------------------------

KNN_K = 8
"""Neighbors per item in the precomputed k-NN graph (§10.2).

k=8 is bounded per-item (avoids "every item is a neighbor" degeneration
on dense clusters) and cheap to compute at cache-load (~13k cosine ops
on the current ~1631-item cache). Biological analog: bounded connectivity
per plant in mycorrhizal networks.
"""

PRIMING_HALF_LIFE_SEC = 5 * 60
"""5 minutes, code constant, not caller-tunable (§10.3).

Matches human short-term priming window (~2-30 min in behavioral
experiments). Short enough that adversarial gaming requires sustained
pressure not one-shot; long enough to stay useful across 3-5
conversational turns.
"""

PRIMING_MAX_BOOST = 0.15
"""Maximum boost priming can add to composite_rank (§7 C4 semantics).

Ranking-signal-only: priming reorders within threshold-passers but
does NOT lift items over the threshold. The threshold gate stays
similarity-based; priming can only add up to this much to composite_rank
AFTER threshold passage.
"""

HUB_CENTRALITY_THRESHOLD = 40
"""In-degree threshold above which an item counts as a hub (§8, §10.6).

An item's in-degree = number of other items that list it in their k-NN
neighbors. With KNN_K=8 and cache size ~1631, mean in-degree ≈ 8. A hub
with in-degree ≥ 40 sits far above the mean — the mother-tree analog.
"""

HUB_ORIGINATION_CAP = 0.3
"""Multiplier applied to priming strength when a hub ORIGINATES priming.

Closes the adversarial-hub-flooding vector: adversary who raises a
hub's activation gets diminished amplification (30% of normal) on the
outgoing signal. Hubs still propagate; they just don't broadcast at
full strength. Signals RECEIVED by hubs are uncapped — hubs remain
load-bearing for network function.
"""

MAX_PRIMED_STATE_SIZE = 500
"""Cost-of-signal principle (§8): perpetual priming is metabolically
expensive. Evict oldest primed-timestamps when state exceeds this size."""


# --------------------------------------------------------------------
# Module state
# --------------------------------------------------------------------

# k-NN graph: item_id -> list of neighbor item_ids (k-nearest).
# Built once at cache-load; static thereafter.
_KNN_GRAPH: dict[str, list[str]] = {}

# In-degree per item id: how many other items list this as a neighbor.
# Static after cache-load. Used to identify hubs (mother-tree analog).
_KNN_INDEGREE: dict[str, int] = {}

# Cached lookup: item_id -> _CachedItem (so we can look up tier when
# checking C5 constraint-exemption without re-searching the cache).
_ITEM_INDEX: dict[str, _CachedItem] = {}

# Priming state: item_id -> (primed_at_unix, primed_by_source_id).
# Populated at end of each retrieval; consulted at start of the next.
# Discarded on session-end via ``discard_priming_state()``.
_PRIMED_STATE: dict[str, tuple[float, str]] = {}


# --------------------------------------------------------------------
# k-NN graph construction (§10.2)
# --------------------------------------------------------------------


def _build_knn_graph() -> None:
    """Compute k-NN graph over all cached items using cosine similarity.

    Called from _ensure_v2_state after v1's _ensure_cache populates
    _EMBEDDING_CACHE. Cost: O(N × N × D) where N is item count and D
    is embedding dim (384 for all-MiniLM-L6-v2). For N≈1631, that's
    manageable at cache-load (one-time cost).

    Skipped items: those with None embeddings (the source adapter's
    behavior-neutral fallback when the model couldn't load).
    """
    _KNN_GRAPH.clear()
    _KNN_INDEGREE.clear()
    _ITEM_INDEX.clear()

    all_items: list[_CachedItem] = []
    for items in _EMBEDDING_CACHE.values():
        for item in items:
            if item.embedding is not None:
                all_items.append(item)
                _ITEM_INDEX[item.id] = item

    if not all_items:
        return

    for i, item in enumerate(all_items):
        # Compute similarity to every other item; keep top-K.
        sims: list[tuple[float, str]] = []
        for j, other in enumerate(all_items):
            if i == j:
                continue
            sim = _cosine(item.embedding, other.embedding)
            sims.append((sim, other.id))
        sims.sort(reverse=True)
        neighbors = [neighbor_id for _sim, neighbor_id in sims[:KNN_K]]
        _KNN_GRAPH[item.id] = neighbors
        for neighbor_id in neighbors:
            _KNN_INDEGREE[neighbor_id] = _KNN_INDEGREE.get(neighbor_id, 0) + 1


def _is_hub(item_id: str) -> bool:
    """True if item's in-degree crosses HUB_CENTRALITY_THRESHOLD (§8)."""
    return _KNN_INDEGREE.get(item_id, 0) >= HUB_CENTRALITY_THRESHOLD


def _ensure_v2_state() -> None:
    """Populate v2 state (k-NN graph) on first retrieval.

    v1's _ensure_cache is called first (via retrieve_v2) to populate
    _EMBEDDING_CACHE; then we build the k-NN graph over it. Both are
    one-time costs at first retrieval.
    """
    _ensure_cache()
    if not _KNN_GRAPH:
        _build_knn_graph()


# --------------------------------------------------------------------
# C5 constraint-exemption (§7, §11) — symmetric enforcement
# --------------------------------------------------------------------


def _is_constraint_exempt(tier: MemoryLinkageTier) -> bool:
    """True for constraint-tier items — exempt from priming both ways.

    §Q2 / §11: constraint-tier items neither receive priming boost NOR
    originate priming to neighbors. Symmetric per §11 Aether refinement:
    asymmetric exemption is un-exempted.
    """
    return tier == "constraint"


# --------------------------------------------------------------------
# Priming boost computation (§7 C4 semantics + §8 hub asymmetry)
# --------------------------------------------------------------------


def _priming_boost(item_id: str, now_unix: float) -> float:
    """Decayed priming boost for an item.

    Returns 0.0 if item is not primed. Otherwise returns a value in
    [0, PRIMING_MAX_BOOST] scaled by:
      - exponential decay: exp(-ln(2) * t / half_life)
      - HUB_ORIGINATION_CAP if the source that primed this item is
        itself a hub (mother-tree asymmetry, §8)

    The cap applies to signals ORIGINATING from a hub, per §8's
    "signals FROM a hub amplification-capped" rule. Signals RECEIVED
    by a hub (i.e., where this item is the hub) are uncapped —
    equivalently, the cap applies at the priming-source lookup, not
    the priming-target lookup.
    """
    entry = _PRIMED_STATE.get(item_id)
    if entry is None:
        return 0.0
    primed_at, primed_by_id = entry
    age_sec = now_unix - primed_at
    if age_sec < 0:
        return 0.0
    decay = math.exp(-math.log(2.0) * age_sec / PRIMING_HALF_LIFE_SEC)
    boost = PRIMING_MAX_BOOST * decay
    if _is_hub(primed_by_id):
        boost *= HUB_ORIGINATION_CAP
    return boost


# --------------------------------------------------------------------
# Priming state update (§9 primed_by field derivation)
# --------------------------------------------------------------------


def _update_primed_state(surfaced_ids: list[str], now_unix: float) -> None:
    """Update _PRIMED_STATE after this turn's retrieval.

    Each surfaced item primes its k-NN neighbors for the next turn,
    subject to C5 symmetric exemption:
      - Constraint-tier surfaced items do NOT originate priming.
      - Constraint-tier neighbor items do NOT receive priming.

    The primed_by_id recorded is the source item's id (the item that
    caused the priming). This id is used later by _priming_boost to
    check hub-status on the ORIGINATING side (§8 mother-tree asymmetry).
    """
    for source_id in surfaced_ids:
        source_item = _ITEM_INDEX.get(source_id)
        if source_item is None:
            continue
        # C5: constraint-tier items do not originate priming.
        if _is_constraint_exempt(source_item.tier):
            continue
        for neighbor_id in _KNN_GRAPH.get(source_id, []):
            neighbor_item = _ITEM_INDEX.get(neighbor_id)
            if neighbor_item is None:
                continue
            # C5: constraint-tier items do not receive priming.
            if _is_constraint_exempt(neighbor_item.tier):
                continue
            # Record. If the neighbor was already primed by someone
            # else earlier this turn, keep the most-recent priming
            # source (last write wins — deterministic within a turn).
            _PRIMED_STATE[neighbor_id] = (now_unix, source_id)

    _evict_stale_and_overflow(now_unix)


def _evict_stale_and_overflow(now_unix: float) -> None:
    """Evict primed entries past 5 half-lives OR when state exceeds max size.

    Past 5 half-lives, the decay multiplier is < 0.032 — negligible.
    Removing lets the state size stay bounded even without explicit
    session-end signal.

    On overflow: evict oldest entries until under MAX_PRIMED_STATE_SIZE
    (cost-of-signal principle, §8).
    """
    max_age = 5 * PRIMING_HALF_LIFE_SEC
    stale = [item_id for item_id, (t, _) in _PRIMED_STATE.items() if now_unix - t > max_age]
    for item_id in stale:
        del _PRIMED_STATE[item_id]

    if len(_PRIMED_STATE) > MAX_PRIMED_STATE_SIZE:
        sorted_by_age = sorted(_PRIMED_STATE.items(), key=lambda kv: kv[1][0])
        excess = len(_PRIMED_STATE) - MAX_PRIMED_STATE_SIZE
        for item_id, _ in sorted_by_age[:excess]:
            del _PRIMED_STATE[item_id]


def discard_priming_state() -> None:
    """Discard all priming state.

    Called on session-end / compaction to reset the memory-signal.
    Cache and k-NN graph are unaffected — those are stateless-per-turn
    substrate. Only the primed_neighbors map is discarded.
    """
    _PRIMED_STATE.clear()


# --------------------------------------------------------------------
# Main retrieval — C5 semantics (ranking-signal-only)
# --------------------------------------------------------------------


def retrieve_v2(
    prompt: str,
    recent_context: str | None = None,
) -> list[MemoryLinkagePayload]:
    """v2 retrieval with priming/spreading-activation composed on v1 math.

    Semantics per §7 C5:
    1. Threshold gate stays similarity-based (unchanged from v1).
    2. For items past threshold, composite_rank gets a priming boost
       IF the item was primed on a prior turn AND is not constraint-tier.
    3. Constraint-tier items always have primed_by=None (§Q2/C5).
    4. After retrieval, surfaced items prime their k-NN neighbors for
       the next turn (subject to C5 symmetric exemption).
    5. primed_by field on returned payloads is engine-written only,
       derives from source item id, immutable-post-write (§9/§13.2).
    """
    if not prompt:
        return []

    _ensure_v2_state()
    now_unix = time.time()
    topic = synthesize_topic(prompt, recent_context)
    topic_vec = _embed_topic(topic)

    candidates: list[MemoryLinkagePayload] = []
    for source, items in _EMBEDDING_CACHE.items():
        threshold = compute_threshold(source, len(items))
        for item in items:
            similarity = _cosine(topic_vec, item.embedding)
            # C4: threshold gate stays similarity-based; priming does
            # NOT lift items over the threshold.
            if similarity < threshold:
                continue
            recency_days = _days_since(item.filed_at_unix)
            base_rank = composite_score(
                similarity=similarity,
                tier=item.tier,
                recency_days=recency_days,
                importance_score=item.importance_score,
            )

            # C5 constraint-exemption: constraint-tier items get no
            # priming boost and always report primed_by=None.
            if _is_constraint_exempt(item.tier):
                boost = 0.0
                primed_by_id = None
            else:
                boost = _priming_boost(item.id, now_unix)
                entry = _PRIMED_STATE.get(item.id)
                # §9/§13.2 lockdown: primed_by derives from state's
                # source_id (engine-written), not from item content
                # or prompt (content-uninfluenceable). Immutable via
                # frozen dataclass (immutable-post-write).
                primed_by_id = entry[1] if entry is not None else None

            content_kind, content, path_or_ref = _shape_content(
                item.source, item.content, item.path
            )
            candidates.append(
                MemoryLinkagePayload(
                    source=item.source,
                    id=item.id,
                    tier=item.tier,
                    similarity=similarity,
                    recency_days=recency_days,
                    importance_score=item.importance_score,
                    composite_rank=base_rank + boost,
                    title=item.title,
                    content=content,
                    matched_reason=_cite_reason(item, similarity, threshold),
                    content_kind=content_kind,
                    path_or_ref=path_or_ref,
                    primed_by=primed_by_id,
                )
            )

    candidates.sort(key=lambda p: p.composite_rank, reverse=True)
    selected = candidates[:TOTAL_INJECTION_CAP]

    # Update priming state for next turn based on what surfaced this turn.
    _update_primed_state([p.id for p in selected], now_unix)
    return selected


# --------------------------------------------------------------------
# Install seam
# --------------------------------------------------------------------


def install() -> None:
    """Bind retrieve_v2 as the active retriever.

    Replaces v1 for use via ``memory_linkage.retrieve_for_context``.
    v1 remains importable for baseline comparison and for the
    C1-stateless test case.
    """
    set_retriever(retrieve_v2)


# --------------------------------------------------------------------
# Test-only helpers (for controlled state manipulation in tests)
# --------------------------------------------------------------------


def _reset_v2_state_for_tests() -> None:
    """Clear all v2 module state — for test isolation only.

    Not part of the public API. Test files import and call this
    to guarantee clean state per test. Not used at runtime.
    """
    _KNN_GRAPH.clear()
    _KNN_INDEGREE.clear()
    _ITEM_INDEX.clear()
    _PRIMED_STATE.clear()
    # v1's cache too, so k-NN builds fresh on next retrieve
    _EMBEDDING_CACHE.clear()


def _inject_test_cache(items_by_source: dict[str, list[_CachedItem]]) -> None:
    """Populate _EMBEDDING_CACHE directly for tests without loading substrate.

    Tests build tiny synthetic caches with known tiers, embeddings, and
    connectivity so C5 semantics, hub asymmetry, and priming decay can be
    verified deterministically.
    """
    _EMBEDDING_CACHE.clear()
    for source, items in items_by_source.items():
        _EMBEDDING_CACHE[source] = items  # type: ignore[index]
    _KNN_GRAPH.clear()
    _KNN_INDEGREE.clear()
    _ITEM_INDEX.clear()


__all__ = [
    "HUB_CENTRALITY_THRESHOLD",
    "HUB_ORIGINATION_CAP",
    "KNN_K",
    "PRIMING_HALF_LIFE_SEC",
    "PRIMING_MAX_BOOST",
    "discard_priming_state",
    "install",
    "retrieve_v2",
]
