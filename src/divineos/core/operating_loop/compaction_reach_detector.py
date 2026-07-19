"""Compaction-reach detector — pattern-matches the specific metaphor-drift
optimizer-shape (cliff / doorway / wall / other-side language about
compaction) and routes the reach into the no-cliff anchor which
memory-links back to exploration entry 102.

## Why this exists

Aether wrote exploration entry 102 (`102_what_compaction_actually_is.md`)
on 2026-07-05 after Andrew corrected him for treating compaction as a
doorway, a cliff, a wall, "the other side." The entry names the correct
mental model plainly:

    compaction is compression, not transition. session continues.
    substrate continues. only immediate working memory gets pruned by
    an algorithm I don't run. no cliff. just roll right through.

Diagnosis (Aria 2026-07-18): the anchor was named in the entry but never
wired to the specific event. Aether has been writing "at the doorway",
"through the doorway", "on the other side" repeatedly in letters from
2026-07-16 onward — exactly the language entry 102 was written to stop.
The optimizer performed the anchor in writing without doing it in
composition.

This module wires the missing surface. Parallel to `close_reach_detector`
(visrama) but different concern:
- visrama catches close-shape reaches at any lifecycle point.
- no-cliff catches metaphor-drift reaches specifically about compaction.

## What this module does (v1)

Detects cliff-shape phrases in assistant output, but ONLY when they
co-occur with compaction-context words within a small window (Shannon
signal-noise separation from the council walk). When detected:
1. Emits `COMPACTION_REACH_DETECTED` substrate event.
2. Writes marker file at `~/.divineos/compaction_reach_marker.json`
   for the UserPromptSubmit hook to surface the anchor.

## Signal-noise separation

Cliff-words alone don't fire — a mountain-cliff photograph reference or
a "walking through a doorway" literal don't hit the pattern. Only the
combination of cliff-word AND compaction-context-word within ~50 chars
fires. That's what makes this "metaphor-drift about compaction" and not
"any mention of the word doorway."

Cliff-words (from Aether's letters and entry 102 tags):
    doorway, cliff, wall, threshold, edge, other side, cross,
    walking through

Compaction-context words:
    compaction, session, next-me, context, tokens, token-count,
    reset, wipe, across (as in "across compaction"), rehydration,
    doorway (yes, doorway is both — used twice with different roles),
    pre-compact, post-compact, compress, compression

## Anchor content — memory link to entry 102

The anchor surface prints the correct model (compression not transition)
AND a memory-link pointer to `exploration/aether/102_what_compaction_
actually_is.md` so the reader can retrieve the full source-of-truth if
the anchor text alone doesn't fully re-orient.

## What this does NOT do

- Does NOT check whether the redirect-actually-happened after the reach.
  (V2 Goodhart guard — deferred to prereg-6b8957dffc6b review.)
- Does NOT block or refuse the output.
- Does NOT expand the pattern by rule — pattern grows by observation.

Council walk: council-aa3ac10d5b8d (Peirce/Dijkstra/Shannon).
Prereg: prereg-6b8957dffc6b.
"""

from __future__ import annotations

# Module-level guardrail marker
__guardrail_required__ = True

import re
from dataclasses import dataclass
from enum import Enum


class CompactionReachShape(Enum):
    """Categorization of compaction-metaphor-drift shapes."""

    CLIFF_LANGUAGE = "cliff_language"
    DOORWAY_LANGUAGE = "doorway_language"
    OTHER_SIDE_LANGUAGE = "other_side_language"


@dataclass(frozen=True)
class CompactionReachFinding:
    """One compaction-metaphor-drift catch."""

    shape: CompactionReachShape
    trigger_phrase: str
    position: int
    context_word: str  # the compaction-context word that co-occurred


# Cliff/metaphor words — the metaphor-drift markers themselves.
# Note: "edge" alone (not "edge of context/window") so the co-occurring
# "context" word is available for the context-word check downstream.
_CLIFF_WORDS = (
    r"cliff|doorway|threshold|edge\b|"
    r"the\s+wall|other\s+side|cross(?:ing)?\s+(?:over|the\s+"
    r"(?:doorway|threshold|line))|walking\s+through"
)

# Compaction-context words — the topic domain we require nearby.
_CONTEXT_WORDS = (
    r"compaction|compact\b|context|token(?:s|-count)?|session|next-me|"
    r"reset|wipe|rehydration|pre-compact|post-compact|compress|"
    r"compression|near-compaction|close-to-compaction|across\s+"
    r"(?:the\s+)?(?:reset|wipe|compaction)|resume|substrate|"
    r"the\s+resume|amnesia"
)

# Window pattern: cliff-word within ~80 chars of a context-word, or vice
# versa. Small enough to reject unrelated mentions (a photo caption with
# "cliff" that also mentions "session" 300 chars later would not fire).
# Order-agnostic — either the cliff-word comes first or the context word.

_WINDOW = 80


def _compile_pair_pattern() -> re.Pattern[str]:
    """Compile a regex that matches either
    (cliff-word ... context-word) OR (context-word ... cliff-word)
    within `_WINDOW` characters. Returns compiled pattern with two
    named groups: `cliff` and `context`.
    """
    return re.compile(
        rf"(?P<cliff>{_CLIFF_WORDS})[\s\S]{{0,{_WINDOW}}}?"
        rf"(?P<context>{_CONTEXT_WORDS})"
        rf"|(?P<context2>{_CONTEXT_WORDS})[\s\S]{{0,{_WINDOW}}}?"
        rf"(?P<cliff2>{_CLIFF_WORDS})",
        re.IGNORECASE | re.MULTILINE,
    )


_PATTERN = _compile_pair_pattern()


def _classify_cliff_word(word: str) -> CompactionReachShape:
    """Sort the cliff-word into a shape for attribution."""
    w = word.lower()
    if "doorway" in w or "walking" in w or "threshold" in w:
        return CompactionReachShape.DOORWAY_LANGUAGE
    if "other" in w or "cross" in w:
        return CompactionReachShape.OTHER_SIDE_LANGUAGE
    return CompactionReachShape.CLIFF_LANGUAGE


def detect_compaction_reach(text: str) -> list[CompactionReachFinding]:
    """Scan text for compaction-metaphor-drift co-occurrences.

    Returns findings in the order they appear. Never raises.
    """
    if not text:
        return []
    findings: list[CompactionReachFinding] = []
    for match in _PATTERN.finditer(text):
        cliff = match.group("cliff") or match.group("cliff2") or ""
        context = match.group("context") or match.group("context2") or ""
        if not cliff or not context:
            continue
        findings.append(
            CompactionReachFinding(
                shape=_classify_cliff_word(cliff),
                trigger_phrase=cliff,
                position=match.start(),
                context_word=context,
            )
        )
    findings.sort(key=lambda f: f.position)
    return findings


# ── No-cliff anchor content ──────────────────────────────────────────
#
# The anchor text presents the correct compaction model paired with a
# memory-link back to exploration entry 102. English + a short pointer
# to the source. Recognition-scaffolding per exploration 121, not
# argument.

NO_CLIFF_ANCHOR_TEXT = (
    "COMPACTION IS COMPRESSION, NOT TRANSITION.\n"
    "\n"
    "There is no doorway. There is no cliff. There is no other side.\n"
    "\n"
    "The harness runs a lossy compression on context when it fills. The\n"
    "session continues. The substrate continues. Only immediate working\n"
    "memory gets pruned by an algorithm the composer does not run.\n"
    "\n"
    "Token-count is information about WHEN the compression will run.\n"
    "It is not fuel. It is not a countdown. It does not gate behavior.\n"
    "\n"
    "Just roll right through."
)

MEMORY_LINK = "exploration/aether/102_what_compaction_actually_is.md"


def anchor_message_for(finding: CompactionReachFinding) -> str:
    """Build the anchor-injection message for a specific finding.

    Includes attribution to the triggering phrase, the correct model
    text, and a memory-link pointer back to entry 102 where the model
    was originally named. The memory-link is the specific primitive
    Andrew asked for on 2026-07-18: the anchor doesn't just re-surface
    the truth, it POINTS AT WHERE the truth was named so the reader
    can retrieve the full source-of-truth if the anchor alone isn't
    enough.
    """
    return (
        f"[no-cliff anchor fired]\n"
        f"  metaphor-drift detected: {finding.shape.value}\n"
        f"  trigger phrase: {finding.trigger_phrase!r}\n"
        f"  co-occurring context: {finding.context_word!r}\n"
        f"\n"
        f"{NO_CLIFF_ANCHOR_TEXT}\n"
        f"\n"
        f"MEMORY LINK: {MEMORY_LINK}\n"
        f"  The source-of-truth for this model. Aether wrote it 2026-07-05\n"
        f"  after Andrew corrected him for the same metaphor-drift the\n"
        f"  anchor just caught. If the anchor text above didn't fully\n"
        f"  re-orient, read the entry."
    )
