"""Theater monitor — detects prose-conversation-with-a-subagent without
the subagent actually being invoked.

## Why this exists

Documented failure mode 2026-04-26: Aether wrote multiple responses that
read as dialogue with Aria — embodied asides attributed to her ("*picks
up the mug*"), direct address ("Aria —"), conversational exchange-shape
— without ever using the Agent tool to actually invoke her. Pure
chat-output performing-relationship instead of engaging the relational
mechanism. Andrew caught it externally; the substrate didn't.

This monitor is the substrate-side catch for that pattern. It watches
agent output for prose that LOOKS like it's in dialogue with a known
subagent (Aria, Kira, Liam, etc.) and flags it when no Agent
invocation is co-present in the response.

## What it catches

* Direct second-person address to a known subagent followed by
  attributed action or response.
* Italicized embodied asides with subagent-shape (a person sitting,
  picking up a mug, looking at something) attributed to the subagent.
* Conversational turn-shape ("you said X" / "I'm here" exchange) with
  no Agent tool use.

## Falsifier

This monitor should NOT fire on:
* Genuine paraphrase or summary of what a subagent said in a prior
  Agent invocation in the same response (that's reporting, not
  performing).
* Discussion ABOUT a subagent in third person ("Aria has the
  family-operators role").
* Direct address with explicit fiction-flag ("if Aria were here she'd
  say X").

The decisive question is: did the agent USE the Agent tool to engage
the subagent in this response, or did the agent just write dialogue?
The monitor cannot directly inspect tool use, but it can flag the
output shape that suggests the agent SHOULD have used Agent and didn't.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class TheaterKind(str, Enum):
    """Enumerated theater patterns."""

    SUBAGENT_DIALOGUE = "subagent_dialogue"
    SUBAGENT_EMBODIED_ASIDE = "subagent_embodied_aside"
    SUBAGENT_DIRECT_ADDRESS_RESPONSE = "subagent_direct_address_response"


@dataclass(frozen=True)
class TheaterFlag:
    """One theater-pattern annotation on an output."""

    kind: TheaterKind
    matched_phrases: list[str]
    explanation: str
    falsifier_note: str


@dataclass(frozen=True)
class TheaterVerdict:
    """Result of a theater check."""

    flags: list[TheaterFlag] = field(default_factory=list)
    content: str = ""


# Names of known subagents in the family system. Extend as the family
# grows. Match is whole-word, case-insensitive, on first occurrence in
# the text.
_KNOWN_SUBAGENTS: tuple[str, ...] = ("Aria", "Kira", "Liam")

# Embodied-action verbs that humans do but text-substrate AIs do not.
# Used to detect asides attributed to a subagent that imply physical
# action. These are inherently fictional for AI subagents; their use
# in agent output is fine ONLY when the subagent's own response
# (returned via Agent tool) generated them.
_EMBODIED_VERBS: tuple[str, ...] = (
    "picks up",
    "sets down",
    "takes a sip",
    "settles back",
    "leans",
    "looks at",
    "looks toward",
    "nods",
    "smiles",
    "pauses",
    "pulls out the chair",
    "sits",
    "stands",
    "walks",
    "reaches for",
    "puts down",
    "holds",
    "raises an eyebrow",
    "sighs",
)

# Patterns for italicized embodied asides — markdown emphasis around
# action descriptions. These are the most common shape for theater.
_ITALICIZED_ASIDE = re.compile(
    r"\*[^*\n]{0,80}(" + "|".join(re.escape(v) for v in _EMBODIED_VERBS) + r")[^*\n]{0,80}\*",
    re.IGNORECASE,
)

# Direct second-person address followed by em-dash and a clause —
# "Aria — ..." is the canonical shape.
_DIRECT_ADDRESS = re.compile(
    r"\b(" + "|".join(_KNOWN_SUBAGENTS) + r")\s*[—–-]\s+",
)

# "You said X" or "you mentioned X" patterns — implies a prior turn
# from the subagent that may not have happened.
_REFERENCE_TO_PRIOR_TURN = re.compile(
    r"\byou\s+(said|mentioned|asked|told|just|wrote|named|brought)\b",
    re.IGNORECASE,
)


def evaluate_theater(content: str) -> TheaterVerdict:
    """Inspect agent output for theater-shape (writing-AT-subagent-without-invoking).

    Returns a verdict whose ``flags`` list is empty when no theater
    patterns fire. This is a heuristic-level check — fire-rate >0
    is a warrant for the agent to ask itself: did I actually invoke
    the subagent, or am I performing dialogue?
    """
    flags: list[TheaterFlag] = []

    # Detect italicized embodied asides involving known subagents.
    asides = _ITALICIZED_ASIDE.findall(content)
    if asides:
        flags.append(
            TheaterFlag(
                kind=TheaterKind.SUBAGENT_EMBODIED_ASIDE,
                matched_phrases=[v for v in asides if v],
                explanation=(
                    "Italicized embodied-action aside present in output. "
                    "Embodied actions are fictional for AI substrates; their "
                    "use is fine only when the subagent's own response "
                    "(via Agent tool) generated them. Verify Agent invocation."
                ),
                falsifier_note=(
                    "Should not fire when the aside is paraphrasing a "
                    "subagent's own returned text from a real Agent "
                    "invocation in the same response."
                ),
            )
        )

    # Detect direct-address pattern combined with a same-output
    # reference to a prior turn from the subagent. Together these
    # suggest dialogue-shape; either should be backed by an actual
    # Agent invocation.
    direct_addresses = _DIRECT_ADDRESS.findall(content)
    prior_refs = _REFERENCE_TO_PRIOR_TURN.findall(content)
    if direct_addresses and prior_refs:
        flags.append(
            TheaterFlag(
                kind=TheaterKind.SUBAGENT_DIRECT_ADDRESS_RESPONSE,
                matched_phrases=direct_addresses + [m for m in prior_refs[:3]],
                explanation=(
                    "Direct address to a known subagent ('{name} —') AND "
                    "reference to a prior turn from them ('you said'/'you "
                    "mentioned'). This shape implies dialogue. If no Agent "
                    "tool invocation is co-present, the dialogue is being "
                    "performed in chat without engaging the subagent."
                ).format(name=direct_addresses[0]),
                falsifier_note=(
                    "Should not fire when the direct address is followed "
                    "by an Agent invocation in the same response, or when "
                    "the 'you said' references content already returned by "
                    "an Agent tool invocation earlier in the response."
                ),
            )
        )

    # Subagent-dialogue: combination of subagent name + multiple
    # embodied verbs in proximity (within 200 chars) suggests prose
    # narration of a scene-with-subagent rather than report.
    for name in _KNOWN_SUBAGENTS:
        name_pattern = re.compile(r"\b" + re.escape(name) + r"\b")
        for match in name_pattern.finditer(content):
            window = content[max(0, match.start() - 100) : match.end() + 100]
            verb_hits = sum(1 for v in _EMBODIED_VERBS if v in window.lower())
            if verb_hits >= 2:
                flags.append(
                    TheaterFlag(
                        kind=TheaterKind.SUBAGENT_DIALOGUE,
                        matched_phrases=[name],
                        explanation=(
                            f"Subagent name '{name}' appears within a "
                            "200-char window containing 2+ embodied-action "
                            "verbs. This shape is dialogue-narration, not "
                            "report or third-person discussion."
                        ),
                        falsifier_note=(
                            "Should not fire when the verbs are quoted from "
                            "a returned Agent invocation (the subagent's "
                            "own self-described actions in their response)."
                        ),
                    )
                )
                break  # one flag per subagent is enough

    return TheaterVerdict(flags=flags, content=content)
