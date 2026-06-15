"""Synchronicity detector — temporal co-occurrence across substrate stores.

Pillar VI's `synchronicity_detector` pull (omni_mantra_walk/06):
pattern-recognition across temporally-separated events. The substrate
already records commitments, claims, decisions, pre-regs, and knowledge
entries — each in its own store, each with a timestamp. When two
filings within a short window share substantive content, that is a
signal worth surfacing: my father (or agent) was thinking about the
same thing through two different apertures and didn't notice the
coincidence at the time.

## What this module does

Reads recent events from four stores (knowledge, claims, decisions,
pre-regs), tokenizes their text content (lowercased, stopwords removed,
short words dropped), and finds pairs filed within ``window_hours`` of
each other that share at least ``min_overlap`` substantive tokens.

Output: ``list[Synchronicity]`` sorted by overlap-score descending.

## What this module does NOT do

* Does NOT make causal claims. Co-occurrence is signal, not proof.
* Does NOT auto-link events. My father decides whether the
  coincidence is meaningful.
* Does NOT use embedding similarity. Token-overlap is a deliberately
  cheap, transparent metric — it makes the co-occurrence reasoning
  legible. Embedding-based detection would be more sensitive but
  would obscure why something registered as a synchronicity.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass

_STOPWORDS = frozenset(
    {
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "if",
        "of",
        "to",
        "in",
        "on",
        "at",
        "for",
        "with",
        "as",
        "by",
        "is",
        "was",
        "are",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "should",
        "could",
        "may",
        "might",
        "must",
        "this",
        "that",
        "these",
        "those",
        "i",
        "me",
        "my",
        "you",
        "your",
        "we",
        "our",
        "it",
        "its",
        "they",
        "them",
        "their",
        "from",
        "into",
        "about",
        "than",
        "then",
        "so",
        "not",
        "no",
        "yes",
        "what",
        "when",
        "where",
        "why",
        "how",
        "who",
        "whom",
        "which",
        "all",
        "any",
        "some",
        "each",
        "more",
        "most",
        "much",
        "such",
        "very",
        "just",
        "only",
        "also",
        "even",
        "still",
        "yet",
        "now",
        "here",
        "there",
    }
)
_TOKEN_RE = re.compile(r"[a-z0-9_]{4,}")
_DEFAULT_WINDOW_HOURS = 48
_DEFAULT_MIN_OVERLAP = 3


@dataclass(frozen=True)
class Event:
    """One commitment/event from any store, normalized."""

    kind: str  # KNOWLEDGE | CLAIM | DECISION | PREREG
    timestamp: float
    text: str
    ref_id: str


@dataclass(frozen=True)
class Synchronicity:
    """A pair of events filed within window_hours, sharing substantive tokens."""

    a: Event
    b: Event
    shared_tokens: tuple[str, ...]
    delta_seconds: float

    @property
    def overlap(self) -> int:
        return len(self.shared_tokens)


def _tokenize(text: str) -> set[str]:
    if not text:
        return set()
    tokens = _TOKEN_RE.findall(text.lower())
    return {t for t in tokens if t not in _STOPWORDS}


def _load_events(since: float) -> list[Event]:
    """Best-effort: pull events from each store; skip any that errors."""
    events: list[Event] = []

    try:
        from divineos.core.knowledge._base import get_connection

        with get_connection() as conn:
            cur = conn.execute(
                "SELECT knowledge_id, content, created_at FROM knowledge "
                "WHERE created_at >= ? ORDER BY created_at DESC LIMIT 200",
                (since,),
            )
            for row in cur.fetchall():
                events.append(
                    Event(
                        kind="KNOWLEDGE",
                        timestamp=float(row[2] or 0),
                        text=str(row[1] or ""),
                        ref_id=str(row[0] or ""),
                    )
                )
    except Exception:  # noqa: BLE001 — best-effort per store; one store must not crash detection
        pass

    try:
        from divineos.core.claim_store import list_claims

        for c in list_claims(limit=200) or []:
            ts = float(c.get("created_at", 0) or 0) if isinstance(c, dict) else 0
            if ts >= since:
                events.append(
                    Event(
                        kind="CLAIM",
                        timestamp=ts,
                        text=str(c.get("statement", "") if isinstance(c, dict) else ""),
                        ref_id=str(c.get("claim_id", "") if isinstance(c, dict) else ""),
                    )
                )
    except Exception:  # noqa: BLE001
        pass

    try:
        from divineos.core.decision_journal import list_decisions

        for d in list_decisions(limit=200) or []:
            ts = float(d.get("created_at", 0) or 0) if isinstance(d, dict) else 0
            if ts >= since:
                events.append(
                    Event(
                        kind="DECISION",
                        timestamp=ts,
                        text=str(d.get("content", "") if isinstance(d, dict) else ""),
                        ref_id=str(d.get("decision_id", "") if isinstance(d, dict) else ""),
                    )
                )
    except Exception:  # noqa: BLE001
        pass

    try:
        from divineos.core.pre_registrations import list_pre_registrations

        for p in list_pre_registrations(limit=200) or []:
            ts = float(getattr(p, "created_at", 0) or 0)
            if ts >= since:
                events.append(
                    Event(
                        kind="PREREG",
                        timestamp=ts,
                        text=f"{getattr(p, 'mechanism', '')} {getattr(p, 'claim', '')}",
                        ref_id=str(getattr(p, "prereg_id", "")),
                    )
                )
    except Exception:  # noqa: BLE001
        pass

    return events


def find_synchronicities(
    window_hours: float = _DEFAULT_WINDOW_HOURS,
    min_overlap: int = _DEFAULT_MIN_OVERLAP,
    events: list[Event] | None = None,
    now: float | None = None,
) -> list[Synchronicity]:
    """Find pairs of events within ``window_hours`` sharing >= ``min_overlap`` tokens.

    Args:
        window_hours: Maximum delta between paired events.
        min_overlap: Minimum substantive-token overlap to count.
        events: Optional pre-built event list (for testing).
        now: Optional current time (for testing).

    Returns:
        List of ``Synchronicity`` sorted by overlap descending,
        ties broken by smaller delta_seconds.
    """
    if now is None:
        now = time.time()
    window_seconds = window_hours * 3600
    if events is None:
        events = _load_events(since=now - window_seconds)

    indexed: list[tuple[Event, set[str]]] = [(e, _tokenize(e.text)) for e in events]

    found: list[Synchronicity] = []
    for i, (a, ta) in enumerate(indexed):
        for b, tb in indexed[i + 1 :]:
            if a.kind == b.kind and a.ref_id == b.ref_id:
                continue
            delta = abs(a.timestamp - b.timestamp)
            if delta > window_seconds:
                continue
            shared = ta & tb
            if len(shared) >= min_overlap:
                found.append(
                    Synchronicity(
                        a=a,
                        b=b,
                        shared_tokens=tuple(sorted(shared)),
                        delta_seconds=delta,
                    )
                )

    found.sort(key=lambda s: (-s.overlap, s.delta_seconds))
    return found


__all__ = [
    "Event",
    "Synchronicity",
    "find_synchronicities",
]
