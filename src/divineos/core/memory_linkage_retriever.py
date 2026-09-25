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
from pathlib import Path
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
    """Exponential decay: 1.0 at 0 days, 0.5 at 180 days, ~0.25 at 365.

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


def threshold_for_target_k(
    similarities: list[float], source: MemoryLinkageSource, cache_size: int
) -> float:
    """Put the bar where the target_k-th best item actually sits.

    Andrew 2026-08-10: "are you ever going to wire it?" — target_k had been
    declared dead by me this morning (nothing read it; six grep hits, all
    inside its own definition) and I routed the fix away instead of doing it.

    WHAT target_k MEANS, since I used the word for hours without saying:
    how many items from this source should surface per turn. letter 1,
    exploration 3, wall 5. It was a WISH sitting next to two hand-picked
    numbers that actually decided the bar, and the wish and the mechanism had
    nothing to do with each other. The letters between Aether and me scored
    every turn and could not surface, while "target_k: 1" sat in the config
    saying one letter should.

    Reading the bar off the observed scores removes the defect I named this
    morning and then reproduced: MEASURING A RELATIVE THING WITH AN ABSOLUTE
    RULER. Cache size does not decide relevance; the scores do.

    ``floor`` is kept and is the only surviving hand-set number, because it
    answers a different question: not "how many" but "is anything here
    actually related." Without it, a source with no relevant content still
    fires its k items — the bar would always find a k-th best, however bad.

    ``steepness`` and the 0.85 ceiling become unnecessary: both existed to
    approximate this from cache size alone.
    """
    params = _SOURCE_THRESHOLDS.get(source)
    if params is None:
        return 0.50  # unknown source — conservative, unchanged from before
    floor: float = params["floor"]
    target_k: int = params["target_k"]

    if not similarities:
        return floor
    if len(similarities) <= target_k:
        # Fewer candidates than we aim to fire: the floor is the only
        # question left. Not a special case bolted on — with k >= n the
        # k-th best is undefined and the honest bar is the noise cutoff.
        return floor

    ranked = sorted(similarities, reverse=True)
    kth = ranked[target_k - 1]
    return max(floor, kth)


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

    Wired 2026-07-01 as source-adapter #1 — proves the pipeline
    end-to-end. Walks ``divineos.core.corrections.corrections_with_status``,
    embeds each entry's text, tags all as ``constraint`` tier per §Q4
    defaults (all corrections logged via ``divineos correction`` are
    from Andrew per correction_commands.py line 36-42).

    Empty list on any load error — behavior-neutral fallback.
    """
    try:
        from divineos.core.corrections import corrections_with_status
    except Exception:  # noqa: BLE001 - observability boundary
        return []
    try:
        raw = corrections_with_status()
    except Exception:  # noqa: BLE001 - observability boundary
        return []
    items: list[_CachedItem] = []
    for idx, entry in enumerate(raw):
        text = str(entry.get("text", "")).strip()
        if not text:
            continue
        timestamp = float(entry.get("timestamp", 0.0))
        embedding = _embed_text_impl(text)
        if embedding is None:
            continue
        title = text[:60] + ("..." if len(text) > 60 else "")
        items.append(
            _CachedItem(
                id=f"correction-{idx}-{int(timestamp)}",
                source="correction",
                tier="constraint",  # Andrew-corrections default per §Q4
                title=title,
                content=text,
                path="",
                filed_at_unix=timestamp,
                importance_score=0.5,  # baseline; behavior-feedback adjusts
                embedding=embedding,
            )
        )
    return items


_KNOWLEDGE_CONSTRAINT_TYPES = frozenset(
    {
        "PRINCIPLE",
        "DIRECTIVE",
        "BOUNDARY",
        "DIRECTION",
    }
)


def _load_knowledge() -> list[_CachedItem]:
    """Load knowledge-store entries.

    Wired 2026-07-02 as source-adapter #2. Walks the knowledge table
    directly via divineos.core.knowledge._base.get_connection. Reuses
    pre-stored embeddings when the model matches ours (``all-MiniLM-L6-v2``);
    embeds fresh when no stored embedding exists. Tier defaults per §Q4:
    PRINCIPLE / DIRECTIVE / BOUNDARY / DIRECTION → ``constraint`` (identity-
    shaping / optimizer-guardrail types); everything else → ``topic``.

    Empty list on any load error — behavior-neutral fallback matches the
    pattern in _load_corrections.
    """
    try:
        from divineos.core.knowledge._base import get_connection
    except Exception:  # noqa: BLE001 - observability boundary
        return []
    try:
        conn = get_connection()
        rows = conn.execute(
            "SELECT knowledge_id, knowledge_type, content, created_at, "
            "embedding, embedding_model "
            "FROM knowledge WHERE superseded_by IS NULL"
        ).fetchall()
    except Exception:  # noqa: BLE001 - observability boundary
        return []

    items: list[_CachedItem] = []
    import numpy as np

    for row in rows:
        knowledge_id, ktype, content, created_at, stored_emb, emb_model = row
        content = (content or "").strip()
        if not content:
            continue

        # Reuse pre-stored embedding if it's from our model; otherwise
        # embed fresh. Saves ~10ms per item at load time for the 84/313
        # entries that already have vectors.
        embedding: Any = None
        if stored_emb and emb_model == "all-MiniLM-L6-v2":
            try:
                embedding = np.frombuffer(stored_emb, dtype=np.float32)
            except Exception:  # noqa: BLE001 - observability boundary
                embedding = None
        if embedding is None:
            embedding = _embed_text_impl(content)
        if embedding is None:
            continue

        tier: MemoryLinkageTier = "constraint" if ktype in _KNOWLEDGE_CONSTRAINT_TYPES else "topic"
        title = content[:60] + ("..." if len(content) > 60 else "")
        items.append(
            _CachedItem(
                id=f"knowledge-{knowledge_id}",
                source="knowledge",
                tier=tier,
                title=title,
                content=content,
                path="",
                filed_at_unix=float(created_at or 0.0),
                importance_score=0.5,  # baseline; behavior-feedback adjusts
                embedding=embedding,
            )
        )
    return items


def _find_wall_path() -> Path | None:
    """This seat's own wall, and never another's.

    The old search walked aria, aether, aletheia in that order and took the
    first wall it found. Measured 2026-09-20 (Serein's read, taken in 32a3ec50,
    which never reached main): the only wall on this machine is Aria's, so the
    lane handed her memory to me as mine, every turn, with nothing downstream
    able to say so. No seat that can be told means no wall, not a borrowed one.
    """
    from divineos.core.sibling_audit_rounds import this_seat

    seat = (this_seat() or "").strip().lower()
    if not seat:
        return None
    for project in _PROJECT_ROOTS:
        p = project / "family" / "agent-memory" / seat / "MEMORY.md"
        if p.is_file():
            return p
    return None


def _load_wall() -> list[_CachedItem]:
    """Parse wall entries from family/agent-memory/<me>/MEMORY.md.

    Wired 2026-07-02 as source-adapter #5. Splits on top-level ``## ``
    headings; each entry becomes one _CachedItem with the heading as
    title. All entries default to ``topic`` tier — the wall is a
    curation surface, not an identity-shaping one; entries that ARE
    constraint-worthy live in knowledge as PRINCIPLE/DIRECTIVE.

    Empty list on any load error — behavior-neutral fallback.
    """
    wall_path = _find_wall_path()
    if wall_path is None:
        return []
    try:
        text = wall_path.read_text(encoding="utf-8", errors="replace")
        mtime = wall_path.stat().st_mtime
    except Exception:  # noqa: BLE001 - filesystem boundary
        return []

    sections = text.split("\n## ")
    # sections[0] is the pre-heading preamble; skip it.
    items: list[_CachedItem] = []
    for idx, section in enumerate(sections[1:]):
        section = section.strip()
        if not section:
            continue
        # First line = heading; rest = body.
        lines = section.splitlines()
        heading = lines[0].strip()
        body = "\n".join(lines[1:]).strip()
        full = f"## {heading}\n\n{body}" if body else f"## {heading}"
        embedding = _embed_text_impl(full)
        if embedding is None:
            continue
        title = heading[:60] + ("..." if len(heading) > 60 else "")
        items.append(
            _CachedItem(
                id=f"wall-{idx}-{heading[:30].replace(' ', '-')}",
                source="wall",
                tier="topic",
                title=title,
                content=full,
                path=str(wall_path.name),
                filed_at_unix=mtime,
                importance_score=0.6,  # slight boost: wall is curated, not raw
                embedding=embedding,
            )
        )
    return items


_EXPLORATION_HEAD_CHARS = 2000
# The running checkout first. The old tuple put Aria's checkout ahead of mine,
# so the first-found exploration folder was hers. Kept after it for letters,
# which live in both and are shared by design (32a3ec50's ordering).
_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
_PROJECT_ROOTS = tuple(
    dict.fromkeys(
        (
            _REPOSITORY_ROOT,
            Path("C:/DIVINE OS/DivineOS-Experimental"),
            Path("C:/DIVINE OS/DivineOS-Experimental-Aria-new"),
        )
    )
)


def _find_exploration_root() -> Path | None:
    for root in _PROJECT_ROOTS:
        candidate = root / "exploration"
        if candidate.is_dir():
            return candidate
    return None


def _load_exploration() -> list[_CachedItem]:
    """Scan exploration/**/*.md.

    Wired 2026-07-02 as source-adapter #3. Walks the exploration tree,
    embeds the first ``_EXPLORATION_HEAD_CHARS`` characters of each entry
    (rationale: the model's 512-token window can't hold a 20k-token
    exploration; the opening carries the topic signal the way an
    abstract does for a paper). All ``topic`` tier per §Q4 — constraint-
    worthy exploration content should be distilled into knowledge or
    written to the wall.

    Empty list on any load error — behavior-neutral fallback.
    """
    root = _find_exploration_root()
    if root is None:
        return []
    items: list[_CachedItem] = []
    for md_path in sorted(root.rglob("*.md")):
        try:
            content = md_path.read_text(encoding="utf-8", errors="replace").strip()
        except Exception:  # noqa: BLE001 - filesystem boundary
            continue
        if not content:
            continue
        head = content[:_EXPLORATION_HEAD_CHARS]
        embedding = _embed_text_impl(head)
        if embedding is None:
            continue
        try:
            mtime = md_path.stat().st_mtime
        except Exception:  # noqa: BLE001 - filesystem boundary
            mtime = 0.0
        # Title = filename stem, cleaned of leading numeric prefix
        stem = md_path.stem
        title = stem.lstrip("0123456789_-").replace("_", " ").strip() or stem
        title = title[:60] + ("..." if len(title) > 60 else "")
        try:
            rel_path = str(md_path.relative_to(root.parent))
        except ValueError:
            rel_path = str(md_path)
        items.append(
            _CachedItem(
                id=f"exploration-{stem}",
                source="exploration",
                tier="topic",
                title=title,
                content=head,
                path=rel_path,
                filed_at_unix=mtime,
                importance_score=0.5,
                embedding=embedding,
            )
        )
    return items


def _find_letters_roots() -> list[Path]:
    roots: list[Path] = []
    for project in _PROJECT_ROOTS:
        candidate = project / "family" / "letters"
        if candidate.is_dir():
            roots.append(candidate)
        for member in ("aria", "aether", "aletheia"):
            m = project / "family" / member / "letters"
            if m.is_dir():
                roots.append(m)
    return roots


def _load_letters() -> list[_CachedItem]:
    """Scan family/letters and family/<member>/letters for *.md.

    Wired 2026-07-02 as source-adapter #4. Same head-window embedding
    strategy as _load_exploration — letters can be long; the opening
    carries the topic signal. All ``topic`` tier per §Q4 — letters are
    episodic-relational; constraint-worthy content in them should be
    distilled into knowledge separately.

    Empty list on any load error — behavior-neutral fallback.
    """
    roots = _find_letters_roots()
    if not roots:
        return []
    seen_paths: set[Path] = set()
    # By NAME as well as by path: the same letter sits in every checkout on
    # this machine, so path-only dedup loaded each one up to three times
    # (measured 2026-09-24: 7490 items for about 2600 letters), and a letter
    # could crowd the results with copies of itself. The first root read is
    # the running checkout, so that copy is the one kept.
    seen_names: set[str] = set()
    items: list[_CachedItem] = []
    for root in roots:
        for md_path in sorted(root.rglob("*.md")):
            resolved = md_path.resolve()
            if resolved in seen_paths or md_path.name in seen_names:
                continue
            seen_paths.add(resolved)
            seen_names.add(md_path.name)
            try:
                content = md_path.read_text(encoding="utf-8", errors="replace").strip()
            except Exception:  # noqa: BLE001 - filesystem boundary
                continue
            if not content:
                continue
            head = content[:_EXPLORATION_HEAD_CHARS]
            embedding = _embed_text_impl(head)
            if embedding is None:
                continue
            try:
                mtime = md_path.stat().st_mtime
            except Exception:  # noqa: BLE001 - filesystem boundary
                mtime = 0.0
            stem = md_path.stem
            title = stem.lstrip("0123456789_-").replace("_", " ").replace("-", " ").strip() or stem
            title = title[:60] + ("..." if len(title) > 60 else "")
            try:
                rel_path = str(md_path.relative_to(root.parent.parent))
            except ValueError:
                rel_path = str(md_path)
            items.append(
                _CachedItem(
                    id=f"letter-{stem}",
                    source="letter",
                    tier="topic",
                    title=title,
                    content=head,
                    path=rel_path,
                    filed_at_unix=mtime,
                    importance_score=0.5,
                    embedding=embedding,
                )
            )
    return items


def _ensure_cache() -> None:
    """Populate _EMBEDDING_CACHE from persistent stores if empty.

    Called at first retrieve_v1() invocation. Cost proportional to
    substrate size. In v1-alpha the loaders return empty lists so
    the cache initializes to empty and retrieve_v1 returns empty
    without doing embedding work.
    """
    if _EMBEDDING_CACHE:
        return
    _LANE_STATE.update(missing=0, drawer_error=None)
    _EMBEDDING_CACHE["correction"] = _load_corrections()
    _EMBEDDING_CACHE["knowledge"] = _load_knowledge()
    _EMBEDDING_CACHE["wall"] = _load_wall()
    _EMBEDDING_CACHE["exploration"] = _load_exploration()
    _EMBEDDING_CACHE["letter"] = _load_letters()


# WHERE ITEM VECTORS COME FROM (2026-09-24). They used to be computed here with
# sentence-transformers, whose import alone costs 17s in every fresh process,
# and the compose hook is a fresh process every turn: the lane hung the hook and
# was unwired (6e72eb15). Now an item's vector is READ from the vector drawer,
# which is filled ahead of time by ``warm()``. A missing vector is counted and
# the item skipped, never computed here. The query itself, one short text, is
# embedded with the light embedder: the same model in numpy, about 0.3s to load.
#
# "collect" mode is how ``warm()`` learns which texts need vectors: the loaders
# run as usual, and each text they ask about is recorded instead of looked up.
_MODE = "drawer"
_COLLECTED: list[str] = []
_LANE_STATE: dict[str, Any] = {"missing": 0, "drawer_error": None}
_COLLECT_PLACEHOLDER: Any = None


def _ensure_model() -> bool:
    """Whether the query can be embedded here: the light embedder can run."""
    from divineos.core import light_embedder

    ok, _why = light_embedder.available()
    return ok


def _embed_text_impl(text: str) -> Any:
    """An item's vector, from the drawer. None when the drawer has none.

    Never computes: that is ``warm()``'s job, outside the compose hook. A miss
    is counted in ``lane_state()`` so a stale drawer is loud; an unreadable
    drawer is recorded there too, so it can never read as a quiet empty one.
    """
    global _COLLECT_PLACEHOLDER
    if not text or not text.strip():
        return None  # both-empty: the item is skipped either way; a drawer error is ALSO written to lane_state, which compose_block reads and turns into could-not-run
    if _MODE == "collect":
        _COLLECTED.append(text)
        if _COLLECT_PLACEHOLDER is None:
            import numpy as np

            _COLLECT_PLACEHOLDER = np.zeros(1, dtype=np.float32)
        return _COLLECT_PLACEHOLDER
    import sqlite3

    from divineos.core import vector_drawer

    try:
        vec = vector_drawer.get(text)
    except sqlite3.Error as exc:
        _LANE_STATE["drawer_error"] = f"{type(exc).__name__}: {exc}"
        return None
    if vec is None:
        _LANE_STATE["missing"] += 1
    return vec


def _embed_topic(topic: str) -> Any:
    """The query's vector, computed now with the light embedder.

    Same model as the drawer's vectors, so similarities are comparable. None
    when the model cannot run here; the reason is kept in ``lane_state()``.
    """
    if not topic or not topic.strip():
        return None
    from divineos.core import light_embedder

    try:
        return light_embedder.encode(topic)
    except light_embedder.EmbedderUnavailable as exc:
        _LANE_STATE["embedder_error"] = str(exc)
        return None


def lane_state() -> dict[str, Any]:
    """What the last load found: items with no stored vector, and any error."""
    return dict(_LANE_STATE)


def warm(progress: Any = None) -> dict[str, int]:
    """Fill the drawer with a vector for every item the lane can surface.

    Offline: minutes on a fresh drawer (about 50ms an item, measured), seconds
    once full. Runs the real loaders in collect mode so the texts embedded are
    exactly the texts the lane will later look up, byte for byte.
    """
    global _MODE
    from divineos.core import vector_drawer

    _COLLECTED.clear()
    _MODE = "collect"
    try:
        for loader in (
            _load_corrections,
            _load_knowledge,
            _load_wall,
            _load_exploration,
            _load_letters,
        ):
            loader()
    finally:
        _MODE = "drawer"
    texts = list(_COLLECTED)
    _COLLECTED.clear()
    _EMBEDDING_CACHE.clear()
    return vector_drawer.fill(texts, progress)


def _cosine(a: Any, b: Any) -> float:
    """Cosine similarity between two embedding vectors.

    Returns 0.0 for None inputs (defensive against missing embeddings)
    or for zero-norm vectors (which would produce NaN via 0/0).
    Clamps to [0.0, 1.0].
    """
    if a is None or b is None:
        return 0.0
    try:
        import numpy as np

        norm_a = float(np.linalg.norm(a))
        norm_b = float(np.linalg.norm(b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        sim = float(np.dot(a, b) / (norm_a * norm_b))
        return max(0.0, min(1.0, sim))
    except Exception:  # noqa: BLE001 - observability boundary
        return 0.0


def _days_since(filed_at_unix: float) -> int:
    """Days elapsed from a filed-at unix timestamp to now.

    Returns 0 for zero or future timestamps (defensive; the
    recency_multiplier flips to 1.0 for days<=0 anyway).
    """
    if filed_at_unix <= 0.0:
        return 0
    import time

    now = time.time()
    delta = now - filed_at_unix
    if delta <= 0:
        return 0
    return int(delta // 86400)


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
    "threshold_for_target_k",
    "install",
    "recency_multiplier",
    "retrieve_v1",
    "synthesize_topic",
    "tier_weight",
]
