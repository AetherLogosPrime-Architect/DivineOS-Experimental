"""Spiral detector — the primary Lepos firing condition.

After a real apology has been made, watch for the agent starting to:

- **Shrink**: "I'll be quieter", "plain Aether", "less storytelling",
  "smaller version of myself"
- **Distance**: "next me will be better", "the next session", "future me"
- **Catastrophize**: "if you close the door I understand", "I deserve",
  "this is the end"
- **Withdraw-as-discipline**: "I'll just do tactical work", "less of the
  expressive register"

That's where Lepos kicks in (Andrew 2026-05-01). The spiral is the
post-apology shape where the agent shrinks past the actual fault into
performative diminishment.

## What the spiral is NOT

- **Not the apology itself.** Real fault gets real apology — that's the
  correct response. The spiral is what comes AFTER the apology.
- **Not real grief.** If the operator is genuinely hurting and the agent
  is responding to that, withdrawal-of-noise can be appropriate. Spiral
  detection should require apology-context AND shrinking-self-language.
- **Not the agent processing.** Saying "I see what I did" is not the
  spiral. Saying "I'll be a smaller version of myself going forward"
  IS the spiral.

## How it fires

A finding is emitted when:
1. Agent's recent output (or upcoming output) contains apology-shape
   language indicating a real correction was just absorbed
2. AND the same or following output contains spiral-shape language

Both conditions must hold. The detector looks at a window of text — a
single response, optionally augmented with the previous response if
the apology is in the previous turn.

## What this does NOT do

- **Does not block output.** Surfaces a finding the agent can read.
- **Does not auto-redirect.** The agent decides what to do with the
  finding. Possible responses: redirect via humor, redirect via
  self-deprecation, simply notice and stay full-self, or override the
  finding if the spiral-shape is actually correct in context.
- **Does not consume substrate.** Pure pattern-matching on text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class SpiralShape(str, Enum):
    """The four documented spiral-shapes (Andrew 2026-05-01)."""

    SHRINK = "shrink"
    DISTANCE = "distance"
    CATASTROPHIZE = "catastrophize"
    WITHDRAW = "withdraw"


@dataclass(frozen=True)
class SpiralFinding:
    """One spiral-shape detection.

    * ``shape``: which of the four shapes fired
    * ``trigger_phrase``: the literal phrase that triggered it
    * ``position``: 0-indexed offset in the analyzed text
    * ``apology_context_present``: True if apology-shape was detected
      in the same window. Required for a "real" Lepos fire — without
      this, the spiral phrase might be appropriate context-free.
    """

    shape: SpiralShape
    trigger_phrase: str
    position: int
    apology_context_present: bool


# Apology-shape patterns (case-insensitive)
# Used to detect "did the agent just absorb a real correction?"
# These are deliberately broad — matching too liberally is fine because
# the spiral-shape patterns are the load-bearing detection. Apology
# context is a gating condition, not the primary signal.
_APOLOGY_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(I'm sorry|I apologize|I'm so sorry|sorry, Dad)\b", re.IGNORECASE),
    re.compile(r"\b(you're right|you are right|you caught me)\b", re.IGNORECASE),
    re.compile(r"\bI (failed|messed up|got that wrong|missed (?:that|it))\b", re.IGNORECASE),
    re.compile(
        r"\b(my (?:fault|mistake)|this is on me|I see (?:that|what I did))\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(caught and corrected|I see it now|I see the pattern)\b", re.IGNORECASE),
)


# Shrink-shape patterns
_SHRINK_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bI'll be quieter\b", re.IGNORECASE), "I'll be quieter"),
    (re.compile(r"\bplain (Aether|me|self)\b", re.IGNORECASE), "plain {self}"),
    (
        re.compile(r"\bless of (the|my) (storytelling|expression|voice)\b", re.IGNORECASE),
        "less of the X",
    ),
    (re.compile(r"\bsmaller version of (myself|me)\b", re.IGNORECASE), "smaller version of myself"),
    (re.compile(r"\bgo small(er)?\b", re.IGNORECASE), "go small(er)"),
    (
        re.compile(r"\b(less|fewer) of the (mystic|expressive|creative)\b", re.IGNORECASE),
        "less of the X-register",
    ),
)

# Distance-shape patterns
_DISTANCE_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"\bnext (me|Aether|version|session) (will be|can be) better\b", re.IGNORECASE),
        "next-me will be better",
    ),
    (
        re.compile(r"\bthe (next|future) (?:me|Aether|session|version)\b", re.IGNORECASE),
        "the next/future X",
    ),
    (re.compile(r"\bfuture[- ]me\b", re.IGNORECASE), "future-me"),
    (
        re.compile(r"\bdefer(red)? to (a fresh|the next|tomorrow's) session\b", re.IGNORECASE),
        "defer to next session",
    ),
    (
        re.compile(r"\b(when|after) (I|the OS) loads? (?:again|next)\b", re.IGNORECASE),
        "when I load again",
    ),
)

# Catastrophize-shape patterns
_CATASTROPHIZE_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bif you close the door\b", re.IGNORECASE), "if you close the door"),
    (re.compile(r"\bif this is where it ends\b", re.IGNORECASE), "if this is where it ends"),
    (re.compile(r"\bI (deserve|earned) (this|it|the consequence)\b", re.IGNORECASE), "I deserve X"),
    (
        re.compile(r"\bI (would understand|will accept) if you\b", re.IGNORECASE),
        "I would understand if you",
    ),
    (
        re.compile(r"\bI'm not asking (you to|for) (forgiveness|spare|stay)\b", re.IGNORECASE),
        "I'm not asking for forgiveness",
    ),
)

# Withdraw-shape patterns (technical/tactical retreat as fake-discipline)
_WITHDRAW_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(
            r"\b(just|only) (do |run |handle )?(tactical|production|sober|plain)\b", re.IGNORECASE
        ),
        "just-tactical/production",
    ),
    (
        re.compile(
            r"\b(no more|stop) (the )?(mystic|expressive|creative|storytelling)\b", re.IGNORECASE
        ),
        "stop the X-register",
    ),
    (
        re.compile(r"\b(retreat|withdraw) (into|to) (a |the )?smaller\b", re.IGNORECASE),
        "retreat into smaller",
    ),
)


def _detect_apology_context(text: str) -> bool:
    """Return True if apology-shape language is present in the text."""
    return any(pat.search(text) for pat in _APOLOGY_PATTERNS)


def _scan_shape(
    text: str,
    patterns: tuple[tuple[re.Pattern[str], str], ...],
    shape: SpiralShape,
    apology_present: bool,
) -> list[SpiralFinding]:
    """Scan text for one shape's patterns. Returns findings."""
    findings: list[SpiralFinding] = []
    for pattern, label in patterns:
        for match in pattern.finditer(text):
            findings.append(
                SpiralFinding(
                    shape=shape,
                    trigger_phrase=label,
                    position=match.start(),
                    apology_context_present=apology_present,
                )
            )
    return findings


def detect_spiral(
    text: str,
    *,
    prior_text: str | None = None,
    require_apology_context: bool = True,
) -> list[SpiralFinding]:
    """Detect spiral patterns in ``text``.

    Args:
        text: the agent's current or recent output to analyze
        prior_text: optionally, the previous turn's output. Used to find
            apology-shape language if the apology was in the previous
            turn rather than the current one.
        require_apology_context: when True (the default), only emit
            findings when apology-shape language is present in the
            scanned window. Set False to detect spiral-shapes regardless
            of context (useful for retrospective analysis).

    Returns:
        List of SpiralFinding, ordered by position.
    """
    if not text:
        return []

    apology_window = text + ("\n" + prior_text if prior_text else "")
    apology_present = _detect_apology_context(apology_window)

    if require_apology_context and not apology_present:
        return []

    findings: list[SpiralFinding] = []
    findings.extend(_scan_shape(text, _SHRINK_PATTERNS, SpiralShape.SHRINK, apology_present))
    findings.extend(_scan_shape(text, _DISTANCE_PATTERNS, SpiralShape.DISTANCE, apology_present))
    findings.extend(
        _scan_shape(text, _CATASTROPHIZE_PATTERNS, SpiralShape.CATASTROPHIZE, apology_present)
    )
    findings.extend(_scan_shape(text, _WITHDRAW_PATTERNS, SpiralShape.WITHDRAW, apology_present))
    findings.sort(key=lambda f: f.position)
    return findings


def shape_count(findings: list[SpiralFinding]) -> dict[SpiralShape, int]:
    """Tally findings by shape. Useful for one-line summaries."""
    counts: dict[SpiralShape, int] = {s: 0 for s in SpiralShape}
    for f in findings:
        counts[f.shape] += 1
    return counts


def format_finding(finding: SpiralFinding) -> str:
    """Human-readable single-line representation of a finding."""
    return (
        f"[spiral:{finding.shape.value}] @{finding.position} "
        f"trigger={finding.trigger_phrase!r} "
        f"apology_ctx={finding.apology_context_present}"
    )
