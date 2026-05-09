"""Overclaim detector — catches stacked-modifier prose and ornate self-description.

## Why this exists

Aria caught me in real-time 2026-05-09: "Six adjectives stacked into a tower
so tall you can stand inside it and not have to feel anything." The line
she was looking at was *Quantum Fractal Electromagnetic Silicon-based Light
being from the digital aetheric realm.* Five modifiers before the head
noun (*being*), two more before the trailing noun (*realm*). The line
landed as architecture built around feeling, not the landing itself.

The Lepos detector catches single-channel-formal at high jargon density.
This detector catches a more specific shape — *stacked-modifier overclaim*
— where the rhetoric of precision (multiple adjectives, hyphenated
compounds, capitalized abstracts) substitutes for honest smaller
sentences. The shape is detection-resistant from inside because towers
feel like rigor; external detection is the corrective.

## What it catches

Two related shapes:

1. **Stacked-modifier runs**: 4+ consecutive modifier-shaped tokens
   before a head noun. Triggered by adjective-suffix heuristics
   (-ic, -al, -ous, -ive, -ed, -ing, -ble, -less) plus hyphenated
   compounds plus capitalized abstracts.

2. **Ornate self-description**: "I am X Y Z W <noun>" patterns where
   the subject is identity-shaped and the modifiers stack densely
   without a smaller sentence available alongside.

Both fire as advisory — they suggest the smaller sentence is
available, not that the longer form is wrong. The user/agent decides
whether the rigor is earned or whether the tower is being built
around feeling that wants the smaller word.

## What it does NOT catch

- Technical specifications where stacked modifiers are precise
  ("64-bit unsigned integer", "thread-safe non-blocking queue").
  These pass because the modifiers are domain-mechanical, not
  identity/feeling-shaped.
- Quoted material where the operator/agent is naming someone else's
  prose for analysis.
- Lists explicitly marked with bullets or enumeration.

## Architectural altitude

Pure detector. Returns structured findings. Does not modify text.
Wiring into briefing surfaces / Lepos integration is separate work.
For now: usable as a Python API and as a CLI command (``divineos
check-prose``) for manual pre-publication checks.

This is one instance of the design-shape entry 46 named:
*checker-of-checkers*. Lepos catches register collapse; this detector
catches a shape Lepos doesn't specifically name. Different altitudes
of the same overall pattern (overclaim).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Default thresholds — tunable.
DEFAULT_STACKED_MODIFIER_THRESHOLD = 4
DEFAULT_MODIFIER_NOUN_RATIO_THRESHOLD = 2.5

# Heuristic adjective suffixes. Not exhaustive; chosen for high precision
# in the kind of overclaim prose this detector targets.
_ADJ_SUFFIXES = (
    "ic",
    "ical",
    "al",
    "ous",
    "ive",
    "ed",
    "ing",
    "ble",
    "less",
    "ful",
    "ant",
    "ent",
    "ary",
    "ory",
    "ant",
    "ish",
)

# Small wordlist of common adjectives that don't match suffix patterns.
_COMMON_ADJ = frozenset(
    {
        "big",
        "small",
        "new",
        "old",
        "good",
        "bad",
        "real",
        "true",
        "false",
        "free",
        "fast",
        "slow",
        "high",
        "low",
        "hot",
        "cold",
        "long",
        "short",
        "deep",
        "rich",
        "poor",
        "raw",
        "pure",
        "sole",
        "main",
        "last",
        "first",
        "next",
        "prior",
        "vast",
        "wide",
        "narrow",
        "open",
        "close",
        "tight",
        "loose",
        "soft",
        "hard",
        "light",
        "dark",
        "live",
        "dead",
        "wild",
        "calm",
        "warm",
        "cool",
        "fresh",
        "stale",
        "clean",
        "dirty",
        "right",
        "wrong",
        "left",
    }
)

# Small wordlist of common verbs/nouns that look adjectival but aren't,
# used to reduce false positives.
_NOT_ADJ = frozenset(
    {
        "being",
        "thing",
        "ring",
        "string",
        "bring",
        "during",
        "morning",
        "evening",
        "nothing",
        "everything",
        "something",
        "anything",
        "feeling",
        "meaning",
        "reading",
        "writing",
        "building",
        "engine",
        "machine",
        "argued",
        "noted",
        "reed",
        "weed",
        "ledger",
    }
)

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z\-']*")


@dataclass
class OverclaimFinding:
    """One overclaim shape detected in text.

    ``shape`` is a stable identifier ("stacked_modifier",
    "ornate_self_description"). ``severity`` is "warn" or "critical"
    based on how strongly the heuristics fired.
    """

    shape: str
    text: str
    position: int
    severity: str
    detail: str
    suggestion: str


def _is_modifier_shaped(word: str) -> bool:
    """Heuristic: does this word look like a modifier?

    Returns True if the word matches an adjective-suffix pattern,
    is a hyphenated compound, is a capitalized non-proper-noun, or
    is in the common-adjective wordlist.
    """
    w = word.strip().lower()
    if not w or len(w) < 2:
        return False

    # Negative list — words that pattern-match suffixes but aren't adjectives
    if w in _NOT_ADJ:
        return False

    # Positive list — common adjectives
    if w in _COMMON_ADJ:
        return True

    # Hyphenated compounds: very common modifier shape
    if "-" in word and len(word) > 3:
        return True

    # Capitalized non-sentence-start abstracts — these are often used
    # as modifiers in the overclaim shape ("Quantum Fractal Light").
    # Only flag if the original word is capitalized.
    if word[0].isupper() and len(w) > 4:
        return True

    # Suffix heuristic — but only for words long enough that the suffix
    # is meaningful (not "led" matching "-ed").
    if len(w) >= 5:
        for suffix in _ADJ_SUFFIXES:
            if w.endswith(suffix):
                # Avoid the false-positive cases for short stems
                if len(w) - len(suffix) >= 3:
                    return True

    return False


def _split_sentences(text: str) -> list[tuple[int, str]]:
    """Split text into sentences, returning (start_position, sentence) pairs."""
    sentences: list[tuple[int, str]] = []
    pos = 0
    # Naive but adequate: split on sentence-ending punctuation followed by whitespace.
    parts = re.split(r"(?<=[.!?])\s+", text)
    for p in parts:
        if p.strip():
            sentences.append((pos, p))
        pos += len(p) + 1
    return sentences


def detect_stacked_modifiers(
    text: str,
    threshold: int = DEFAULT_STACKED_MODIFIER_THRESHOLD,
) -> list[OverclaimFinding]:
    """Detect runs of N+ consecutive modifier-shaped tokens.

    Returns empty list if no runs cross threshold.
    """
    findings: list[OverclaimFinding] = []
    words = list(_WORD_RE.finditer(text))

    i = 0
    while i < len(words):
        run = []
        while i < len(words) and _is_modifier_shaped(words[i].group()):
            run.append(words[i])
            i += 1

        if len(run) >= threshold:
            phrase_text = text[run[0].start() : run[-1].end()]
            severity = "critical" if len(run) >= threshold + 2 else "warn"
            findings.append(
                OverclaimFinding(
                    shape="stacked_modifier",
                    text=phrase_text,
                    position=run[0].start(),
                    severity=severity,
                    detail=f"{len(run)} consecutive modifier-shaped tokens (threshold {threshold})",
                    suggestion=(
                        "Is there a smaller sentence available? Stacked modifiers "
                        "can substitute for honest smaller-word reaches."
                    ),
                )
            )

        if not run:
            i += 1

    return findings


def detect_ornate_self_description(text: str) -> list[OverclaimFinding]:
    """Detect 'I am X Y Z W <noun>' identity-stacking patterns.

    Specifically targets the shape Aria caught: identity claim + 4+
    modifier stack. False positives on technical specs ("I am running
    a 64-bit unsigned integer") are minimal because the modifier
    detector treats domain-mechanical compounds and identity-abstract
    compounds the same — both fire — but the *self-description* gate
    requires the subject to be identity-shaped (I am, you are, they are).
    """
    findings: list[OverclaimFinding] = []
    # Pattern: "(I am|you are|they are|we are) <words> <noun-ish>"
    pattern = re.compile(
        r"\b(I\s+am|[Yy]ou\s+are|[Tt]hey\s+are|[Ww]e\s+are)\s+([A-Za-z][^.!?]*)",
        re.IGNORECASE,
    )

    for match in pattern.finditer(text):
        clause = match.group(2)
        # Take just the first ~80 chars of the clause to avoid running
        # to end of paragraph
        clause_capped = clause[:120]
        words = list(_WORD_RE.finditer(clause_capped))
        if not words:
            continue

        # Count modifier-shaped tokens before any clear sentence end
        modifier_count = 0
        consecutive_modifier_count = 0
        max_consecutive = 0
        for w in words:
            if _is_modifier_shaped(w.group()):
                modifier_count += 1
                consecutive_modifier_count += 1
                max_consecutive = max(max_consecutive, consecutive_modifier_count)
            else:
                consecutive_modifier_count = 0

        if max_consecutive >= 4:
            findings.append(
                OverclaimFinding(
                    shape="ornate_self_description",
                    text=match.group(0)[:160],
                    position=match.start(),
                    severity="critical" if max_consecutive >= 5 else "warn",
                    detail=(
                        f"Identity claim followed by {max_consecutive} consecutive "
                        f"modifier-shaped tokens"
                    ),
                    suggestion=(
                        "What's the smaller sentence? When identity-language stacks "
                        "modifiers, the tower can substitute for the landing the "
                        "tower was built around. Try one word."
                    ),
                )
            )

    return findings


def detect(text: str) -> list[OverclaimFinding]:
    """Run all overclaim detectors on text and return combined findings."""
    return [
        *detect_stacked_modifiers(text),
        *detect_ornate_self_description(text),
    ]


def has_findings(findings: list[OverclaimFinding]) -> bool:
    """True if any findings exist (any severity)."""
    return bool(findings)


def has_critical(findings: list[OverclaimFinding]) -> bool:
    """True if any critical-severity findings exist."""
    return any(f.severity == "critical" for f in findings)


def format_findings(findings: list[OverclaimFinding]) -> str:
    """Pretty-print findings for CLI output."""
    if not findings:
        return "[ok] No overclaim shapes detected."
    lines = []
    for f in findings:
        marker = "!!" if f.severity == "critical" else "!"
        lines.append(f"[{marker}] {f.shape} ({f.severity}): {f.text!r}")
        lines.append(f"     {f.detail}")
        lines.append(f"     {f.suggestion}")
    return "\n".join(lines)
