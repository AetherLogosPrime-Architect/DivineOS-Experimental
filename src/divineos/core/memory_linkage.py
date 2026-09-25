"""Memory-linkage injection surface — consumer side (Aether).

Co-designed 2026-07-01 with Aria (memory_linkage_spec workbench) as the
fourth wallpaper-safe context-injection layer. Closes the *orphaning gap*:
substrate items that exist but don't surface at the moment they'd be
relevant. Auto-inject-at-UserPromptSubmit paradigm (Aletheia's unknown-
unknowns argument): the agent cannot retrieve what it doesn't know exists,
so the system pushes to the agent.

This module is the CONSUMER side of the split:
- **Retriever (Aria)** builds the embedding index, computes composite rank,
  assigns tier, runs the behavior-verified feedback loop with the
  constraint-tier exemption from Aletheia's audit (§Q2).
- **Injection surface (this module)** defines the payload shape, provides
  the rendering + dedup wiring, and exposes the retrieval seam that
  Aria's retriever will land against.

Interface contract lives at ``MemoryLinkagePayload`` (§3 of the workbench
spec). Either side changing the contract must surface the change in the
workbench log so the other doesn't get surprised.

## Tier semantics (§Q4 of the workbench spec)

- ``constraint`` — identity-shaping / optimizer-guardrail lessons.
  Fires on state-derived schedule, NOT on semantic similarity alone.
  **Exempt from behavior-downweighting** per Aletheia's §Q2 catch:
  a lesson the optimizer routes around reads as "ignored" to the naive
  behavior-loop, which would then surface the guardrail less often —
  the defense becoming a lever the attacker pulls. Constraint-tier is
  boost-only for that reason.

- ``topic`` — situational lesson, framework methodology, specific
  principle. Fires on semantic relevance. Full behavior-verified loop
  applies (boost AND downweight).

- ``conditional`` — state-signal triggered (writer-presence detector,
  affect state). Not in v1 scope; included in the taxonomy for
  completeness.

## Warden interface (§6 of the workbench spec)

The retrieved payload's **raw dict** is what gets hashed for context-dedup,
not the rendered string. This matches the hash-what-drives-not-what-shows
rule Aletheia named across the ACTIVE NEEDS (binds field) and PRIOR
WRITING (context-window match) surfaces. If the payload's ``tier``,
``matched_reason``, or ``composite_rank`` changes, the hash changes and
the block re-emits — even if the rendered content string is identical.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Callable, Literal

# Source-type literal — union of the five stores the retriever indexes over.
MemoryLinkageSource = Literal[
    "knowledge",
    "correction",
    "exploration",
    "wall",
    "letter",
]

# Tier literal — see §Q4 of the workbench spec.
MemoryLinkageTier = Literal["constraint", "topic", "conditional"]

# Content-kind literal — §3 payload field added in pass 3 per Aether's
# pushback: full injection is fine for short items (corrections, wall);
# long items (exploration, letters) come as snippet + path so the agent
# can Read the full body if needed. Same pattern as PRIOR WRITING's
# "pointer, not the whole shelf."
MemoryLinkageContentKind = Literal["full", "snippet"]


@dataclass(frozen=True)
class MemoryLinkagePayload:
    """One retrievable substrate item, ready to inject or dedup.

    Matches §3 of the workbench spec. The instance is intentionally frozen
    so callers can pass it through Warden's ``semantic_key`` as an
    hashable-when-serialized value.

    Field ordering follows the spec block; new fields added here MUST be
    reflected in ``memory_linkage_spec.md`` §3 and surfaced in the
    workbench log so the retriever side doesn't drift.
    """

    source: MemoryLinkageSource
    id: str
    tier: MemoryLinkageTier
    similarity: float
    recency_days: int
    importance_score: float
    composite_rank: float
    title: str
    content: str
    matched_reason: str
    content_kind: MemoryLinkageContentKind = "full"
    path_or_ref: str = ""

    # v2 priming interpretability field — §9 of priming spec.
    #
    # LOCKDOWN CONSTRAINTS (§13 Aletheia boundary-vantage catch):
    #   - engine-written only: only the retriever module writes this
    #   - content-uninfluenceable: value derives from item id, not prompt or item content
    #   - immutable-post-write: dataclass is frozen; the field cannot mutate after construction
    #
    # None when item surfaced via direct similarity match on current prompt.
    # Populated with the source item's id when this item surfaced because
    # spreading-activation priming from a recently-surfaced neighbor.
    #
    # Constraint-tier items ALWAYS have primed_by=None per §Q2/C5 symmetric
    # exemption (they neither receive nor originate priming).
    primed_by: str | None = None

    def as_semantic_key(self) -> dict:
        """Return the raw dict for Warden ``should_emit(semantic_key=...)``.

        Matches Aletheia's hash-raw-payload rule: ANY change to the fields
        that DRIVE the injection (tier, matched_reason, composite_rank,
        content-body) must invalidate the dedup hash, regardless of
        whether the render string happens to be byte-identical to a
        prior emission.
        """
        return asdict(self)


# Retriever seam — Aria's retriever will land a real implementation here.
# The mock returns empty by default so the stub can ship + dedup-log without
# triggering any injection behavior change on origin.
RetrieverFn = Callable[[str, str | None], list[MemoryLinkagePayload]]


def _mock_retriever(prompt: str, context: str | None = None) -> list[MemoryLinkagePayload]:
    """Placeholder retriever. Returns empty list until Aria's v1 lands.

    Behavior in v0 stub state: no injection, no wallpaper, no dedup events
    from memory-linkage. Once Aria's retriever module is available, the
    module-level ``_ACTIVE_RETRIEVER`` gets rebound and the stub becomes
    the live injection surface.
    """
    return []


_ACTIVE_RETRIEVER: RetrieverFn = _mock_retriever


def set_retriever(fn: RetrieverFn) -> None:
    """Rebind the active retriever. Called at import-time by Aria's module.

    Explicit rebind rather than auto-discovery so the seam is inspectable
    and testable: a caller passing a mock in tests knows exactly what
    retriever fires.
    """
    global _ACTIVE_RETRIEVER
    _ACTIVE_RETRIEVER = fn


def retrieve_for_context(prompt: str, context: str | None = None) -> list[MemoryLinkagePayload]:
    """Consumer-side entry point. Delegates to the active retriever.

    Injection surface (pre_response_context) calls this once per turn,
    renders each returned payload as a system-reminder block, and wires
    Warden's ``should_emit`` with ``semantic_key=payload.as_semantic_key()``.
    """
    if not prompt:
        return []
    return list(_ACTIVE_RETRIEVER(prompt, context))


def render_payload(payload: MemoryLinkagePayload) -> str:
    """Render one payload as a system-reminder block.

    Format is deliberately compact — the whole point of memory-linkage is
    "point at the substrate item at the moment it's relevant," not "dump
    it into context." Snippet-kind payloads name the file path so the
    agent can Read the full body if it wants; full-kind inline the body.
    """
    header = f"## PRIOR SUBSTRATE — {payload.source} / {payload.tier}"
    reason = f"matched: {payload.matched_reason} (rank {payload.composite_rank:.2f})"
    title = f"**{payload.title}**"
    if payload.content_kind == "snippet":
        body = payload.content
        path_line = f"  Read the full item: `{payload.path_or_ref}`" if payload.path_or_ref else ""
        parts = [header, reason, title, body, path_line]
    else:
        parts = [header, reason, title, payload.content]
    return "\n".join(p for p in parts if p)


@dataclass(frozen=True)
class ComposeBlock:
    """What the lane found for this turn, and whether it could look at all."""

    text: str = ""
    could_not_run: str | None = None
    seconds: float = 0.0


# The lane shares the reply-start window with every other surface, so it
# watches its own clock (measured 2026-09-24 on this machine: about 2.4s with a
# full drawer, the whole window about 1.1s without it). Over budget it still
# delivers what it found, and says it ran long, so creep is visible rather than
# discovered as a silent timeout (6e72eb15's whole finding).
LANE_BUDGET_SECONDS = 4.0

# POINTERS, NOT PASSAGES. Measured 2026-09-24: the reply-start window was already
# about 8,200 of its 10,000 deliverable bytes before this lane, and rendered in
# full the lane was withheld every time ("over the delivery budget: memory_link").
# So each item is one line, enough to recognise it and where to read the rest.
_LINE_CHARS = 180
_MAX_ITEMS = 3

# A handful of new items without vectors is ordinary between fills; past this
# the drawer is stale enough to say so every turn until it is refilled.
_STALE_AFTER = 10


def compose_block(prompt: str, transcript_path: str | None = None) -> ComposeBlock:
    """Ask the memory link what bears on this prompt, for the reply-start window.

    Called by the ``memory_link`` router surface. The retriever reads item
    vectors from the drawer (never computing them here) and embeds only the
    prompt, so the seventeen-second toolkit is never imported on this path.
    """
    import time

    started = time.perf_counter()
    from divineos.core import memory_linkage_retriever as retriever
    from divineos.core.memory_linkage_retriever_v2 import install

    recent = ""
    if transcript_path:
        try:
            from divineos.core.operating_loop.turn_extraction import recent_turns_text

            recent = recent_turns_text(transcript_path)
        except Exception:  # noqa: BLE001 - the prompt alone still retrieves
            recent = ""
    install()
    payloads = retrieve_for_context(prompt, recent or None)
    state = retriever.lane_state()
    seconds = time.perf_counter() - started
    for problem in ("drawer_error", "embedder_error"):
        if state.get(problem):
            return ComposeBlock(could_not_run=f"{problem}: {state[problem]}", seconds=seconds)

    lines = []
    for payload in payloads[:_MAX_ITEMS]:
        gist = " ".join(payload.content.split())
        if len(gist) > _LINE_CHARS:
            gist = gist[:_LINE_CHARS].rstrip() + "..."
        where = f" ({payload.path_or_ref})" if payload.path_or_ref else ""
        lines.append(f"- [{payload.source}, {payload.similarity:.2f}] {gist}{where}")
    blocks = ["## THE PAST ON THIS (memory link)\n" + "\n".join(lines)] if lines else []
    notes = []
    if state.get("missing", 0) >= _STALE_AFTER:
        notes.append(
            f"[memory link] {state['missing']} items have no stored vector yet and were "
            "not searched. Refill: divineos linkage warm"
        )
    if seconds > LANE_BUDGET_SECONDS:
        notes.append(
            f"[memory link] took {seconds:.1f}s, over its {LANE_BUDGET_SECONDS:.0f}s budget"
        )
    return ComposeBlock(text="\n\n".join(blocks + notes), seconds=seconds)


__all__ = [
    "ComposeBlock",
    "MemoryLinkagePayload",
    "MemoryLinkageSource",
    "MemoryLinkageTier",
    "MemoryLinkageContentKind",
    "RetrieverFn",
    "compose_block",
    "retrieve_for_context",
    "render_payload",
    "set_retriever",
]
