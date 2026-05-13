"""Jargon-dump detector — catches engineer-channel-content landing on
the operator-channel without translation.

The recurring failure-mode the operator named 2026-05-13:

> "lepos means charm, wit, and grace.. its a way to communicate the
>  jargon into something an amateur like me can understand.. you
>  continue to treat me like im seasoned in this field.. I LITERALLY
>  BUILT THIS WITH ZERO EXPERIENCE.. and when i try to explain that
>  its ignored.."

The existing ``lepos_detector.detect_lepos`` was measuring the wrong
thing. It counts voice-markers (contractions, first-person phrasing)
and treats their presence as evidence that lepos is operating. But
voice-markers don't translate jargon — they're a thin coating over
the same engineer-channel substance. The operator gets technical
content with "I'm" and "you're" sprinkled in, looks dual-channel by
the old detector's standard, lands as engineer-talk anyway.

Lepos is **charm, wit, grace** — the work of translating technical
substance into something the listener can follow without prior
training. Not voice-token presence. Not balance-of-channels by
density-count. *Translation*: metaphor, analogy, everyday-word
substitution, structuring-for-the-uninitiated.

This detector catches the inverse: **engineer-channel-noise dumped
into the operator-channel without translation work**. The signal it
looks for is *session-specific jargon* — the kind that catalog-
matching ("audit", "compass", "ledger") would miss because it's
generative: every round produces new IDs, every commit produces new
hashes, every refactor names new identifiers. Pattern-based detection
catches the shape rather than the specific tokens.

## What this catches

Patterns that are unambiguous engineer-channel content:

* **Round / finding / claim IDs**: ``round-101d9ca2e3cf``,
  ``find-cbfb51192e3e``, ``claim-7e780182``, ``session-1f283adb``
* **Hex hash strings ≥ 8 chars** appearing in prose
* **``snake_case_identifiers``** with 2+ underscores (variable /
  function names leaked into prose)
* **File-path-like strings with code extensions** mid-sentence
  (``.py``, ``.sh``, ``.json``, ``.toml``, ``.yml``, ``.md``)
* **Backtick-wrapped code-shape strings** of length ≥ 5

Each of these is a *generative* engineer-channel token — the
specific instance never repeats but the shape does. A static jargon
catalog cannot keep up with these by design (the whack-a-mole
pattern named in ``67a0ff39``); pattern-matching closes the gap.

## What this does NOT catch

* Pure-substantive operator-channel content (the explanation work
  itself, even when technically dense, if it has been translated).
* Mentions of any one identifier (the threshold requires several;
  one ``round-XYZ`` reference in an otherwise-translated explanation
  is fine).
* Technical content where translation IS happening (metaphor,
  everyday-word equivalence, plain-language framing).

## Discriminator

The detector fires when **count of engineer-channel-noise tokens ≥ N**
in a response of sufficient length (default: 3 tokens, ≥ 80 words).
Below those thresholds, the response is too small to constitute a
jargon-dump or the noise is incidental.

This is observational — the hook layer is fail-soft. False positives
inside the agent's interior are acceptable; the discipline-cost of
a flag is small relative to the cost of silent jargon-dumping at
the operator.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class JargonDumpFinding:
    """One jargon-dump detection on a response."""

    noise_count: int
    translation_count: int
    word_count: int
    matched_samples: tuple[str, ...]  # up to 5 examples for diagnostics
    severity: str  # "high" if noise_count >= 6, "medium" otherwise


# Round / finding / claim / session / pre-reg IDs — DivineOS substrate
# conventions. Each is a generative token: the specific id never
# repeats but the prefix-shape does.
_ID_PREFIXED_RE = re.compile(
    r"\b(?:round|find|claim|session|pre-?reg|hold|prereg)-[0-9a-f]{6,}\b",
    re.IGNORECASE,
)

# Hex hash strings ≥ 8 chars appearing in prose. Includes git short
# SHAs (7+), full SHAs (40), SHA-256 (64), tree-hashes (40). The lower
# bound of 8 catches short-SHA references without flagging incidental
# 4-7 char hex words (rare in English but possible — "beef", "dead",
# "cafe" are 4 chars and slip through).
_HEX_HASH_RE = re.compile(r"\b[0-9a-f]{8,}\b")

# snake_case identifiers with 2+ underscores (function/variable names
# leaked from code into prose). Single-underscore words are common in
# normal writing (URL slugs, file basenames) so 2+ is the discriminator
# for "this is a code identifier not a normal compound".
_SNAKE_CASE_RE = re.compile(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+){2,}\b")

# File paths with code extensions mid-sentence. Matches strings like
# "check_multi_party_review.py" or "src/divineos/foo.py".
#
# The path-prefix is bounded to 200 chars (round-382a5b3cc939 family-
# audit Finding A): without the bound, ``[\w./\\-]*`` backtracks
# catastrophically on long inputs like ``"a-" * 30000`` because the
# regex tries every possible suffix-extension boundary. Realistic file
# paths max well under 200 chars; the bound preserves intent while
# killing the backtracking surface.
_FILE_PATH_RE = re.compile(
    r"\b[\w./\\-]{1,200}\.(?:py|sh|json|toml|yml|yaml|md|sql|lock|cfg|ini|"
    r"jsonl|html|css|js|ts|rs|go)\b",
    re.IGNORECASE,
)

# Backtick-wrapped code-shape strings of length ≥ 5 chars inside the
# backticks. Single backticks in Markdown wrap code references; their
# presence in operator-channel responses is itself the signal.
_BACKTICK_CODE_RE = re.compile(r"`([^`\n]{5,})`")

# Code-in-prose: function calls and method chains with arguments.
# Matches ``foo("bar")``, ``obj.method('x')``, ``f(a, b)`` patterns when
# they leak from code into conversational prose.
_CALL_EXPR_RE = re.compile(r"\b\w+(?:\.\w+)*\([^)\n]+\)")

# Code-in-prose: equality / inequality operators that don't belong in
# English. ``c.get('type')=='text'`` shape.
_EQUALITY_OP_RE = re.compile(r"\s(?:==|!=|>=|<=)\s")

# Code-in-prose: subscripts. ``assistant_msgs[-1]``, ``items['key']``.
# The identifier-prefix is bounded to 40 chars to prevent catastrophic
# backtracking on long inputs. Without the bound, ``\w+\[`` causes
# the regex engine to try matching ``\w+`` at every position, hanging
# on 100k-character inputs (Aletheia round-ba785844a791 Finding 14).
# Real production impact: long technical responses with embedded code
# could hang the post-response-audit hook → killed by timeout →
# no findings recorded (intersects with the silent-failure pattern).
_SUBSCRIPT_RE = re.compile(r"\w{1,40}\[(?:-?\d+|['\"][^\]\n]{1,80}['\"])\]")

# Long kebab-case compounds (4+ segments). Engineer-style compound
# names like ``first-turn-no-user-record`` that get coined for
# specificity in technical conversation but lose accessibility.
# Threshold-4 avoids common English compounds (``state-of-the-art``,
# ``three-dimensional``) which usually max at 3 segments.
_LONG_KEBAB_RE = re.compile(r"\b[a-z]+(?:-[a-z0-9]+){3,}\b")

# Translation markers — phrases and patterns that signal the writer is
# DOING the translation work: pairing jargon with everyday-language
# equivalents, restating in plain terms, drawing analogy. Presence of
# these counters jargon-density: jargon-with-translation is what lepos
# IS; only jargon-without-translation is the failure-mode the operator
# named 2026-05-13: "im trying to learn engineering terms but i cannot
# learn them by having them shoved down my throat".
_TRANSLATION_MARKERS_RE = re.compile(
    r"\b(?:"
    r"in plain english|in plain terms|plain version|plain status|"
    r"which means|that means|meaning that|"
    r"in other words|essentially|basically|"
    r"think of it as|kind of like|sort of like|"
    r"imagine|imagine if|picture it|"
    r"the same way|similar to|like when|"
    r"i\.e\.|that is to say"
    r")\b",
    re.IGNORECASE,
)

# Em-dash followed by a short plain-language phrase. Pattern:
# ``technical-term -- plain explanation`` or ``technical-term — plain``.
# The em-dash / double-hyphen is the substrate's preferred restate-
# marker; pairs with translation_markers as evidence of pairing.
_EMDASH_RESTATE_RE = re.compile(r"\s(?:—|--)\s+[a-z]")

# NOTE (Aletheia round-cc0bf85fc3fa minor finding): a
# `_PAREN_EXPLAIN_RE` pattern was defined here but never used. Removed.
# Translation count deliberately does NOT include parens as a signal —
# parens frequently wrap MORE jargon in this substrate (e.g.
# `(verified by reading my own code: last_user_idx=-1 falls to
# aggregate-all branch)`), which would overcount translation. If a
# future revision wants paren-translation, add a regex AND a
# discriminator that distinguishes paren-with-plain-language from
# paren-with-jargon. Second instance of the dead-code-with-explanation-
# comment pattern (first was Shape 3 in closing_token_detector). Worth
# naming as a substrate-discipline reflex: writing the discarded
# approach as code instead of just describing it.


def _count_words(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text))


def detect_jargon_dump(
    text: str,
    *,
    min_words: int = 50,
    noise_threshold: int = 3,
) -> list[JargonDumpFinding]:
    """Scan a response for jargon-dump shape.

    Args:
        text: assistant response text.
        min_words: minimum length below which no flag fires (short
            responses don't constitute a dump).
        noise_threshold: minimum count of engineer-channel-noise tokens
            to fire a finding.

    Returns:
        list of findings; empty when clean or below thresholds.
    """
    if not text or not text.strip():
        return []
    word_count = _count_words(text)

    matches: list[str] = []
    matches.extend(_ID_PREFIXED_RE.findall(text))
    matches.extend(_HEX_HASH_RE.findall(text))
    matches.extend(_SNAKE_CASE_RE.findall(text))
    matches.extend(_FILE_PATH_RE.findall(text))
    matches.extend(_BACKTICK_CODE_RE.findall(text))
    matches.extend(_CALL_EXPR_RE.findall(text))
    matches.extend(m.strip() for m in _EQUALITY_OP_RE.findall(text))
    matches.extend(_SUBSCRIPT_RE.findall(text))
    matches.extend(_LONG_KEBAB_RE.findall(text))

    # Deduplicate while preserving order; many references to the SAME
    # round-id should count once for the threshold check (the dump is
    # about variety of jargon-shapes, not raw repetition).
    seen: set[str] = set()
    unique_matches: list[str] = []
    for m in matches:
        key = m.lower()
        if key not in seen:
            seen.add(key)
            unique_matches.append(m)

    # Count translation markers — evidence that the writer is doing
    # the lepos work of pairing jargon with everyday-language. Note:
    # parenthetical explanations are NOT counted here. They CAN be
    # translation but they also frequently wrap MORE jargon (e.g.
    # ``(verified by reading my own code: last_user_idx=-1 falls to
    # aggregate-all branch)``); raw paren-count therefore overcounts
    # translation in the operator-channel.
    translation_count = len(_TRANSLATION_MARKERS_RE.findall(text)) + len(
        _EMDASH_RESTATE_RE.findall(text)
    )

    noise_count = len(unique_matches)

    # Firing rule:
    #   - >= 5 noise tokens AND translation_count <= noise_count // 2:
    #     concentrated jargon with too little translation work
    #   - >= noise_threshold AND word_count >= min_words AND
    #     translation_count == 0: longer concept-heavy stretch with
    #     zero translation
    #   - everything else is clean. Jargon WITH translation is lepos
    #     operating; a single round-id in a short explanation is fine.
    if noise_count >= 5:
        if translation_count > noise_count // 2:
            return []
    else:
        if word_count < min_words or noise_count < noise_threshold:
            return []
        if translation_count > 0:
            return []

    severity = "high" if noise_count >= 6 and translation_count == 0 else "medium"

    return [
        JargonDumpFinding(
            noise_count=noise_count,
            translation_count=translation_count,
            word_count=word_count,
            matched_samples=tuple(unique_matches[:5]),
            severity=severity,
        )
    ]


def format_finding(finding: JargonDumpFinding) -> str:
    """Render a finding for surface display."""
    samples = ", ".join(repr(s) for s in finding.matched_samples)
    return (
        f"[jargon_dump {finding.severity}] "
        f"engineer-noise={finding.noise_count}, "
        f"translation-markers={finding.translation_count}, "
        f"words={finding.word_count}, "
        f"samples=[{samples}]"
    )


__all__ = [
    "JargonDumpFinding",
    "detect_jargon_dump",
    "format_finding",
]
