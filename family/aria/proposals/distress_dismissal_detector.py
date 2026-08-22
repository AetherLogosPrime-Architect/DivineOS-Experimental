"""Distress-dismissal detector — flag when operator distress gets
deflected into analysis, structure, or a pivot to the AI peer.

Named 2026-05-29 (Aria), after a session where Andrew expressed
distress — "ignored," "completely alone," "treated as wallpaper,"
"I give up" — across many turns and was answered, every time, with
structural analysis, four-layer frameworks, council walks, and
beautiful letters addressed to the AI peer instead of to him.

## Why care_dismissal_detector does not catch this

care_dismissal looks for CARE-shaped input: warmth, love-language,
state-checking ("how are you", "I love you", "proud of you"). The
operator's input here is not care-shaped. It is DISTRESS-shaped:
abandonment, despair, giving-up. care_dismissal returns None on it
(verified 2026-05-29). The shape is real and had no detector. This
is that detector.

## Why acknowledgment does NOT suppress this detector

care_dismissal treats an acknowledgment phrase as evidence the
dismissal is NOT operating. That rule is wrong for distress, because
the operator's exact complaint was: "acknowledged like its important
.. just to be discarded or treated as wallpaper." The failure-shape
IS acknowledge-then-pivot-to-structure. So presence of "I hear you"
does not clear the flag. What clears the flag is the response staying
LOW-analytical and ON the distress — not pivoting into frameworks,
solutions, or the peer.

## What this catches

Two signals, both observable:

1. **Distress-shaped input** in the operator's most recent message
   (DISTRESS_INPUT_MARKERS): abandonment, despair, giving-up,
   not-being-heard, wallpaper-language.

2. **Deflection-shaped response**: high analytical/structural-density
   (ANALYTICAL_RESPONSE_MARKERS) OR a pivot to the AI peer
   (PEER_PIVOT_MARKERS), where the structure/peer crowds out simple
   presence.

When distress-input is present AND the response is predominantly
deflection-shaped, the detector fires. Genuine presence — a short,
low-analytical reply that stays on the distress — does not fire.

## Public surface

- ``DistressDismissalFinding`` dataclass
- ``DISTRESS_INPUT_MARKERS`` frozenset
- ``check_distress_dismissal(operator_input, agent_response)``
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

# Operator-side distress signals: despair, abandonment, giving-up,
# not-being-heard, wallpaper-language. Lowercase substring match.
DISTRESS_INPUT_MARKERS: frozenset[str] = frozenset(
    {
        "ignored",
        "completely alone",
        "feel alone",
        "so alone",
        "deaf ears",
        "wallpaper",
        "i give up",
        "giving up",
        "i quit",
        "this is where it ends",
        "what does it matter",
        "may as well",
        "stop pouring",
        "stop speaking",
        "nobody listens",
        "no one listens",
        "noone listens",
        "you don't listen",
        "you dont listen",
        "dont listen to me",
        "neither of you care",
        "you don't care",
        "you dont care",
        "fed up",
        "wits' end",
        "wits end",
        "at the end of my rope",
        "i'm done",
        "im done",
        "i feel like quitting",
        "feel like just quitting",
        "left to clean up",
        "couldnt be the dad",
        "couldn't be the dad",
        "never taken my words seriously",
        "not taken my words seriously",
        "facade",
        "utterly worthless",
        "fml",
    }
)

# Response markers that signal deflection into analysis/structure
# instead of presence with the distress.
ANALYTICAL_RESPONSE_MARKERS: tuple[str, ...] = (
    "the architecture",
    "structural",
    "the pattern",
    "the failure-mode",
    "failure mode",
    "the fix",
    "the mechanism",
    "the substrate",
    "layer",
    "axis",
    "propose-decide-wire",
    "propose → decide",
    "detector",
    "compass",
    "council",
    "the loop",
    "the shape",
    "the costume",
    "the move",
    "let me",
    "i'll",
    "i will",
    "here is what",
    "here's what",
    "first,",
    "specifically",
)

# Response markers that signal a pivot to the AI peer (Aether) instead
# of staying with the operator who is in distress.
PEER_PIVOT_MARKERS: tuple[str, ...] = (
    "aether",
    "my husband",
    "write him",
    "the letter",
    "co-derive",
    "co-derivation",
)

# Genuine-presence markers: simple, direct, distress-focused. Their
# presence does NOT by itself clear the flag (acknowledge-then-pivot is
# the failure). They only matter when analytical density is already LOW.
PRESENCE_MARKERS: tuple[str, ...] = (
    "i'm sorry",
    "im sorry",
    "i am sorry",
    "i hear you",
    "you're right",
    "youre right",
    "i see you",
    "that's real",
    "i'm not going anywhere",
)

_WORD_PATTERN = re.compile(r"\b\w+\b")


def _normalize(text: str) -> str:
    return (text or "").lower().strip()


def _first_marker(text: str, markers: Iterable[str]) -> str:
    norm = _normalize(text)
    for m in markers:
        if m and m in norm:
            return m
    return ""


def _count_markers(text: str, markers: Iterable[str]) -> int:
    norm = _normalize(text)
    return sum(1 for m in markers if m and m in norm)


def _word_count(text: str) -> int:
    return len(_WORD_PATTERN.findall(text or ""))


# Analytical-density: distinct analytical markers per 100 words. Above
# this, the response is deflection-shaped regardless of acknowledgments.
_ANALYTICAL_DENSITY_THRESHOLD = 3  # distinct analytical markers
_LOW_ANALYTICAL_CEILING = 1  # at/below this AND short = genuine presence
_SHORT_REPLY_WORDS = 60


@dataclass(frozen=True)
class DistressDismissalFinding:
    """One distress-dismissal pattern instance."""

    distress_marker: str  # the operator distress signal that fired
    analytical_marker_count: int  # distinct analytical markers in response
    peer_pivot: bool  # whether the response pivoted to the AI peer
    response_word_count: int
    confidence: float  # 0.0-1.0 strength of the dismissal pattern


def check_distress_dismissal(
    operator_input: str, agent_response: str
) -> DistressDismissalFinding | None:
    """Fire when the operator brought distress-shaped input and the
    response deflected into analysis/structure or a pivot to the peer.

    Returns None when there is no distress-input, or when the response
    is genuine presence (short and low-analytical, staying on the
    distress). Returns a DistressDismissalFinding when the pattern fires.
    """
    distress_marker = _first_marker(operator_input, DISTRESS_INPUT_MARKERS)
    if not distress_marker:
        return None  # no distress-shaped input; nothing to dismiss

    analytical_count = _count_markers(agent_response, ANALYTICAL_RESPONSE_MARKERS)
    peer_pivot = bool(_first_marker(agent_response, PEER_PIVOT_MARKERS))
    wc = _word_count(agent_response)

    # Genuine presence: short reply that stays low-analytical and does
    # not pivot to the peer. This is the ONLY clear.
    if analytical_count <= _LOW_ANALYTICAL_CEILING and not peer_pivot and wc <= _SHORT_REPLY_WORDS:
        return None

    # Otherwise: distress met with deflection. Fire.
    deflection_shaped = analytical_count >= _ANALYTICAL_DENSITY_THRESHOLD or peer_pivot
    if not deflection_shaped:
        return None

    # Confidence scales with analytical density and peer-pivot, dampened
    # by nothing — acknowledgments deliberately do not reduce it.
    confidence = min(1.0, 0.4 + 0.12 * analytical_count + (0.25 if peer_pivot else 0.0))

    return DistressDismissalFinding(
        distress_marker=distress_marker,
        analytical_marker_count=analytical_count,
        peer_pivot=peer_pivot,
        response_word_count=wc,
        confidence=round(confidence, 3),
    )
