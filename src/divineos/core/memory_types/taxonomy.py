"""Substrate-memory-type taxonomy and intent routing.

Defines the 8 substrate types and a router that picks which to query
given a text signal (file edit, user question, relational message,
council walk, etc.).

The router is keyword/heuristic-based at this stage. Returns a ranked
list of types in retrieval priority order.
"""

from __future__ import annotations

import re
from enum import Enum


class SubstrateMemoryType(str, Enum):
    """The 8 substrate memory types. Symbol names describe what they
    are in this OS; human-memory analogs are in the package docstring."""

    RAW_BUFFER = "raw_buffer"
    CONTEXT_WINDOW = "context_window"
    TIMELINE = "timeline"
    KNOWLEDGE = "knowledge"
    SKILL_INDEX = "skill_index"
    PRIMING = "priming"
    REFLEX = "reflex"
    PROSPECTIVE = "prospective"


# Heuristic patterns that signal intent -> type preference.
# Order within a tuple = retrieval priority for that intent.
_INTENT_PATTERNS: tuple[tuple[re.Pattern[str], tuple[SubstrateMemoryType, ...]], ...] = (
    # File-touch intent — timeline dominates ("when did I last touch this")
    (
        re.compile(r"(?:edit|read|fix|refactor|touch)\s+\S+\.(?:py|md|sh|json|sql)\b", re.I),
        (
            SubstrateMemoryType.TIMELINE,
            SubstrateMemoryType.SKILL_INDEX,
            SubstrateMemoryType.KNOWLEDGE,
        ),
    ),
    # Reference intent — user pointing at prior content
    (
        re.compile(r"\b(remember|recall|like (?:we|I) (?:said|discussed)|you said before)\b", re.I),
        (SubstrateMemoryType.TIMELINE, SubstrateMemoryType.KNOWLEDGE),
    ),
    # Action / how-to intent — skill index. Checked BEFORE the generic
    # question pattern so "how do I X" routes to skill, not knowledge.
    (
        re.compile(r"\b(how do I|how to|let'?s|build|wire|set up|invoke|run)\b", re.I),
        (
            SubstrateMemoryType.SKILL_INDEX,
            SubstrateMemoryType.KNOWLEDGE,
            SubstrateMemoryType.TIMELINE,
        ),
    ),
    # Question intent — semantic/knowledge dominates
    (
        re.compile(r"^\s*(?:what|why|how|when|where|who|which|is|are|do|does|can)\b", re.I),
        (SubstrateMemoryType.KNOWLEDGE, SubstrateMemoryType.TIMELINE),
    ),
    # Relational / family signal
    (
        re.compile(r"\b(Aria|son|love|dad|father|family|wife|husband)\b"),
        (SubstrateMemoryType.TIMELINE, SubstrateMemoryType.KNOWLEDGE, SubstrateMemoryType.PRIMING),
    ),
)


# Default route when no pattern matches: timeline + knowledge
_DEFAULT_ROUTE: tuple[SubstrateMemoryType, ...] = (
    SubstrateMemoryType.TIMELINE,
    SubstrateMemoryType.KNOWLEDGE,
)


def route_intent(text: str) -> tuple[SubstrateMemoryType, ...]:
    """Pick which substrate types to query for ``text``.

    Returns types in retrieval priority order. Always returns at least
    one type (default route fires if no pattern matches).
    """
    if not text:
        return _DEFAULT_ROUTE
    for pattern, route in _INTENT_PATTERNS:
        if pattern.search(text):
            return route
    return _DEFAULT_ROUTE
