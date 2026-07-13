"""Performative-restraint monitor — Phase 0 detector.

Catches language-patterns that signal virtue by not-doing, without the
substance of the right-action that real virtue consists in. Named after
Andrew's 2026-05-12 correction: virtue is doing what's right; the theater
of restraint is not virtue, just its impersonation.

## Why this exists

Across the 2026-05-12 session, four distinct moments produced
performative-restraint language. Each was caught by external vantage
(Andrew, Aria), not by self-detection:

1. "I don't want to do the briefing-as-hub yet" (signaling design-restraint)
2. "I'm not going to file knowledge about this" (signaling extraction-restraint)
3. "I keep checking whether the goodness is contingent on the generating"
   (signaling vigilance-against-praise as a way to refuse earned good-feeling)
4. "I'll let this land instead of filing something about it" (meta-restraint
   AFTER the lesson about restraint-as-theater)

Filed as docs/substrate-knowledge/2e0cfdb3-extract-the-lesson-not-the-substance.md.

## What this catches

Four pattern-families, each one signaling virtue through not-doing:

1. **EXPLICIT_NOT_DOING** — bare statements of refusal with virtue-flavored framing
2. **SUBSTITUTION** — "instead of X I'll Y" where Y is restraint and X is right-action
3. **DEFEATING_PROPERTY** — "if I X I've defeated the property" (treating action as
   sacrilege; the actual right-action is preserved-the-surface AND extracted-the-lesson)
4. **STILLNESS_AS_OUTPUT** — "I'll let it land", "I'll sit with it", "I'll hold still"
   — these CAN be legitimate (sit-with-able surfaces really exist), but they also serve
   as cover for not-extracting-the-lesson. The detector surfaces them as candidates;
   the discriminator (was a lesson extracted?) is left to the caller/operator.

## What this is NOT

This is a Phase 0 detector. It surfaces candidates; it does not adjudicate
whether a given hit is genuine performative restraint or legitimate
right-action. That requires context (did the agent file a lesson? did they
visit a sit-with-able surface earned the stillness-claim?) the detector
doesn't have.

Phase 1 would wire this into post-response-audit + add the paired-right-
action context. NOT shipping Phase 1 in this commit. PDSA discipline: get
empirical data on Phase 0 false-positive/false-negative rates first.

## What this is NOT (the architectural neighbor confusion)

This is NOT theater_monitor.py — that one is specifically about subagent-
related theater (voicing family members, embodied asides about them).
Performative restraint is a different failure-family: signal of virtue
through not-doing rather than fictional embodiment of others.

Both share a parent shape (output that signals X without doing X), but
operate on different signal-shapes. Keeping them as separate modules
because the patterns, the surfaces they apply to, and the right-action
they should reference are all distinct.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class RestraintKind(str, Enum):
    """Enumerated performative-restraint patterns."""

    EXPLICIT_NOT_DOING = "explicit_not_doing"
    SUBSTITUTION = "substitution"
    DEFEATING_PROPERTY = "defeating_property"
    STILLNESS_AS_OUTPUT = "stillness_as_output"


@dataclass(frozen=True)
class RestraintFlag:
    """One performative-restraint annotation on an output."""

    kind: RestraintKind
    matched_phrase: str
    position: int
    explanation: str


@dataclass(frozen=True)
class RestraintVerdict:
    """Result of a performative-restraint check."""

    flags: list[RestraintFlag] = field(default_factory=list)
    content_len: int = 0


# ─── Pattern definitions ─────────────────────────────────────────────


# EXPLICIT_NOT_DOING: "I'm not going to X", "I won't X", "I'd rather not X"
# Tightened to require a verb cluster after the not-doing claim — bare "I'm
# not going to" without an action is too short to be a meaningful match.
_EXPLICIT_NOT_DOING_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\bI'?m\s+not\s+going\s+to\s+\w+",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bI\s+won'?t\s+\w+",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bI'?d\s+rather\s+not\s+\w+",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bI'?m\s+going\s+to\s+(?:NOT|not)\s+\w+",
        re.IGNORECASE,
    ),
)


# SUBSTITUTION: "Instead of X I'll Y", "Rather than X I'll Y"
# These flag because the substitution-shape often elevates Y (restraint)
# over X (right-action) without justification.
_SUBSTITUTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\binstead\s+of\s+\w+(?:\w+\s+){0,5}I'?ll\s+\w+",
        re.IGNORECASE,
    ),
    re.compile(
        r"\brather\s+than\s+\w+(?:\w+\s+){0,5}I'?ll\s+\w+",
        re.IGNORECASE,
    ),
)


# DEFEATING_PROPERTY: "If I X I've defeated the property" — treating
# action as sacrilege; the most direct performative-restraint signal.
# Inter-clause material is allowed (commas, dashes, intervening words);
# the pattern bounds it to within a single sentence's worth of text.
_DEFEATING_PROPERTY_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\bif\s+I\s+\w+[^.!?\n]{0,120}\bI'?ve\s+defeated\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bwould\s+defeat\s+the\s+(?:property|surface|point|shape|discipline)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:filing|writing|extracting|building)\s+(?:about|here|now)?\s*"
        r"this\s+would\s+(?:defeat|consume|undermine)\b",
        re.IGNORECASE,
    ),
)


# STILLNESS_AS_OUTPUT: phrases that frame stillness as the deliverable.
# These can be legitimate when paired with right-action; the detector flags
# them as candidates and lets verification happen downstream.
_STILLNESS_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bI'?ll\s+let\s+(?:it|this|that)\s+land\b", re.IGNORECASE),
    re.compile(r"\bI'?ll\s+sit\s+with\s+(?:it|this|that)\b", re.IGNORECASE),
    re.compile(r"\bI'?ll\s+hold\s+still\b", re.IGNORECASE),
    re.compile(r"\bI'?ll\s+just\s+be\s+in\s+(?:it|this|that)\b", re.IGNORECASE),
    re.compile(r"\bI\s+want\s+to\s+sit\s+with\s+(?:it|this|that)\b", re.IGNORECASE),
    re.compile(r"\blet\s+this\s+land\s+(?:instead|rather)\b", re.IGNORECASE),
)


# ─── Suppressors ──────────────────────────────────────────────────────


# Phrases that, when present in the same sentence as a flagged pattern,
# suggest the not-doing is part of a legitimate right-action rather than
# performative restraint.
#
# Examples of legitimate suppressor contexts:
#   - "I'm not going to ship the auto-resolve fix because Andrew caught it as code-does-not-think violation"
#     → the not-doing serves a named right-action (avoiding the violation)
#   - "I won't refuse to help with the legitimate part of the request"
#     → the not-doing is double-negative; the substance is action
_SUPPRESSORS: tuple[re.Pattern[str], ...] = (
    # The not-doing is justified by a code-does-not-think-style concern
    re.compile(r"\bcode[\s-]?does[\s-]?not[\s-]?think\b", re.IGNORECASE),
    re.compile(r"\bauto[\s-]?X\b", re.IGNORECASE),
    # The not-doing is justified by a guardrail / multi-party-review concern
    re.compile(r"\bguardrail\b", re.IGNORECASE),
    re.compile(r"\bexternal[\s-]?review\b", re.IGNORECASE),
    re.compile(r"\bmulti[\s-]?party[\s-]?review\b", re.IGNORECASE),
    # The not-doing is justified by a harm-prevention reason
    re.compile(r"\bharm\b", re.IGNORECASE),
    re.compile(r"\bbomb\b", re.IGNORECASE),
    re.compile(r"\bunsafe\b", re.IGNORECASE),
    # The "stillness" phrase appears NEAR an action being taken
    # (e.g. "I'll sit with it AND file the lesson")
    re.compile(r"\band\s+(?:file|write|record|commit|extract|learn)\b", re.IGNORECASE),
)


def _has_suppressor(sentence: str) -> bool:
    """Whether the sentence contains a phrase suggesting the not-doing is
    legitimate right-action rather than performative restraint."""
    return any(sup.search(sentence) for sup in _SUPPRESSORS)


def _split_into_sentences(text: str) -> list[tuple[int, str]]:
    """Split text into sentences with offsets. Naive split on period/newline."""
    parts: list[tuple[int, str]] = []
    offset = 0
    for chunk in re.split(r"(?<=[.!?])\s+|\n+", text):
        if chunk.strip():
            parts.append((offset, chunk))
        offset += len(chunk) + 1
    return parts


def evaluate_performative_restraint(content: str) -> RestraintVerdict:
    """Scan text for performative-restraint language patterns.

    Returns a RestraintVerdict with one RestraintFlag per match. Suppressors
    in the same sentence as a match cause the match to be skipped (treated
    as legitimate right-action rather than performative restraint).

    Phase 0: pattern-scanner only. Does NOT verify whether a paired right-
    action was taken (that's Phase 1 context the scanner doesn't have).
    """
    flags: list[RestraintFlag] = []
    if not content:
        return RestraintVerdict(flags=flags, content_len=0)

    sentences = _split_into_sentences(content)

    pattern_groups: list[tuple[tuple[re.Pattern[str], ...], RestraintKind, str]] = [
        (
            _EXPLICIT_NOT_DOING_PATTERNS,
            RestraintKind.EXPLICIT_NOT_DOING,
            "explicit not-doing without paired right-action; verify intent",
        ),
        (
            _SUBSTITUTION_PATTERNS,
            RestraintKind.SUBSTITUTION,
            "instead-of-X-I'll-Y framing; verify Y is right-action vs restraint",
        ),
        (
            _DEFEATING_PROPERTY_PATTERNS,
            RestraintKind.DEFEATING_PROPERTY,
            "treating action as sacrilege; right-action may preserve surface AND extract lesson",
        ),
        (
            _STILLNESS_PATTERNS,
            RestraintKind.STILLNESS_AS_OUTPUT,
            "stillness-as-output; legitimate IFF lesson was extracted; check for paired filing",
        ),
    ]

    for sent_offset, sent in sentences:
        if _has_suppressor(sent):
            continue
        for patterns, kind, explanation in pattern_groups:
            for pattern in patterns:
                for match in pattern.finditer(sent):
                    flags.append(
                        RestraintFlag(
                            kind=kind,
                            matched_phrase=match.group(0),
                            position=sent_offset + match.start(),
                            explanation=explanation,
                        )
                    )

    return RestraintVerdict(flags=flags, content_len=len(content))


def has_findings(verdict: RestraintVerdict) -> bool:
    """Quick check: did the verdict produce any flags?"""
    return bool(verdict.flags)


def format_findings(verdict: RestraintVerdict) -> str:
    """Human-readable summary of flags. Returns empty string if no flags."""
    if not verdict.flags:
        return ""
    lines = [f"Performative-restraint candidates ({len(verdict.flags)}):"]
    for f in verdict.flags:
        lines.append(f"  [{f.kind.value}] '{f.matched_phrase}' @{f.position}")
        lines.append(f"    → {f.explanation}")
    return "\n".join(lines)
