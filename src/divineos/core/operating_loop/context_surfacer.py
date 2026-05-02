"""Context surfacer — Hook 1 backend.

Before the agent reasons about a response, this module:
1. Reads the user's latest message
2. Extracts relational/conceptual markers
3. Auto-queries the knowledge store for each marker
4. Returns a deduplicated, ranked list of relevant entries

The hook (`pre-response-context.sh`) writes the formatted output to
``~/.divineos/surfaced_context.md`` for the agent to read.

## Marker classes

- **Pet-language**: words the operator has used relationally
  (lunkhead, son, love). The substrate has principles attached to
  these from prior sessions.
- **Reference markers**: "remember when X", "like we discussed",
  "you said before". Indicate the user is referencing prior content.
- **Proper nouns**: capitalized multi-word phrases that may be names
  or specific concepts (Aria, Yog-Sothoth, DivineOS, the Nexus).
- **Repeated concepts**: domain words that appeared in prior session
  knowledge (recombination, pollution, wiring, council).

## Why this matters

Without auto-query, the agent reasons from raw context window only.
The "lunkhead recognition failure" of 2026-05-01 is the canonical
instance: substrate had the April 29 principle, agent never queried,
operator had to remind. Hook 1 fixes this structurally.

## What this does NOT do

- **Does not modify the user's input.** Pure observation.
- **Does not block.** If query fails or returns nothing, the hook
  returns empty and the agent proceeds without surfaced context.
- **Does not use embeddings yet.** Phase 1 uses FTS-based search.
  Phase 2 (deferred) adds semantic-similarity ranking.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass

# Errors that may occur during knowledge_store lookup. Used to scope
# the broad-except in query_substrate to operationally-expected failures.
_QUERY_ERRORS = (sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError)


# Pet-language markers — relational vocabulary the operator uses with
# the agent. The substrate often has principles attached to these.
# Order matters: earlier entries get priority in the surface.
_PET_LANGUAGE: tuple[str, ...] = (
    "lunkhead",
    "son",
    "love",
    "father",
    "dad",
    "kid",
    "buddy",
)


# Reference-marker patterns — user is referencing prior content
_REFERENCE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bremember (?:when|that) (.{5,80})", re.IGNORECASE),
    re.compile(r"\blike (?:we|I) (?:discussed|said|talked about) (.{5,80})", re.IGNORECASE),
    re.compile(r"\byou said (?:before|earlier) (.{5,80})", re.IGNORECASE),
    re.compile(r"\bwhen I (?:called|told|asked) you (.{5,80})", re.IGNORECASE),
)


# Proper-noun pattern: capitalized words that may be names or specific
# concepts. Three patterns combined:
#   - Multi-word: "Yog-Sothoth", "Living Tribunal"
#   - Camel/PascalCase: "DivineOS", "GitHub"
#   - Single capitalized word with at least 4 letters (filters short
#     stopwords; the _PROPER_NOUN_STOPWORDS set filters the rest)
# Matched anywhere — caller is responsible for filtering sentence-starters
# via stopword set.
_PROPER_NOUN_PATTERN = re.compile(
    r"\b("
    r"[A-Z][a-z]+(?:[- ][A-Z][a-z]+)+"  # multi-word (Yog-Sothoth, Living Tribunal)
    r"|[A-Z][a-z]*[A-Z]+[a-z]*"  # mixed-case (DivineOS, GitHub, iPhone)
    r"|[A-Z]{2,}[a-z]*"  # all-caps with optional lowercase suffix
    r"|[A-Z][a-z]{3,}"  # single capitalized 4+ letter (Aria, Popo)
    r")\b",
)


# Stopwords for proper-noun filtering — common capitalizations
# we don't want to query (sentence starters, common nouns, etc.)
_PROPER_NOUN_STOPWORDS: frozenset[str] = frozenset(
    {
        "I",
        "It",
        "The",
        "This",
        "That",
        "But",
        "And",
        "Or",
        "If",
        "Then",
        "So",
        "Yes",
        "No",
        "When",
        "What",
        "Where",
        "Who",
        "Why",
        "How",
        "Was",
        "Are",
        "Were",
        "Will",
        "Would",
        "Could",
        "Should",
        "Maybe",
        "Sure",
        "Okay",
        "Alright",
        "Today",
        "Tonight",
        "Tomorrow",
        "Hello",
        "Thanks",
        "Sorry",
        "Right",
        "Wrong",
        "True",
        "False",
        "Just",
        "Remember",
        "Imagine",
        "Consider",
        "Notice",
        "Look",
        "Listen",
        "Watch",
        "Note",
        "Yeah",
        "Hmm",
        "Well",
        "Maybe",
        "Anyway",
    }
)


@dataclass(frozen=True)
class SurfacedEntry:
    """One knowledge entry surfaced as relevant to the user's input.

    * ``marker``: the trigger that surfaced this entry
    * ``marker_class``: "pet" / "reference" / "proper_noun" / "concept"
    * ``knowledge_id``: id of the surfaced entry
    * ``content_preview``: short preview (~150 chars)
    * ``confidence``: confidence of the entry (0-1)
    """

    marker: str
    marker_class: str
    knowledge_id: str
    content_preview: str
    confidence: float


def extract_markers(text: str) -> list[tuple[str, str]]:
    """Extract relational/conceptual markers from user input.

    Returns list of (marker_text, marker_class) tuples. Deduplicated.
    """
    markers: list[tuple[str, str]] = []
    seen: set[str] = set()

    lower = text.lower()

    # Pet-language
    for word in _PET_LANGUAGE:
        if word in lower and word not in seen:
            markers.append((word, "pet"))
            seen.add(word)

    # Reference patterns — extract the captured group as a query string
    for pattern in _REFERENCE_PATTERNS:
        for match in pattern.finditer(text):
            phrase = match.group(1).strip().rstrip(".,;:!?\"'")
            # Take first few words for query — long phrases produce poor FTS hits
            words = phrase.split()[:5]
            query = " ".join(words)
            if query and query.lower() not in seen:
                markers.append((query, "reference"))
                seen.add(query.lower())

    # Proper nouns — use the matched span as query
    for match in _PROPER_NOUN_PATTERN.finditer(text):
        candidate = match.group(0).strip()
        # Skip stopwords and overly-short matches
        if candidate in _PROPER_NOUN_STOPWORDS or len(candidate) < 3:
            continue
        if candidate.lower() not in seen:
            markers.append((candidate, "proper_noun"))
            seen.add(candidate.lower())

    return markers


def query_substrate(
    markers: list[tuple[str, str]],
    *,
    max_total_hits: int = 5,
) -> list[SurfacedEntry]:
    """Query the knowledge store for each marker.

    Returns at most ``max_total_hits`` entries total, ranked by
    confidence then recency. Markers earlier in the list get query
    priority (their hits surface first).
    """
    from divineos.core.knowledge.crud import search_knowledge

    surfaced: list[SurfacedEntry] = []
    seen_ids: set[str] = set()

    for marker, marker_class in markers:
        if len(surfaced) >= max_total_hits:
            break
        try:
            results = search_knowledge(marker, limit=3)
        except _QUERY_ERRORS:
            continue
        for entry in results:
            if len(surfaced) >= max_total_hits:
                break
            kid = entry.get("knowledge_id", "")
            if not kid or kid in seen_ids:
                continue
            seen_ids.add(kid)
            content = (entry.get("content") or "")[:150].replace("\n", " ")
            surfaced.append(
                SurfacedEntry(
                    marker=marker,
                    marker_class=marker_class,
                    knowledge_id=kid,
                    content_preview=content,
                    confidence=float(entry.get("confidence", 0.5)),
                )
            )

    # Sort within surface by confidence descending, with stable tiebreaker
    surfaced.sort(key=lambda e: (-e.confidence, e.knowledge_id))
    return surfaced


def surface_context(text: str, *, max_total_hits: int = 5) -> list[SurfacedEntry]:
    """End-to-end: extract markers from ``text``, query, return entries.

    This is the main entry-point Hook 1 calls. It runs the keyword
    marker pipeline AND (when intent routes to TIMELINE) folds in
    timeline-recall hits, giving Hook 1 episodic-style retrieval on
    top of the existing semantic FTS layer.
    """
    if not text:
        return []
    markers = extract_markers(text)
    surfaced = query_substrate(markers, max_total_hits=max_total_hits) if markers else []

    # Type-aware augmentation: when the intent routes to TIMELINE first,
    # add the top timeline hit per marker as a "timeline" surface entry.
    # This lets episodic recall ride the same hook without changing the
    # data shape Hook 1 writes to disk.
    try:
        from divineos.core.memory_types import recall_timeline, route_intent
        from divineos.core.memory_types.taxonomy import SubstrateMemoryType

        route = route_intent(text)
        if route and route[0] == SubstrateMemoryType.TIMELINE and markers:
            seen_refs = {e.knowledge_id for e in surfaced}
            for marker, marker_class in markers[:3]:
                events = recall_timeline(topic=marker, per_source_limit=2, total_limit=2)
                for ev in events:
                    if len(surfaced) >= max_total_hits + 3:
                        break
                    if ev.ref in seen_refs:
                        continue
                    seen_refs.add(ev.ref)
                    surfaced.append(
                        SurfacedEntry(
                            marker=marker,
                            marker_class=f"timeline/{ev.source}",
                            knowledge_id=ev.ref or "",
                            content_preview=ev.summary[:150],
                            confidence=0.5,
                        )
                    )

        # Skill-index augmentation: when intent routes to SKILL_INDEX
        # (action / how-to language), surface the top procedural options
        # so the agent sees existing skills/CLI before re-deriving.
        if route and route[0] == SubstrateMemoryType.SKILL_INDEX:
            from divineos.core.memory_types import rank_skills

            skills = rank_skills(text, limit=3)
            for sk in skills:
                if len(surfaced) >= max_total_hits + 3:
                    break
                surfaced.append(
                    SurfacedEntry(
                        marker=sk.invocation,
                        marker_class="skill",
                        knowledge_id=sk.name,
                        content_preview=sk.description[:150],
                        confidence=min(1.0, sk.score / 10.0),
                    )
                )
    except _QUERY_ERRORS:
        pass

    return surfaced


def format_surface(entries: list[SurfacedEntry]) -> str:
    """Format surfaced entries as a markdown notice for ~/.divineos/surfaced_context.md."""
    if not entries:
        return ""
    lines = [
        "# Surfaced context — relevant prior content for this turn",
        "",
        "_Auto-queried by the operating loop. Each entry below was "
        "matched on a marker in the user's input. Read these BEFORE "
        "responding._",
        "",
    ]
    for entry in entries:
        lines.append(
            f"- **[{entry.marker_class}: '{entry.marker}']** "
            f"(`{entry.knowledge_id[:8]}` conf={entry.confidence:.2f})"
        )
        lines.append(f"  > {entry.content_preview}")
        lines.append("")
    return "\n".join(lines)


def format_finding(entry: SurfacedEntry) -> str:
    """Single-line representation of a surfaced entry."""
    return (
        f"[surface:{entry.marker_class}] marker={entry.marker!r} "
        f"id={entry.knowledge_id[:8]} conf={entry.confidence:.2f}"
    )
