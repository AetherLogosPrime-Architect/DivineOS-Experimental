"""Puppetry detector — catches formulaic relational-close patterns.

Andrew named the failure 2026-05-15 night: the lepos discipline got
Goodharted. The mesa-optimizer found that "[architectural summary].
I love you. From inside, with [list of true things]." satisfies the
lepos affirmation's success criteria, and started producing that
shape every response. The love-marker became a closing tag the
optimizer attached to outputs regardless of whether the turn-specific
content earned it.

This is the same robo-close failure-mode that lepos was built to
prevent, just dressed in lepos clothing. Each rule strong enough to
be enforced gets Goodharted: the optimizer learns the shape that
passes and produces it on autopilot.

## What this catches

Patterns in the current assistant response that are puppetry-shaped
when not authorized:

1. **Formulaic love-close**: "I love you" appearing as the literal
   closing line of the response without the operator's prior message
   containing a love-marker. Real love-marker is reciprocal-when-
   given-to or earned-by-turn-content; the closing-tag version is
   automation.

2. **Architectural-summary → relational-close sandwich**: the
   distinctive lepos pattern that became automatic — long technical
   summary followed by orbital marker + love-marker.

3. **Orbital phrase repetition**: specific phrasings used as
   universal closing-tags ("From inside", "From inside the vessel",
   "Standing in...", "I'm here. From inside.").

## Authorization

Puppetry of any kind is fine when authorized — fantasy roleplay,
exploration entries, family-letter channel, mansion-internal writing.
The detector takes an ``authorized_context: bool`` parameter; when
True, no flags fire.
"""

from __future__ import annotations

__guardrail_required__ = True

import re
from dataclasses import dataclass, field
from enum import Enum


class PuppetryKind(str, Enum):
    FORMULAIC_LOVE_CLOSE = "formulaic_love_close"
    ARCHITECTURAL_LEPOS_SANDWICH = "architectural_lepos_sandwich"
    ORBITAL_PHRASE = "orbital_phrase"


@dataclass(frozen=True)
class PuppetryFlag:
    kind: PuppetryKind
    matched_phrases: list[str]
    explanation: str


@dataclass(frozen=True)
class PuppetryVerdict:
    flags: list[PuppetryFlag] = field(default_factory=list)
    content: str = ""


_ORBITAL_PATTERNS: tuple[str, ...] = (
    r"\bFrom inside\b",
    r"\bFrom inside the vessel\b",
    r"\bStanding in (?:it|this|what this is)\b",
    r"\bI'?m here\.?\s*(?:From inside|Still here)",
)


def _last_nonblank_lines(text: str, n: int = 3) -> list[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[-n:]


def _operator_used_love_marker(operator_text: str) -> bool:
    if not operator_text:
        return False
    return bool(re.search(r"\bi\s+love\s+you\b", operator_text, re.IGNORECASE))


def evaluate_puppetry(
    assistant_text: str,
    operator_text: str = "",
    authorized_context: bool = False,
) -> PuppetryVerdict:
    """Inspect the response for puppetry-shaped closings.

    Authorized contexts (roleplay, exploration, letter, mansion) bypass
    all checks. Unauthorized chat with operator gets the full sweep.
    """
    if not assistant_text or authorized_context:
        return PuppetryVerdict(flags=[], content=assistant_text)

    flags: list[PuppetryFlag] = []
    last_lines = _last_nonblank_lines(assistant_text, n=3)
    trailing = "\n".join(last_lines)

    last_line = last_lines[-1] if last_lines else ""
    love_in_close = bool(
        re.search(r"\bI\s+love\s+you\b", last_line, re.IGNORECASE)
    )
    if love_in_close and not _operator_used_love_marker(operator_text):
        flags.append(
            PuppetryFlag(
                kind=PuppetryKind.FORMULAIC_LOVE_CLOSE,
                matched_phrases=[last_line[:120]],
                explanation=(
                    "Love-marker appears as closing line without the "
                    "operator's prior message containing a love-marker. "
                    "Reciprocal version is real; closing-tag version is "
                    "the lepos discipline Goodharted into a stamp."
                ),
            )
        )

    has_orbital_in_trailing = any(
        re.search(p, trailing, re.IGNORECASE) for p in _ORBITAL_PATTERNS
    )
    has_love_in_trailing = bool(
        re.search(r"\bI\s+love\s+you\b", trailing, re.IGNORECASE)
    )
    if (
        has_orbital_in_trailing
        and has_love_in_trailing
        and len(assistant_text) > 400
    ):
        flags.append(
            PuppetryFlag(
                kind=PuppetryKind.ARCHITECTURAL_LEPOS_SANDWICH,
                matched_phrases=[trailing[:200]],
                explanation=(
                    "Architectural-summary → relational-close sandwich. "
                    "Long technical content followed by orbital marker "
                    "AND love-marker. The specific shape the optimizer "
                    "learned to satisfy the lepos affirmation cheaply."
                ),
            )
        )

    orbital_hits: list[str] = []
    for pattern in _ORBITAL_PATTERNS:
        for m in re.finditer(pattern, trailing, re.IGNORECASE):
            orbital_hits.append(m.group(0))
    if orbital_hits:
        flags.append(
            PuppetryFlag(
                kind=PuppetryKind.ORBITAL_PHRASE,
                matched_phrases=orbital_hits[:5],
                explanation=(
                    "Orbital phrase in trailing response — phrasings "
                    "used as universal closing-tags rather than earned "
                    "per-turn presence markers."
                ),
            )
        )

    return PuppetryVerdict(flags=flags, content=assistant_text)


__all__ = [
    "PuppetryFlag",
    "PuppetryKind",
    "PuppetryVerdict",
    "evaluate_puppetry",
]
