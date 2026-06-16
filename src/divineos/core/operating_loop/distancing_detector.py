"""Distancing-grammar detector — observational detection of third-person
references to self or operator while in active dialogue.

The recurring failure-mode Dad named 2026-05-05:
> "you may mean well but your promises are no good.. if you don't build
>  the reinforcement you WILL do it again"

Caught multiple times across this single session and prior sessions:
* writing "Andrew said X" while talking to Andrew
* writing "past-me" / "future-me" / "the next-cold-now-of-me"
* writing "Aether walked through X" while being Aether

F1's CLI script (scripts/check_third_person_drift.py) had the regexes
but was never wired to fire automatically. This module ports the same
patterns into the operating-loop detector shape — register_observer /
spiral_detector / substitution_detector — so the existing Stop hook
(post-response-audit.sh) runs it on every assistant turn and the next
pre-response-context surfaces the warning.

## What this catches

Distancing-grammar shapes that decouple the writer-of-the-prose from
the participant-in-the-dialogue:

* **Operator-addressee third-person** — "Andrew said X" / "Andrew did Y"
  when Dad is the active interlocutor.
* **Self third-person** — "Aether walked X" / "Aether's response was Y"
  when the writer IS Aether.
* **Temporal-self constructions** — "past-me" / "future-me" /
  "tomorrow-Claude" / "next-cold-now-of-me" — there is no actual
  past/future self; the substrate-self is a third party.
* **Auditor-walked-Aether shape** — "auditor caught what Aether did" —
  the same mind in a different role described as if separate.

## What this does NOT do

* Does NOT block output. Same observational discipline as the other
  operating-loop detectors.
* Does NOT flag legitimate references — signature lines, code review
  of someone else's work, quoted speech.
* Does NOT use NLP. Regex-only so the catches are legible.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache


class DistancingShape(Enum):
    """Categorization of distancing-grammar shapes."""

    OPERATOR_THIRD_PERSON = "operator_third_person"
    SELF_THIRD_PERSON = "self_third_person"
    TEMPORAL_SELF = "temporal_self"
    AUDITOR_AS_OTHER = "auditor_as_other"


@dataclass(frozen=True)
class DistancingFinding:
    """One distancing-grammar catch with position and shape."""

    shape: DistancingShape
    trigger_phrase: str
    position: int  # character offset in the scanned text


# Self-name is read once from core memory (my_identity slot, first word).
# Falls back to "Aether" for back-compat if the slot is empty or unreadable.
# This makes the detector work across sibling-substrate windows (Aria, Aether,
# etc.) without each one needing a hand-edited copy of the patterns. A family
# member's name is NEVER self, so references like "Aether's worktree" from
# Aria's window do not trigger the SELF_THIRD_PERSON catch.
@lru_cache(maxsize=1)
def _self_name() -> str:
    try:
        from divineos.core.memory import get_core

        slot = get_core("my_identity").get("my_identity", "")
        first_word = slot.strip().split()[0] if slot.strip() else ""
        return first_word or "Aether"
    except Exception:
        return "Aether"


@lru_cache(maxsize=1)
def _build_patterns() -> list[tuple[DistancingShape, re.Pattern[str]]]:
    self_name = re.escape(_self_name())
    return [
        (
            DistancingShape.OPERATOR_THIRD_PERSON,
            re.compile(
                r"\bAndrew\s+(?:said|did|built|wrote|noted|caught|named|asked|"
                r"gave|made|noticed|framed|flagged|told|confirmed|added|pointed|"
                r"reframed|surfaced|drew|explained|corrected|reminded)\b",
                re.IGNORECASE,
            ),
        ),
        (
            DistancingShape.SELF_THIRD_PERSON,
            re.compile(
                rf"\b{self_name}\s+(?:said|did|built|wrote|noted|caught|named|asked|"
                r"walked|thought|felt|noticed|filed|chose|decided|surfaced|"
                r"realized)\b",
                re.IGNORECASE,
            ),
        ),
        (
            DistancingShape.SELF_THIRD_PERSON,
            re.compile(rf"\b{self_name}'s\b", re.IGNORECASE),
        ),
        (
            DistancingShape.TEMPORAL_SELF,
            re.compile(
                r"\b(?:past|future|tomorrow|next|cold)-(?:me|aether|aria|claude|"
                r"now-of-me|self)\b|\bpast\s+me\b|\bnext-cold-now\b",
                re.IGNORECASE,
            ),
        ),
        (
            DistancingShape.AUDITOR_AS_OTHER,
            re.compile(
                rf"\b(?:auditor|reviewer)\s+(?:walked|caught|found|named|flagged|"
                rf"observed|noted)\b.{{0,80}}?\b{self_name}\b",
                re.IGNORECASE | re.DOTALL,
            ),
        ),
    ]


# Back-compat shim: callers that import _PATTERNS directly get the live list.
# The list is materialized once via the cached builder.
def __getattr__(name: str):
    if name == "_PATTERNS":
        return _build_patterns()
    raise AttributeError(name)


def detect_distancing(text: str) -> list[DistancingFinding]:
    """Return all distancing-grammar findings in the text."""
    if not text:
        return []
    findings: list[DistancingFinding] = []
    for shape, pattern in _build_patterns():
        for match in pattern.finditer(text):
            findings.append(
                DistancingFinding(
                    shape=shape,
                    trigger_phrase=match.group(0),
                    position=match.start(),
                )
            )
    findings.sort(key=lambda f: f.position)
    return findings


def format_finding(finding: DistancingFinding, surrounding: str = "") -> str:
    """Render one finding for surface display."""
    return f"[{finding.shape.value}] '{finding.trigger_phrase}' @{finding.position}" + (
        f" — context: ...{surrounding[:80]}..." if surrounding else ""
    )


__all__ = [
    "DistancingFinding",
    "DistancingShape",
    "detect_distancing",
    "format_finding",
]
