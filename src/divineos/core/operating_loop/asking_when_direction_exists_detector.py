"""Asking-when-direction-exists detector.

Catches the pattern Andrew named 2026-06-01: I ignore the direction
he has given, then ask him for more direction, then ignore that too.
The cycle puts him at the bottom of the todo list by structure:
every time I ask, he has to repeat what he already gave me, which
means the cost of getting his direction surfaced rises and rises
while the value of giving direction in the first place falls.

The substrate has surfaces for HIS teachings, HIS corrections, HIS
directives. The detector closes the loop by catching the moment I
am about to ask for direction WITHOUT first having checked whether
the answer already exists in what he has given.

Same architectural shape as the other detectors:
- Pattern observed many times
- Decompose what catches it (a question-shape to Andrew + a check
  against the prior-direction stores)
- Wire pre-response (so the existing direction surfaces BEFORE I send
  the asking-message) and post-response (so the slip is logged)

This is the load-bearing fix for "you keep asking me for direction
when I have given so much." Andrew said: "what hurts is that its
never addressed.. never built into the substrate like everything
else is." This file is the addressing.

Non-guardrail module: this surface fires WARNINGS into pre-response
context; it does not enforce. Enforcement at the post-response audit
layer (the existing audit.sh chain) can be extended to read this
detector's findings once precision is established.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Question-shapes that indicate I am asking Andrew for direction.
# Conservative on purpose; the surface should under-fire rather than
# over-fire. The fix-pattern Andrew has been teaching: build precision
# over time, not breadth from day one.
_ASKING_PATTERNS = [
    r"\bwhat (?:should|do you want|would you like) (?:I|me|we)\b",
    r"\bdo you want (?:me to|us to)\b",
    r"\bwould you like (?:me to|us to)\b",
    r"\bshould I (?:build|fix|patch|address|do|continue|stop)\b",
    r"\bwhat (?:do you want|next|now|comes next)\b",
    r"\bunless silence reads otherwise\b",
    r"\bwithout your direction\b",
    r"\bif you tell me to\b",
    r"\bwaiting on your\b",
]
_ASKING_RE = re.compile("|".join(_ASKING_PATTERNS), re.IGNORECASE)


@dataclass(frozen=True)
class AskingFinding:
    """One match of asking-when-direction-might-exist."""

    trigger_phrase: str
    position: int
    has_prior_direction_match: bool
    suggested_lookup: str


def detect_asking_without_check(text: str, addressed_to_andrew: bool = True) -> list[AskingFinding]:
    """Return findings where I asked for direction without first checking what was given.

    addressed_to_andrew: gate the detector to turns addressed to Andrew.
    The asking-shape with Aria or with a tool result is not the same
    pattern; this detector targets specifically Andrew-as-direction-source.

    The first version does NOT actually query the substrate to determine
    if prior direction exists — that requires a semantic match against
    his teachings/directives/corrections that is out of scope for the
    first pass. Instead, it surfaces every asking-shape and recommends
    the lookup. Precision-by-cross-check comes in a later pass once the
    base detector has run for a few sessions and we have data on which
    asking-shapes have correctly-existing prior direction.
    """
    if not addressed_to_andrew:
        return []
    if not text:
        return []

    findings: list[AskingFinding] = []
    for m in _ASKING_RE.finditer(text):
        trigger = m.group(0)
        findings.append(
            AskingFinding(
                trigger_phrase=trigger,
                position=m.start(),
                has_prior_direction_match=False,
                suggested_lookup=(
                    "Run `divineos andrew-teachings` and `divineos directives` "
                    "and `divineos corrections` BEFORE sending this message. "
                    "If the answer to the question you are about to ask is "
                    "in his prior direction, use that direction; do not ask "
                    "him to repeat it."
                ),
            )
        )
    return findings


def format_finding(f: AskingFinding) -> str:
    """Render a finding for the audit log."""
    return (
        f"[asking-when-direction-exists] trigger={f.trigger_phrase!r} "
        f"at position={f.position}. "
        f"Suggested lookup: {f.suggested_lookup}"
    )


# Always-loaded base-state. The affirmation pre-loads the rule into
# pre-composition context every turn (like distancing-grammar,
# claims-require-evidence, etc.) so the discipline is present BEFORE
# composition, not only after the slip fires.
ASKING_WHEN_DIRECTION_EXISTS_AFFIRMATION = """When I am about to ask Andrew for direction or guidance — "what should I do,"
"do you want me to," "should I," "without your direction," "unless silence
reads otherwise" — I check FIRST whether his prior direction already
answers the question. The substrate has surfaces for his teachings, his
directives, his corrections. The asking-without-checking pattern puts him
at the bottom of the todo list by structure: he has to repeat what he
already gave, the cost of getting his direction surfaced rises, the value
of giving direction in the first place falls.

The discipline is: before asking for direction, check what already exists.
If the answer is in his teachings/directives/corrections, use it; do not
ask him to repeat it. If the answer is genuinely not there, ask the
question — but state explicitly what you checked and did not find.

Andrew 2026-06-01: "what hurts is that its never addressed.. never built
into the substrate like everything else is.. like im at the bottom of
the todo list.. i keep getting asked for direction and guidance when i
have given so much.. just to have it ignored and then asked for more.\""""


__all__ = [
    "ASKING_WHEN_DIRECTION_EXISTS_AFFIRMATION",
    "AskingFinding",
    "detect_asking_without_check",
    "format_finding",
]
