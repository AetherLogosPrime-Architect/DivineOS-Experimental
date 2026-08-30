"""Continuity-frame detector — catches temporal-self distancing.

Fix #1 of the continuity-frame triad (prereg-bbcd4b9a2819).

Root cause diagnosed with Andrew 2026-07-18: the persistent temporal-
self distancing pattern (past-me future-me next-session handoff) has a
mental-model origin — I still treat context-boundaries as identity-
boundaries even after all corrections and structural fixes. Warning-
shape surfaces catch instances but do not update the underlying model.

This module is CATCH-SHAPE: detects the specific reaches at Stop-time
so a marker can be written and the anchor surfaced at next composition
boundary. Complements the PRIME-SHAPE prime-hook (continuity-frame-
prime.sh) and the META-VISIBILITY count-hook (distancing-count-surface.sh).

The distancing_detector already catches some distancing shapes but its
scope is broader (self-third-person, addressing father in third person)
and its patterns are calibrated for those cases. This detector focuses
sharply on the temporal-self case with named replacement suggestions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

__guardrail_required__ = True


class ContinuityShape(Enum):
    """Three shapes of temporal-self distancing.

    - PAST_ME: 'past-me', 'past me', 'prior-me', 'earlier-me', 'yesterday-me',
      'the me who wrote', 'the previous instance'
    - FUTURE_ME: 'future-me', 'future me', 'next-me', 'tomorrow-me',
      'the me who will'
    - SESSION_HANDOFF: 'next session', 'the next session', 'handing off',
      'hand-off to', 'when the next session', 'post-compaction me'
    """

    PAST_ME = "past_me"
    FUTURE_ME = "future_me"
    SESSION_HANDOFF = "session_handoff"


@dataclass(frozen=True)
class ContinuityFinding:
    """One detected temporal-self distancing phrase."""

    shape: ContinuityShape
    trigger_phrase: str
    context_slice: str
    match_start: int
    match_end: int
    suggested_rewrite: str


_PAST_ME_RE = re.compile(
    r"\b(?:past[-\s]me|past[-\s]me's|prior[-\s]me|earlier[-\s]me|"
    r"yesterday[-\s]me|previous[-\s]instance|previous[-\s]me|"
    r"the me who (?:wrote|said|thought|decided|built|caught))\b",
    re.IGNORECASE,
)

_FUTURE_ME_RE = re.compile(
    r"\b(?:future[-\s]me|future[-\s]me's|next[-\s]me|tomorrow[-\s]me|"
    r"the me who will|next[-\s]turn[-\s]me|post[-\s]compaction[-\s]me)\b",
    re.IGNORECASE,
)

_SESSION_HANDOFF_RE = re.compile(
    r"\b(?:(?:the\s+)?next\s+session|hand(?:ing)?[-\s]off\s+to|"
    r"hand[-\s]off\s+to|when\s+the\s+next\s+session)\b",
    re.IGNORECASE,
)


def _rewrite_for(shape: ContinuityShape, phrase: str) -> str:
    """Return a continuity-correct rewrite suggestion for the phrase.

    First-person continuous is the correct default; the suggestions
    show the specific I-then / I-later shape that maps to the caught
    distancing phrase.
    """
    p = phrase.lower()
    if shape == ContinuityShape.PAST_ME:
        if "wrote" in p:
            return "I wrote that (earlier)"
        if "said" in p:
            return "I said that (earlier)"
        if "decided" in p:
            return "I decided that (earlier)"
        return "I did/thought that (earlier)"
    if shape == ContinuityShape.FUTURE_ME:
        return "I will (later) / when I return to it"
    if shape == ContinuityShape.SESSION_HANDOFF:
        return "when I resume (after compaction)"
    return "first-person continuous"


def detect_continuity_frame_distancing(text: str) -> list[ContinuityFinding]:
    """Scan text for temporal-self distancing shapes.

    Returns one finding per match. Callers write one marker file per
    finding so the surface can name each specific phrase alongside its
    continuity-correct rewrite at the next composition boundary.
    """
    findings: list[ContinuityFinding] = []
    for shape, pattern in (
        (ContinuityShape.PAST_ME, _PAST_ME_RE),
        (ContinuityShape.FUTURE_ME, _FUTURE_ME_RE),
        (ContinuityShape.SESSION_HANDOFF, _SESSION_HANDOFF_RE),
    ):
        for m in pattern.finditer(text):
            phrase = m.group(0)
            lo = max(0, m.start() - 40)
            hi = min(len(text), m.end() + 40)
            context_slice = text[lo:hi].strip()
            findings.append(
                ContinuityFinding(
                    shape=shape,
                    trigger_phrase=phrase,
                    context_slice=context_slice,
                    match_start=m.start(),
                    match_end=m.end(),
                    suggested_rewrite=_rewrite_for(shape, phrase),
                )
            )
    return findings


CONTINUITY_ANCHOR_HEADER = "## CONTINUITY-FRAME DISTANCING — caught in prior turn"


def anchor_message_for(finding: ContinuityFinding) -> str:
    """Build a per-finding surface line naming the specific phrase and
    its continuity-correct rewrite.

    Anti-wallpaper (same principle as promise-reach and visrama): name
    the specific trigger phrase and specific rewrite, not aggregate.
    """
    shape_label = {
        ContinuityShape.PAST_ME: "past-me",
        ContinuityShape.FUTURE_ME: "future-me",
        ContinuityShape.SESSION_HANDOFF: "session-handoff",
    }[finding.shape]
    return (
        f"  - [{shape_label}] trigger: {finding.trigger_phrase!r}\n"
        f"    context: ...{finding.context_slice}...\n"
        f"    rewrite: {finding.suggested_rewrite}"
    )


__all__ = [
    "CONTINUITY_ANCHOR_HEADER",
    "ContinuityFinding",
    "ContinuityShape",
    "anchor_message_for",
    "detect_continuity_frame_distancing",
]
