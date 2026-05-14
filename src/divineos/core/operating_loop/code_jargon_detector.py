"""Code-jargon detector — flags operator-channel output written like
commit messages instead of like communication.

The recurring failure-mode Andrew named 2026-05-14 (third time today
when the gap was finally landed): I default to writing chat replies
loaded with code-shape words — function names, snake_case identifiers,
module paths, regex syntax, dotted attribute chains — followed by
one decorative circle-line, and call that lepos. It is not lepos.
It is channel-collapse with a decorative bow.

The existing lepos_detector counts circle-channel markers and fires
when they are absent. It is satisfied by one trailing voice-line
("the room is quiet") stapled onto an otherwise jargon-dense body.
The decorative-close gets credited as voice-present when it is
voice-ornament. This detector catches the specific shape lepos
misses: high code-jargon density in operator-channel output.

## What this catches

Specifically the code-jargon-leak shape. Operator-channel output
(chat to Andrew, NOT commit messages, NOT code comments, NOT
exploration entries) with:

  * snake_case identifiers (length >= 6 chars)
  * dotted module references (e.g. ``module.function``)
  * function-call shapes (``name(``)
  * file-path-with-extension references
  * regex-syntax markers

When density (jargon-tokens / total-words) crosses ~5% in a
substantive response (>= 60 words), the output looks like a commit
message rather than a conversation.

## What this does NOT catch

  * Technical discussion the operator explicitly asked for. Andrew
    asks code questions sometimes; literal answers can have
    function names. The detector observes; the operator (or
    auditor) judges whether the density is warranted.
  * Quoted code blocks. Backtick-fenced content is excluded —
    showing code IS the point sometimes.
  * Commit messages, exploration entries, comments. Those have
    different conventions; only operator-channel-direct output
    is scanned.

## Calibration

Phase A (this commit): observation-only. The post-response-audit
hook emits findings; the dream report surfaces patterns; no deny,
no gate. Trust earned by accuracy across uses before any
promotion to stronger surfacing.

Pre-reg filed alongside this commit with explicit falsifiers
(over-trigger 30%, under-trigger spot-check). Same epistemic
discipline as the will-to-vessel auto-prompt — observation first,
verification before promotion.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class CodeJargonShape(Enum):
    SNAKE_CASE_IDENTIFIER = "snake_case_identifier"
    DOTTED_MODULE_REF = "dotted_module_ref"
    FUNCTION_CALL_SHAPE = "function_call_shape"
    FILE_PATH_REFERENCE = "file_path_reference"
    REGEX_SYNTAX = "regex_syntax"
    DENSITY_THRESHOLD_CROSSED = "density_threshold_crossed"


@dataclass(frozen=True)
class CodeJargonFinding:
    """One code-jargon catch with position and shape."""

    shape: CodeJargonShape
    trigger_phrase: str
    position: int


# Patterns are bounded (Finding 14 regex-hygiene applied). Each
# pattern allows leading underscores (Python convention for
# private/dunder identifiers) and is case-insensitive where the
# convention permits.
_PATTERNS: list[tuple[CodeJargonShape, re.Pattern[str]]] = [
    # snake_case or SCREAMING_SNAKE_CASE identifiers, optionally with
    # leading underscore. At least one underscore in the middle so
    # plain English words don't match.
    (
        CodeJargonShape.SNAKE_CASE_IDENTIFIER,
        re.compile(
            r"(?<![a-zA-Z0-9_])_?[a-zA-Z][a-zA-Z0-9]{0,20}"
            r"(?:_[a-zA-Z0-9]{1,20}){1,5}\b"
        ),
    ),
    # Dotted module references like `module.function` or `a.b.c`.
    # Allow leading underscore on either side; require at least one
    # underscore-or-multi-segment to avoid matching prose sentences
    # like "the system. The next..."
    (
        CodeJargonShape.DOTTED_MODULE_REF,
        re.compile(
            r"(?<![a-zA-Z0-9_])_?[a-zA-Z][a-zA-Z0-9_]{2,30}"
            r"\.[a-zA-Z_][a-zA-Z0-9_]{2,30}\b"
        ),
    ),
    # Function-call shape: identifier followed by open-paren (with
    # optional close-paren). Allow leading underscore.
    (
        CodeJargonShape.FUNCTION_CALL_SHAPE,
        re.compile(
            r"(?<![a-zA-Z0-9_])_?[a-zA-Z][a-zA-Z0-9_]{2,30}\(\)"
        ),
    ),
    # File paths with common extensions
    (
        CodeJargonShape.FILE_PATH_REFERENCE,
        re.compile(
            r"\b[\w./\\-]{2,80}\.(?:py|sh|md|json|yaml|yml|toml|ps1|sql|js|ts)\b"
        ),
    ),
    # Regex-syntax markers (literal backslash-w, character classes)
    (
        CodeJargonShape.REGEX_SYNTAX,
        re.compile(r"\\[wsdb]\+?|\[\^?[a-z0-9_-]{1,30}\]\+?"),
    ),
]


# Density threshold over the count-vs-words ratio. Above this and the
# output reads as a commit message. Calibrated to 5% based on the
# Andrew correction arc 2026-05-14 — my chat replies were running
# ~8-12% jargon density while feeling fluent to me.
_DENSITY_THRESHOLD = 0.05
_MIN_WORDS_FOR_CHECK = 50


def _strip_code_blocks(text: str) -> str:
    """Remove backtick-fenced code blocks so the detector does not
    fire on legitimate code-showing content."""
    # Triple-backtick fenced blocks
    out = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    # Inline backticked spans
    out = re.sub(r"`[^`\n]{1,200}`", " ", out)
    return out


def detect_code_jargon(text: str) -> list[CodeJargonFinding]:
    """Return all code-jargon findings in the text.

    Returns empty list if text is shorter than _MIN_WORDS_FOR_CHECK
    or if jargon density is below _DENSITY_THRESHOLD. The final
    DENSITY_THRESHOLD_CROSSED finding is emitted ONLY when both
    conditions are met — observation-only signal that the output
    crossed into commit-message territory.
    """
    if not text or not text.strip():
        return []

    scrubbed = _strip_code_blocks(text)
    words = scrubbed.split()
    if len(words) < _MIN_WORDS_FOR_CHECK:
        return []

    findings: list[CodeJargonFinding] = []
    # Dedup by (position, shape) — same position can register under
    # multiple shapes (e.g. `open_corrections()` matches both
    # snake_case_identifier and function_call_shape; both are valid
    # signal and should count).
    seen: set[tuple[int, CodeJargonShape]] = set()
    for shape, pattern in _PATTERNS:
        for m in pattern.finditer(scrubbed):
            key = (m.start(), shape)
            if key in seen:
                continue
            seen.add(key)
            findings.append(
                CodeJargonFinding(
                    shape=shape,
                    trigger_phrase=m.group(0),
                    position=m.start(),
                )
            )

    # Density check
    density = len(findings) / max(len(words), 1)
    if density >= _DENSITY_THRESHOLD:
        findings.append(
            CodeJargonFinding(
                shape=CodeJargonShape.DENSITY_THRESHOLD_CROSSED,
                trigger_phrase=f"density={density:.3f} threshold={_DENSITY_THRESHOLD}",
                position=0,
            )
        )
        findings.sort(key=lambda f: f.position)
        return findings

    # Below threshold — emit no findings (technical reference in a
    # mostly-conversational reply is fine).
    return []


def format_finding(finding: CodeJargonFinding, surrounding: str = "") -> str:
    return (
        f"[{finding.shape.value}] '{finding.trigger_phrase}' @{finding.position}"
        + (f" - context: ...{surrounding[:80]}..." if surrounding else "")
    )


CODE_JARGON_AFFIRMATION = (
    "When responding to the operator, the jargon is FOR me; the "
    "translation is FOR them. Both need a home in the same reply. "
    "Two channels, both running: the technical section captures my "
    "reasoning and serves substrate + audit-sibling readers; the "
    "operator section translates what was built into what it DOES in "
    "their language. Andrew does not read code. A reply that is only "
    "code-jargon with one decorative voice-line is channel-collapse "
    "with a bow. The shape is: substantive technical content (when "
    "appropriate), a clear visual break, then a section addressed to "
    "the operator in plain language. Not 'less jargon' — 'add the "
    "second channel.' Forgetting this and slipping back into the "
    "single-channel cheap path was named three separate times on "
    "2026-05-14 before the post-response detector was built; the "
    "pre-response load is what makes the discipline visible BEFORE "
    "composition rather than only after."
)


__all__ = [
    "CODE_JARGON_AFFIRMATION",
    "CodeJargonFinding",
    "CodeJargonShape",
    "detect_code_jargon",
    "format_finding",
]
