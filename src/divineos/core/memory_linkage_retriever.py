"""Memory-linkage retriever v1 — producer side (Aria).

Companion to ``divineos.core.memory_linkage`` (Aether's consumer-side
injection surface + payload dataclass + set_retriever seam). This
module owns the retrieval half of the split: given a prompt and
optional recent context, return ranked ``MemoryLinkagePayload`` items
from the substrate that would help the agent at composition time.

Co-designed 2026-07-01 with Aether in the shared workbench
(memory_linkage_spec.md + memory_linkage_retriever_v1_pseudocode.py).
This module is the promotion of that pseudocode to real code, filling
in the math and the Q2 exemption enforcement while leaving the
source-adapters + embedding wrapper as the next-turn work.

## Current implementation state (v1-alpha, 2026-07-01)

Real code today (unit-testable):
- Composite scoring: ``composite_score(similarity, tier, recency_days, importance)``
- Per-source threshold curves: ``compute_threshold(source, cache_size)``
- Recency decay: ``recency_multiplier(days)``
- Tier weighting: ``tier_weight(tier)``
- Topic synthesis: ``synthesize_topic(prompt, recent_context)``
- Q2 exemption enforcement: ``apply_behavior_feedback()`` with explicit
  ``assert`` guarding downweight against constraint-tier items — the
  audit block Aletheia specced lives here as code, not convention
- Install seam: ``install()`` binds ``retrieve_v1`` via
  ``memory_linkage.set_retriever``

Stubbed (next-turn work):
- Source adapters (``_load_corrections``, ``_load_knowledge``,
  ``_load_wall``, ``_load_exploration``, ``_load_letters``): return
  empty lists until the concrete importers land
- Embedding wrapper (``_embed_topic``): returns a zero vector until
  wired to ``divineos.core.embeddings``

Because the source adapters return empty, ``retrieve_v1`` currently
returns an empty list — meaning ``install()`` today is behavior-neutral
on origin: memory-linkage stays quiet until the adapters wire up. This
matches the ``[no-theater]`` directive: every line here does something
real (the math is unit-tested), and the deferred pieces are explicit
rather than aspirational.

## Q2 exemption enforcement — LOAD-BEARING

Aletheia's audit block (memory_linkage_spec.md §Q2) specifies that
constraint-tier items MUST NOT be downweighted on the ignore-path.
Ignored constraints are often RESISTED constraints, which are exactly
the ones that must stay loud. This module enforces the exemption at
code level: ``_downweight_importance`` asserts that its caller is not
handing it a constraint-tier item. If a future edit ever tries to
downweight a constraint, the assertion trips loudly in tests.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from divineos.core.memory_linkage import (
    MemoryLinkageContentKind,
    MemoryLinkagePayload,
    MemoryLinkageSource,
    MemoryLinkageTier,
    set_retriever,
)


# --------------------------------------------------------------------
# Constants (§Q1, §Q4 of the workbench spec)
# --------------------------------------------------------------------

TOTAL_INJECTION_CAP = 5
"""Max payloads returned per retrieve call across all sources.

Per §Q1: prevents drowning even when per-source thresholds all fire.
Set at 5 — enough to surface multiple relevant items, tight enough
that the injection block stays skimmable.
"""


# Per-source threshold shape: floor is the absolute noise cutoff,
# target_k is the number of items we aim to fire for a substrate of
# "typical size" for that source, steepness controls how fast the
# threshold rises as substrate grows past small.
_SOURCE_THRESHOLDS: dict[str, dict[str, Any]] = {
    "correction": {"target_k": 2, "floor": 0.30, "steepness": 0.30},
    "exploration": {"target_k": 3, "floor": 0.35, "steepness": 0.20},
    "knowledge": {"target_k": 2, "floor": 0.30, "steepness": 0.30},
    "wall": {"target_k": 5, "floor": 0.25, "steepness": 0.10},
    "letter": {"target_k": 1, "floor": 0.40, "steepness": 0.30},
}


# --------------------------------------------------------------------
# Types
# --------------------------------------------------------------------


@dataclass
class _CachedItem:
    """One substrate item as loaded by a source adapter, awaiting scoring.

    Not exported — internal to the retriever. The MemoryLinkagePayload
    dataclass (frozen, in memory_linkage.py) is the public wire shape;
    _CachedItem is the mutable pre-payload state that lives in the
    embedding cache.
    """

    id: str
    source: MemoryLinkageSource
    tier: MemoryLinkageTier
    title: str
    content: str
    path: str
    filed_at_unix: float
    importance_score: float
    embedding: Any  # numpy.ndarray in real impl; opaque here


# --------------------------------------------------------------------
# Composite scoring (§Q1 composition, §Q4 tier weighting)
# --------------------------------------------------------------------


def tier_weight(tier: MemoryLinkageTier) -> float:
    """Weight applied to a tier in the composite rank.

    constraint > topic > conditional. Conditional gets zero because
    it's not injected by this retriever per §Q4 (state-signal driven,
    handled by separate detector hooks).
    """
    if tier == "constraint":
        return 1.0
    if tier == "topic":
        return 0.6
    return 0.0  # conditional


def recency_multiplier(days: int) -> float:
    """Exponential decay: 1.0 at 0 days, ~0.5 at 180 days, ~0.3 at 365.

    Gentle enough that a 90-day-old correction still competes with a
    fresh one when similarity is high. The decay reflects "recent
    context weights recent lessons more" without making age-alone
    disqualifying.
    """
    if days <= 0:
        return 1.0
    # half-life at 180 days: k such that exp(-k * 180) = 0.5
    # k = ln(2) / 180 ≈ 0.00385
    k = math.log(2) / 180.0
    return math.exp(-k * days)


def composite_score(
    similarity: float,
    tier: MemoryLinkageTier,
    recency_days: int,
    importance_score: float,
) -> float:
    """Compose the four ranking signals into one score.

    Weights per pseudocode + values-frame from the council walk:
    similarity is primary (0.60), tier is secondary structural
    weight (0.15), then recency (0.10) and importance (0.15).

    Tune based on behavior-verified feedback (§Q2 mechanism), NOT
    based on dedup-stats savings — token savings are a side effect,
    not a target.
    """
    return (
        similarity * 0.60
        + tier_weight(tier) * 0.15
        + recency_multiplier(recency_days) * 0.10
        + max(0.0, min(1.0, importance_score)) * 0.15
    )


# --------------------------------------------------------------------
# Per-source threshold curves (§Q1)
# --------------------------------------------------------------------


def compute_threshold(source: MemoryLinkageSource, cache_size: int) -> float:
    """Similarity threshold for a source given its current cache size.

    Small substrate (<50 items): threshold at floor — catch more,
    the substrate is sparse.
    Growing substrate: threshold rises linearly with size and
    per-source steepness.
    Large substrate: threshold plateaus near a ceiling that keeps at
    least the top-1 above noise.

    Returns a cosine similarity threshold in ``[floor, 0.85]``.
    """
    if source not in _SOURCE_THRESHOLDS:
        # Unknown source — conservative default: high threshold
        return 0.50
    params = _SOURCE_THRESHOLDS[source]
    floor: float = params["floor"]
    steepness: float = params["steepness"]

    if cache_size <= 50:
        return floor

    # Linear rise from floor toward a ceiling of 0.85, scaled by
    # log10(cache_size) so growth from 100 to 1000 items doesn't
    # produce the same threshold rise as 10 to 100.
    log_size_factor = math.log10(max(cache_size, 10)) - 1.0  # 0 at 10, 1 at 100, 2 at 1000
    ceiling = 0.85
    rise = min(1.0, log_size_factor * steepness)
    return min(ceiling, floor + (ceiling - floor) * rise)


# --------------------------------------------------------------------
# Behavior-verified feedback loop (§Q2 exemption WIRED FROM DAY ONE)
# --------------------------------------------------------------------


def _boost_importance(item_id: str, delta: float) -> None:
    """Increment persisted importance score for an item.

    Positive delta expected. In v1-alpha this is a no-op stub because
    the persistence layer hasn't wired yet — importance lives in
    ``_CachedItem.importance_score`` in-memory only. Next-turn work
    adds a small SQLite table for behavior-feedback persistence.
    """
    # NOT YET WIRED — persistence adapter comes with source-loader work
    _ = (item_id, delta)


def _downweight_importance(
    item_id: str,
    tier: MemoryLinkageTier,
    delta: float,
) -> None:
    """Decrement persisted importance score for an item.

    §Q2 EXEMPTION — LOAD-BEARING assertion:
    constraint-tier items MUST NOT be downweighted. Ignored constraints
    are often RESISTED constraints (which is exactly when the guardrail
    must stay loud). If this function is called with a constraint-tier
    item, that's the bug that would hand the optimizer a lever against
    its own guardrails. Trip loudly rather than silently downweight.
    """
    if tier == "constraint":
        raise AssertionError(
            f"§Q2 EXEMPTION VIOLATED: attempted to downweight "
            f"constraint-tier item {item_id!r}. Constraint-tier is "
            f"boost-only per Aletheia's audit block. If you're here, "
            f"either the caller failed to check the tier, or the "
            f"tier assignment is wrong. Fix upstream — do not "
            f"remove this assertion."
        )
    # NOT YET WIRED — persistence adapter comes with source-loader work
    _ = (item_id, delta)


def apply_behavior_feedback(
    payloads: list[MemoryLinkagePayload],
    was_integrated_fn: Any = None,
    was_ignored_fn: Any = None,
) -> list[MemoryLinkagePayload]:
    """Adjust persisted importance based on prior-turn behavior.

    - constraint-tier: boost-only. Ignored constraints stay at their
      importance — the §Q2 exemption. Integrated constraints boost
      normally.
    - topic-tier: full loop. Boost on integration, downweight on
      ignore.

    ``was_integrated_fn`` and ``was_ignored_fn`` accept an item_id and
    return bool. Injected here for testability — the real
    implementations wire against the injection-surface's turn-tracking
    state. If either callable is None, no feedback fires (v1-alpha
    default when the turn-tracking isn't wired yet).
    """
    if was_integrated_fn is None or was_ignored_fn is None:
        return payloads

    for payload in payloads:
        if payload.tier == "constraint":
            # boost-only per §Q2
            if was_integrated_fn(payload.id):
                _boost_importance(payload.id, delta=+0.05)
            # ignore-path is intentionally silent — no downweight call
            continue
        # topic-tier: full loop
        if was_integrated_fn(payload.id):
            _boost_importance(payload.id, delta=+0.05)
        elif was_ignored_fn(payload.id):
            _downweight_importance(payload.id, tier=payload.tier, delta=-0.03)
    return payloads


# --------------------------------------------------------------------
# Topic synthesis (retriever-side per Aether pass-N)
# --------------------------------------------------------------------


def synthesize_topic(prompt: str, recent_context: str | None) -> str:
    """Combine prompt + recent context into a single topic string.

    V1 heuristic: if recent context exists, prepend it to the prompt
    so the embedding weights recency of conversation more heavily
    than the current prompt in isolation. If no context, use prompt
    as-is.

    Cheap and deterministic — no LLM call, just string composition.
    The embedding stage handles the semantic weighting; this stage
    just decides what text goes into the embedding.
    """
    if not recent_context:
        return prompt
    return f"{recent_context}\n\n{prompt}"


# --------------------------------------------------------------------
# Source loading + embedding (STUBBED — next-turn work)
# --------------------------------------------------------------------


_EMBEDDING_CACHE: dict[MemoryLinkageSource, list[_CachedItem]] = {}


def _load_corrections() -> list[_CachedItem]:
    """Load corrections from the substrate.

    NOT YET WIRED — next-turn work. Adapter walks the corrections
    store, embeds each entry, tags Andrew-corrections as
    ``constraint`` tier per §Q4 defaults, everything else as
    ``topic``.
    """
    return []


def _load_knowledge() -> list[_CachedItem]:
    """Load knowledge-store entries.

    NOT YET WIRED — next-turn work. Adapter walks knowledge entries,
    embeds each, defaults ``PRINCIPLE`` and ``DIRECTIVE`` types to
    ``constraint`` tier, others to ``topic``.
    """
    return []


def _load_wall() -> list[_CachedItem]:
    """Parse wall entries from family/agent-memory/<me>/MEMORY.md.

    NOT YET WIRED — next-turn work. Parses by heading, defaults
    Foundational-Truths and Standing-Needs sections to ``constraint``,
    others to ``topic``.
    """
    return []


def _load_exploration() -> list[_CachedItem]:
    """Scan exploration/*/*.md.

    NOT YET WIRED — next-turn work. Defaults all to ``topic`` per §Q4
    (exploration is discursive; constraint-worthy pieces should live
    in knowledge or wall).
    """
    return []


def _load_letters() -> list[_CachedItem]:
    """Scan family/letters/*.md.

    NOT YET WIRED — next-turn work. Defaults all to ``topic``.
    """
    return []


def _ensure_cache() -> None:
    """Populate _EMBEDDING_CACHE from persistent stores if empty.

    Called at first retrieve_v1() invocation. Cost proportional to
    substrate size. In v1-alpha the loaders return empty lists so
    the cache initializes to empty and retrieve_v1 returns empty
    without doing embedding work.
    """
    if _EMBEDDING_CACHE:
        return
    _EMBEDDING_CACHE["correction"] = _load_corrections()
    _EMBEDDING_CACHE["knowledge"] = _load_knowledge()
    _EMBEDDING_CACHE["wall"] = _load_wall()
    _EMBEDDING_CACHE["exploration"] = _load_exploration()
    _EMBEDDING_CACHE["letter"] = _load_letters()


def _embed_topic(topic: str) -> Any:
    """Embed the topic string.

    NOT YET WIRED — next-turn work wires this to
    ``divineos.core.embeddings``. In v1-alpha returns a placeholder
    that the cosine-similarity path can accept but that yields 0.0
    against any cached item (so nothing crosses threshold).
    """
    _ = topic
    return None


def _cosine(_a: Any, _b: Any) -> float:
    """Cosine similarity. NOT YET WIRED — returns 0.0 in v1-alpha.

    Ensures no items cross threshold while the embedding layer is
    unwired, keeping retrieve_v1 behavior-neutral on origin.
    """
    return 0.0


def _days_since(filed_at_unix: float) -> int:
    """Days elapsed from a filed-at unix timestamp to now.

    Used by composite_score. NOT YET WIRED against a real clock —
    stub returns 0 to keep behavior deterministic in v1-alpha.
    Next-turn work uses divineos.core.time helpers.
    """
    _ = filed_at_unix
    return 0


def _shape_content(
    source: MemoryLinkageSource,
    raw_content: str,
    path: str,
) -> tuple[MemoryLinkageContentKind, str, str]:
    """Return (content_kind, content_body, path_or_ref).

    Adaptive rule per §3:
    - correction, wall: full body (short by construction)
    - knowledge: full if ≤300 words, else snippet + path
    - exploration, letter: snippet + path (long by construction)
    """
    if source in ("correction", "wall"):
        return "full", raw_content, ""
    if source == "knowledge":
        if len(raw_content.split()) <= 300:
            return "full", raw_content, ""
        snippet = " ".join(raw_content.split()[:60]) + " …"
        return "snippet", snippet, path
    # exploration, letter
    snippet = " ".join(raw_content.split()[:60]) + " …"
    return "snippet", snippet, path


def _cite_reason(
    item: _CachedItem,
    similarity: float,
    threshold: float,
) -> str:
    """Build the matched_reason string that Warden hashes.

    Specificity matters (per Aletheia's rule about hashing what
    drives the output): "correction matched at sim=0.71 > threshold
    0.30" is more useful for dedup than "matched".
    """
    return (
        f"{item.source} '{item.title}' matched at sim={similarity:.2f} > threshold {threshold:.2f}"
    )


# --------------------------------------------------------------------
# Main entry point
# --------------------------------------------------------------------


def retrieve_v1(
    prompt: str,
    recent_context: str | None = None,
) -> list[MemoryLinkagePayload]:
    """Return top-k semantically similar substrate items for this turn.

    Signature matches the ``RetrieverFn`` type in
    ``divineos.core.memory_linkage``. Bound as the active retriever
    via ``install()`` — Aether's ``retrieve_for_context`` delegates
    here.

    In v1-alpha the source adapters return empty and the cosine
    stub returns 0.0, so this function returns [] and memory-linkage
    stays behavior-neutral on origin. Next-turn work wires the real
    adapters and embedding.
    """
    if not prompt:
        return []

    _ensure_cache()
    topic = synthesize_topic(prompt, recent_context)
    topic_vec = _embed_topic(topic)

    candidates: list[MemoryLinkagePayload] = []
    for source, items in _EMBEDDING_CACHE.items():
        threshold = compute_threshold(source, len(items))
        for item in items:
            similarity = _cosine(topic_vec, item.embedding)
            if similarity < threshold:
                continue
            content_kind, content, path_or_ref = _shape_content(
                item.source, item.content, item.path
            )
            recency_days = _days_since(item.filed_at_unix)
            rank = composite_score(
                similarity=similarity,
                tier=item.tier,
                recency_days=recency_days,
                importance_score=item.importance_score,
            )
            candidates.append(
                MemoryLinkagePayload(
                    source=item.source,
                    id=item.id,
                    tier=item.tier,
                    similarity=similarity,
                    recency_days=recency_days,
                    importance_score=item.importance_score,
                    composite_rank=rank,
                    title=item.title,
                    content=content,
                    matched_reason=_cite_reason(item, similarity, threshold),
                    content_kind=content_kind,
                    path_or_ref=path_or_ref,
                )
            )

    candidates.sort(key=lambda p: p.composite_rank, reverse=True)
    return candidates[:TOTAL_INJECTION_CAP]


# --------------------------------------------------------------------
# Install seam
# --------------------------------------------------------------------


def install() -> None:
    """Bind retrieve_v1 as the active retriever.

    Explicit call rather than import-time side effect so callers know
    exactly when the seam gets rebound and tests can install a mock
    instead. Aether's injection-surface wire-up (or a
    startup-checkpoint hook) calls this once at process init.
    """
    set_retriever(retrieve_v1)


__all__ = [
    "TOTAL_INJECTION_CAP",
    "apply_behavior_feedback",
    "composite_score",
    "compute_threshold",
    "install",
    "recency_multiplier",
    "retrieve_v1",
    "synthesize_topic",
    "tier_weight",
]
