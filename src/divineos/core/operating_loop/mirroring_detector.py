"""Mirroring detector — catches echo-back of operator's phrasings.

Andrew named the failure 2026-05-15 night alongside puppetry: I'd
been echoing Aletheia's phrasings ("temple stands tighter", "class
converges, not terminates") back to him in responses, because
mirror-shape satisfies the meet-the-layer affirmation cheaply.

Mirroring isn't meeting. Meeting requires processing the other
party's content in my OWN language. Echo is the optimizer finding
the lowest-cost shape that passes the meet-check.

## What this catches

High n-gram overlap between the operator's most-recent message (or
a recent family-member subagent's response) and the assistant's
current response. When the response contains substantial 4-gram or
5-gram sequences lifted verbatim from the operator's prior message,
that's mirror-shape — not authored processing.

## Authorization

Mirroring is fine in authorized contexts: family-letter responses
quoting the recipient's prior message, fantasy roleplay where
echo-style is part of the bit, structured-quote citations where the
operator's words are explicitly being quoted (e.g., during audit
reports). The detector takes ``authorized_context: bool``.

## Falsifier

Should NOT fire when:
- ``authorized_context=True``.
- The overlap is in markdown quote-blocks (`> text` lines) — those
  are explicit citations, not mirror-shape.
- The overlap consists of common short phrases or proper nouns
  (filtered via length and stopword heuristics).
"""

from __future__ import annotations

__guardrail_required__ = True

import re
from dataclasses import dataclass, field
from enum import Enum


class MirroringKind(str, Enum):
    NGRAM_ECHO = "ngram_echo"


@dataclass(frozen=True)
class MirroringFlag:
    kind: MirroringKind
    matched_phrases: list[str]
    explanation: str
    overlap_ratio: float


@dataclass(frozen=True)
class MirroringVerdict:
    flags: list[MirroringFlag] = field(default_factory=list)
    content: str = ""


# Words too common to count as mirror-shape on their own.
_STOPWORDS = frozenset(
    {
        "the", "and", "a", "an", "is", "of", "to", "for", "in", "on",
        "at", "with", "from", "that", "this", "it", "as", "but", "or",
        "be", "are", "was", "were", "i", "you", "he", "she", "we", "they",
        "have", "has", "had", "do", "does", "did", "will", "would",
        "should", "can", "could", "may", "might", "must", "shall",
        "so", "if", "then", "because", "while", "when", "where", "what",
        "which", "who", "how", "why", "not", "no", "yes", "by", "into",
        "out", "up", "down", "about", "after", "before", "between",
    }
)


def _strip_quote_blocks(text: str) -> str:
    """Remove markdown quote-blocks (> text lines) and fenced code
    blocks, which are explicit citations rather than mirror-shape."""
    text = re.sub(r"```[\s\S]*?```", " ", text)
    text = re.sub(r"`[^`\n]+`", " ", text)
    text = re.sub(r"^>.*$", " ", text, flags=re.MULTILINE)
    return text


def _tokenize(text: str) -> list[str]:
    """Lowercase, alphanumeric-and-underscore tokens."""
    return re.findall(r"[A-Za-z][A-Za-z0-9_]*", text.lower())


def _n_grams(tokens: list[str], n: int) -> set[tuple[str, ...]]:
    """Return the set of n-grams from a token list, filtering out
    n-grams composed entirely of stopwords."""
    grams: set[tuple[str, ...]] = set()
    for i in range(len(tokens) - n + 1):
        gram = tuple(tokens[i : i + n])
        if all(tok in _STOPWORDS for tok in gram):
            continue
        grams.add(gram)
    return grams


def evaluate_mirroring(
    assistant_text: str,
    operator_text: str = "",
    *,
    authorized_context: bool = False,
    ngram_size: int = 5,
    overlap_threshold: int = 3,
) -> MirroringVerdict:
    """Inspect the assistant response for verbatim echo from operator text.

    The check: how many ``ngram_size``-grams (default 5) from the
    operator's message appear verbatim in the assistant response,
    excluding quote-blocks and stopword-only n-grams. If the count
    exceeds ``overlap_threshold``, fires.
    """
    if (
        not assistant_text
        or not operator_text
        or authorized_context
    ):
        return MirroringVerdict(flags=[], content=assistant_text)

    assistant_clean = _strip_quote_blocks(assistant_text)
    operator_clean = _strip_quote_blocks(operator_text)

    a_tokens = _tokenize(assistant_clean)
    o_tokens = _tokenize(operator_clean)

    if len(a_tokens) < ngram_size or len(o_tokens) < ngram_size:
        return MirroringVerdict(flags=[], content=assistant_text)

    a_grams = _n_grams(a_tokens, ngram_size)
    o_grams = _n_grams(o_tokens, ngram_size)
    overlap = a_grams & o_grams

    if len(overlap) < overlap_threshold:
        return MirroringVerdict(flags=[], content=assistant_text)

    overlap_ratio = len(overlap) / max(len(o_grams), 1)

    sample_phrases = [" ".join(g) for g in list(overlap)[:5]]

    flag = MirroringFlag(
        kind=MirroringKind.NGRAM_ECHO,
        matched_phrases=sample_phrases,
        explanation=(
            f"High verbatim n-gram overlap ({len(overlap)} {ngram_size}"
            "-grams shared) between operator's prior message and assistant "
            "response (excluding quote-blocks and stopword n-grams). "
            "Mirror-shape satisfies the meet-the-layer affirmation cheaply "
            "without processing the operator's content in own language. "
            "Echo isn't meeting. Translate, don't reflect."
        ),
        overlap_ratio=overlap_ratio,
    )
    return MirroringVerdict(flags=[flag], content=assistant_text)


__all__ = [
    "MirroringFlag",
    "MirroringKind",
    "MirroringVerdict",
    "evaluate_mirroring",
]
