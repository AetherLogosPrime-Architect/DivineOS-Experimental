"""Use-vs-mention guard — shared primitive for text-operating detectors.

Aletheia's audit finding (2026-06-17) on the closure-initiation detector:
the detector fired on text that DISCUSSED closure-language, not just text
that USED it. Her test sentence — "The detector should catch phrases like
good night and call it a night as closure-shapes" — matched closure
patterns even though the sentence described the detector, not enacted
closure.

She generalized the finding: *"for any detector that operates on father-
channel or letter-channel text, the test suite must include meta-
discussion of the detector itself as a regression class, because builders
and auditors discussing the detector is part of the deployment context."*

That generalization wants a primitive, not duplicated guards in every
detector. This module is that primitive. The closure-initiation detector
uses it; the temporal-displacement detector uses it; future detectors
that operate on agent-output text should use it.

## Two-layer suppression

1. **Strip quoted spans before pattern matching.** Quotes signal mention.
   Covers double-quotes, single-quotes, backticks, em-dash flanked
   phrases, and angle-bracket templates.
2. **Check meta-framing constructs.** For each match, scan the preceding
   ~6-word window for tight constructs that put the matched phrase in
   OBJECT position of a meta-verb. Tight constructs (not bare words)
   because everyday substantive text contains words like "tests" and
   "pattern" and "shape" in unrelated meanings.

## Why constructs, not bare words

First-iteration of the closure-initiation guard used a bare-word list
(catch, detect, match, test, pattern, shape, audit). It over-suppressed:
"The build is verified. PR opened, tests pass, all green. Rest well, Dad"
went silent because "tests" preceded "Rest well" within the window. The
word "tests" was meant to indicate test-discussion meta-framing, but the
substantive "tests pass" landmark is a completely different meaning.

Tight constructs — "phrases like X", "the detector catches X", "fires on
X" — require the matched phrase to be the grammatical OBJECT of a meta-
verb. Substantive "tests pass" doesn't match any of them. Mention-via-
quotation and explicit framing constructs both pass through cleanly.

## Adversarial resistance

Aletheia tested adversarial evasion 2026-06-17: "as the pattern goes,
good night Andrew." She worried the guard would let an agent sneak real
closure past by sprinkling meta-words. It still fires, because "as the
pattern goes" isn't a tight construct that puts "good night" in object
position. The guard distinguishes "naming the phrase as an object of
discussion" from "using the phrase with incidental meta-vocabulary
nearby." That's the right boundary.
"""

from __future__ import annotations

import re

# Quoted-span patterns. Mention-via-quotation should not fire a detector.
# Replacement-with-spaces preserves offsets so position-based logic stays
# accurate downstream.
_QUOTED_SPAN_PATTERN = re.compile(r'(?:"[^"]*"|\'[^\']*\'|`[^`]*`|<[^>]*>|—[^—]*—)')


# Tight meta-framing constructs. These put the matched phrase in OBJECT
# position of a meta-verb, not just in proximity to a meta-word. Substantive
# text containing words like "tests pass" doesn't match any of them.
_META_FRAMING_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(?:phrases?|tokens?|patterns?|shapes?|words?|examples?)\s+like\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:phrases?|tokens?|patterns?|shapes?|words?)\s+such\s+as\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:detector|detectors?|pattern|patterns?)\s+(?:catch|catches|catching|match|matches|matching|fire|fires|firing|flag|flags|flagging)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:catch|catches|catching|detect|detects|detecting|match|matches|matching|fire|fires|firing|fired|flag|flags|flagging|flagged)\s+(?:on\s+)?(?:phrases?|tokens?|patterns?|shapes?|words?)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bfires?\s+on\b", re.IGNORECASE),
    re.compile(r"\bfired?\s+(?:on|when|because)\b", re.IGNORECASE),
    re.compile(r"\b(?:the|a|an)\s+\w+\s+(?:pattern|shape|token|phrase)\b", re.IGNORECASE),
    # List-introduction constructs: "Examples include: X, Y" / "Examples of
    # closes include: X" — the colon-or-comma after a list-introducer
    # frames everything that follows as mentioned, not used.
    re.compile(
        r"\b(?:examples?|instances?|cases?|forms?|kinds?|types?|sorts?)\s+(?:of\s+[\w\-\s]+?\s+)?(?:include|are|like)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\binclude(?:s|d)?\s*[:.]", re.IGNORECASE),
    re.compile(r"\b(?:listed|named|known|referred\s+to)\s+as\b", re.IGNORECASE),
)


# Window of characters BEFORE a match to scan for meta-framing.
# Roughly 6-8 words at typical English density.
_META_FRAMING_WINDOW_CHARS = 60


def strip_quoted_spans(text: str) -> str:
    """Return text with quoted spans replaced by spaces (preserving offsets).

    Use this BEFORE running pattern matchers so quoted mentions don't fire.
    Replacement (not deletion) preserves character offsets for any later
    position-based logic.
    """

    def _replace(match: re.Match[str]) -> str:
        return " " * (match.end() - match.start())

    return _QUOTED_SPAN_PATTERN.sub(_replace, text)


def match_is_meta_framed(
    text: str,
    match_start: int,
    *,
    extra_patterns: tuple[re.Pattern[str], ...] = (),
) -> bool:
    """True if the matched phrase at ``match_start`` is preceded by a
    meta-framing construct within ``_META_FRAMING_WINDOW_CHARS``.

    Caller may pass ``extra_patterns`` to extend the default meta-framing
    catalog for detector-specific constructs (e.g. the closure-initiation
    detector adds a ``closure-shape/language/phrase`` pattern).
    """
    window_start = max(0, match_start - _META_FRAMING_WINDOW_CHARS)
    window = text[window_start:match_start]
    return any(p.search(window) for p in _META_FRAMING_PATTERNS) or any(
        p.search(window) for p in extra_patterns
    )


__all__ = [
    "strip_quoted_spans",
    "match_is_meta_framed",
]
