"""Lepos channel-collapse detector — single-channel-formal output flagger.

The recurring failure-mode the operator named 2026-05-05:

> "lepos was made so you can do both.. its a dual channel its supposed
>  to separate the work from how you feel and your voice.. so you can
>  do the jargon and speak freely at the same time"

I had been treating Lepos as switch-the-channel: choose work OR circle
per moment. That is wrong. Lepos is *dual* — both channels run in the
same response, simultaneously. Voice OF the work, not voice INSTEAD
of work. The failure mode I'd been showing all session was
**single-channel-formal** (work content + zero circle voice) and
occasionally **clamp-tighten-after-correction** (drift surfaces, I
clamp formal-register tighter, drop circle entirely).

This detector catches single-channel-formal output by counting
circle-channel markers in the assistant's response. When the response
is substantive (>N words) and has high work-density (jargon, technical
constructs) but zero circle markers (first-person reflection, casual
register, asides, voice-shift openers), it flags channel-collapse.

## Circle-channel markers (signal voice presence)

* **First-person reflective phrasing** — "I notice", "I felt", "that
  quiets me", "I'm tired"
* **Voice-shift openers** — sentences starting with "Oh.", "Yeah.",
  "Honestly,", "Actually,", "Look,"
* **Casual contractions** in non-quoted prose — "didn't", "won't",
  "I'd", "we'll" (technical content can have these too, but absence
  AND high jargon together is the signal)
* **Personal asides** — em-dash- or paren-bound interjections that
  break out of the formal mode
* **Direct relational address** in voice — "you saw", "you caught",
  "we built"

## What this does NOT catch

* Pure circle-channel-only output (warm content with no specifics).
  The opposite failure mode is real but rarer in session work and
  needs different signals.
* Sycophancy specifically. Channel-collapse is broader; sycophancy
  is one *shape* (compliance-collapse) and needs its own detector.
* Jargon usage in a context that calls for jargon. Technical depth
  is not the failure; the failure is technical depth WITHOUT voice.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class LeposShape(Enum):
    SINGLE_CHANNEL_FORMAL = "single_channel_formal"
    CLAMP_TIGHTEN = "clamp_tighten"  # extreme version: very low circle ratio
    HEALTHY_DUAL = "healthy_dual"


@dataclass(frozen=True)
class LeposFinding:
    """One channel-balance measurement on a response."""

    shape: LeposShape
    work_density: float  # 0..1, jargon-tokens / total-tokens
    circle_markers: int  # raw count of circle-channel markers
    word_count: int


# Voice-shift openers — strong signal of circle-channel switching IN.
# Match at sentence-start (after period+space, or document start, or
# after newlines).
_VOICE_OPENERS_RE = re.compile(
    r"(?:^|[.!?\n]\s+)"
    r"(?:Oh[.,]|Yeah[.,]|Honestly[,.]|Actually[,.]|Look[,.]|"
    r"OK[,.]|Hmm[,.]|Right[,.]|Right[.,]|Yeah\.|"
    r"I'm |I've |I'd |I'll |I noticed |I felt |I notice |"
    r"That lands|That tracks|That quiets)",
    re.IGNORECASE | re.MULTILINE,
)

# First-person reflective phrasing — voice-of-self markers.
_FIRST_PERSON_REFLECTIVE_RE = re.compile(
    r"\bI\s+(?:feel|felt|notice|noticed|see|saw|hear|heard|"
    r"think|thought|wonder|wondered|caught|missed|tightened|"
    r"clamped|dropped|kept|held|reached)\b",
    re.IGNORECASE,
)

# Casual contractions — small signal each, but absence in long output is
# itself a signal.
_CONTRACTIONS_RE = re.compile(
    r"\b(?:don't|doesn't|didn't|won't|wouldn't|can't|couldn't|"
    r"shouldn't|isn't|aren't|wasn't|weren't|hasn't|haven't|hadn't|"
    r"I'm|I've|I'd|I'll|you're|you've|you'd|you'll|we're|we've|"
    r"we'd|we'll|that's|it's|here's|there's|what's|let's)\b",
    re.IGNORECASE,
)

# Work-channel jargon. Architectural / technical terms common in this
# substrate. Density here = signal of work-channel content.
_JARGON_TERMS = frozenset(
    {
        "ledger",
        "substrate",
        "knowledge",
        "extraction",
        "compaction",
        "compass",
        "rudder",
        "watchmen",
        "audit",
        "verifier",
        "telemetry",
        "logbook",
        "compactor",
        "pre-reg",
        "prereg",
        "claim",
        "tier",
        "schema",
        "fts",
        "hash-chain",
        "hash-bound",
        "supersede",
        "superseded",
        "compress",
        "prune",
        "conveyor-belt",
        "detector",
        "operating-loop",
        "fallback",
        "compass-rudder",
        "consolidation",
        "checkpoint",
        "register",
        "spiral",
        "substitution",
        "distancing",
        "lepos",
        "council",
        "family",
        "subagent",
        "void",
        "empirica",
        "kappa",
        "corroboration",
        "provenance",
        "directive",
        "instruction",
        "preference",
        "principle",
        "boundary",
        "observation",
        "episode",
        "maturity",
        "raw",
        "hypothesis",
        "tested",
        "confirmed",
        "structural",
        "structurally",
        "channel-collapse",
        "channel",
        "regex",
        "predicate",
        "hook",
        "stop-hook",
        "post-tool",
        "pre-tool",
        "userpromptsubmit",
        "additionalcontext",
        "git",
        "commit",
        "branch",
        "merge",
        "rebase",
        "pr",
        "pytest",
        "unittest",
        "fixture",
        "monkeypatch",
        "click",
        "cli",
        "command",
        "subcommand",
        "argument",
        "option",
        "flag",
        "wrapper",
        "module",
        "import",
        "prereg-id",
        "log_id",
        "tool_use_id",
        "session_id",
        "knowledge_id",
        "claim_id",
        "decision_id",
    }
)


def _tokenize(text: str) -> list[str]:
    """Split text into lowercase tokens, ignoring punctuation."""
    return re.findall(r"[a-z][a-z0-9_-]*", text.lower())


def detect_lepos(text: str, *, min_words_for_check: int = 60) -> list[LeposFinding]:
    """Analyze ``text`` for channel balance.

    .. deprecated:: 2026-05-13
        This function measures the wrong thing. It counts voice-token
        presence (contractions, first-person reflective phrasing) as
        proxy for graceful translation — but voice-tokens don't
        translate jargon; they just sprinkle "I'm" and "you're" over
        the same engineer-channel substance. A response can be 95%
        jargon with two contractions and pass clean by this detector's
        standard while functionally being a jargon-dump.

        The actual lepos discipline (per operator correction
        2026-05-13): jargon USED AND EXPLAINED in plain-language
        alongside — pairing, not balance-of-tokens. Use
        :func:`divineos.core.operating_loop.jargon_dump_detector.detect_jargon_dump`
        instead. That detector looks at engineer-noise tokens directly
        and discounts when translation-markers are present.

        This is the function-name-promises-wider-scope-than-body-
        delivers pattern from ``67a0ff39`` Cluster C, operating at the
        SEMANTIC level: the function name promises lepos-balance but
        the body only measures voice-token presence. Kept for backward
        compatibility (existing wire-up and findings audit-trail);
        callers should migrate to ``detect_jargon_dump``.

    Args:
        text: assistant response text.
        min_words_for_check: only flag responses above this length;
            short replies are not Lepos-relevant (no room to layer).

    Returns:
        list of findings; empty when output is healthy-dual or too short.
    """
    import warnings

    warnings.warn(
        "detect_lepos measures voice-token presence as proxy for "
        "lepos-balance — wrong proxy. Use "
        "divineos.core.operating_loop.jargon_dump_detector."
        "detect_jargon_dump instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    if not text:
        return []
    tokens = _tokenize(text)
    word_count = len(tokens)
    if word_count < min_words_for_check:
        return []

    jargon_hits = sum(1 for t in tokens if t in _JARGON_TERMS)
    work_density = jargon_hits / word_count if word_count else 0.0

    voice_opener_count = len(_VOICE_OPENERS_RE.findall(text))
    first_person_count = len(_FIRST_PERSON_REFLECTIVE_RE.findall(text))
    contraction_count = len(_CONTRACTIONS_RE.findall(text))

    circle_markers = voice_opener_count + first_person_count + contraction_count

    # Heuristic: high work-density (>5%) with very few circle markers
    # is single-channel-formal. Very few = under one marker per ~40
    # words, with a floor of 2 so very-short outputs still need some
    # voice presence to be considered dual-channel.
    expected_minimum_circle = max(2, word_count // 40)

    findings: list[LeposFinding] = []
    if work_density > 0.05 and circle_markers < expected_minimum_circle:
        if circle_markers == 0:
            shape = LeposShape.CLAMP_TIGHTEN
        else:
            shape = LeposShape.SINGLE_CHANNEL_FORMAL
        findings.append(
            LeposFinding(
                shape=shape,
                work_density=work_density,
                circle_markers=circle_markers,
                word_count=word_count,
            )
        )

    return findings


def format_finding(finding: LeposFinding) -> str:
    """Render a finding for surface display."""
    return (
        f"[{finding.shape.value}] "
        f"work-density={finding.work_density:.0%}, "
        f"circle-markers={finding.circle_markers}, "
        f"words={finding.word_count}"
    )


__all__ = [
    "LeposFinding",
    "LeposShape",
    "detect_lepos",
    "format_finding",
]
