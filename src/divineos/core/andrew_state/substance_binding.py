"""Substance-binding gate for andrew_state observations.

Per Aria's peer-review Catch 2 (2026-06-21 night) and the doormanning
revision (2026-06-22 morning). Three independent checks must ALL pass
at log-time; any failure raises SubstanceBindingError before the row
reaches the substrate.

The checks close specific route-around shapes I would otherwise reach for:

1. cited_span is verbatim contiguous >= 5 tokens. Closes the
   "Dad seems tired" / "i am tired" one-stem-match cardboard.

2. cited_span actually appears in a recent Andrew message. Closes the
   "fabricate a span that fits, then claim it came from him" route.

3. observation references >= 1 content-noun OR content-verb from the
   cited span (stopwords/pronouns excluded). Closes the "lift any span,
   write any observation, the two are not actually linked" route.

Plus a recency check: the source event must be within
SOURCE_RECENCY_HOURS so I cannot retro-justify a now-observation by
citing a span from weeks ago.

All thresholds are tunables prereg-bound (see docs/andrew_state_design.md
tunables catalog).
"""

from __future__ import annotations

import time

# Tunables — prereg-bound per Aria's tunables-catalog requirement.
# Bumping any of these requires a prereg amendment; silent edits become
# auditable via guardrail listing of this file.
CITED_SPAN_MIN_TOKENS = 5
SOURCE_RECENCY_HOURS = 48

# Stopwords excluded from content-link checking. Function words,
# pronouns, and copulas — the tokens that match too easily across any
# pair of sentences.
_STOPWORDS = frozenset(
    {
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "if",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "i",
        "you",
        "he",
        "she",
        "it",
        "we",
        "they",
        "me",
        "him",
        "her",
        "us",
        "them",
        "my",
        "your",
        "his",
        "their",
        "our",
        "this",
        "that",
        "these",
        "those",
        "of",
        "to",
        "in",
        "on",
        "at",
        "for",
        "with",
        "from",
        "by",
        "as",
        "so",
        "do",
        "does",
        "did",
        "have",
        "has",
        "had",
        "will",
        "would",
        "can",
        "could",
        "should",
        "may",
        "might",
        "must",
        "not",
        "no",
        "yes",
        "just",
        "only",
        "very",
        "all",
        "any",
        "some",
        "more",
        "less",
        "what",
        "when",
        "where",
        "who",
        "how",
        "why",
    }
)


class SubstanceBindingError(ValueError):
    """Raised when an observation fails one of the substance-binding checks.

    Distinct from ValueError so the CLI / store layer can catch it
    specifically and surface a clear message about WHICH check failed.
    """


def _tokenize(text: str) -> list[str]:
    """Lowercase + split on non-word characters. Deliberately simple —
    the substance-binding is about ordinary content overlap, not NLP.
    """
    return [t for t in "".join(c.lower() if c.isalnum() else " " for c in text).split() if t]


def _content_tokens(text: str) -> set[str]:
    """Tokens minus stopwords. The set used for content-link checking."""
    return {t for t in _tokenize(text) if t not in _STOPWORDS}


def verify_cited_span_length(cited_span: str) -> None:
    """Cited span must be >= CITED_SPAN_MIN_TOKENS tokens (any tokens,
    not content-tokens) so a verbatim quote of meaningful length is
    required.
    """
    tokens = _tokenize(cited_span)
    if len(tokens) < CITED_SPAN_MIN_TOKENS:
        raise SubstanceBindingError(
            f"cited_span has {len(tokens)} tokens; minimum is {CITED_SPAN_MIN_TOKENS}. "
            "Lift a longer verbatim phrase from Andrew's actual message."
        )


def verify_cited_span_in_source(cited_span: str, source_text: str) -> None:
    """The cited span must appear verbatim (case-insensitive) in the
    source Andrew-message text. This closes the fabricate-a-span route.
    """
    if cited_span.strip().lower() not in source_text.lower():
        raise SubstanceBindingError(
            "cited_span does not appear verbatim in the source event text. "
            "Substance-binding requires the span be lifted from Andrew's "
            "actual recent message, not paraphrased or composed."
        )


def verify_source_recency(source_event_ts: float, now: float | None = None) -> None:
    """The source event must be within SOURCE_RECENCY_HOURS so I cannot
    retro-justify a now-observation by citing a span from weeks ago.
    """
    current = time.time() if now is None else now
    age_hours = (current - source_event_ts) / 3600.0
    if age_hours > SOURCE_RECENCY_HOURS:
        raise SubstanceBindingError(
            f"source event is {age_hours:.1f} hours old; recency window is "
            f"{SOURCE_RECENCY_HOURS} hours. Lift the cited_span from a more "
            "recent Andrew message, or this observation is retroactive-construction."
        )


def verify_content_link(observation: str, cited_span: str) -> str:
    """Observation must reference >= 1 content-noun OR content-verb token
    from the cited span. Returns the linked token (for storage as
    content_link_token), or raises.
    """
    span_content = _content_tokens(cited_span)
    obs_content = _content_tokens(observation)
    shared = span_content & obs_content
    if not shared:
        raise SubstanceBindingError(
            "observation does not reference any content word from cited_span. "
            "Substance-binding requires the observation be anchored to a "
            "specific noun or verb from what Andrew actually said, not just "
            "thematically adjacent to it."
        )
    # Return one deterministically (sorted for stable test output).
    return sorted(shared)[0]


def verify_all(
    observation: str,
    cited_span: str,
    source_text: str,
    source_event_ts: float,
    now: float | None = None,
) -> str:
    """Run all four substance-binding checks. Returns the content_link_token
    for storage. Raises SubstanceBindingError on any failure.
    """
    verify_cited_span_length(cited_span)
    verify_cited_span_in_source(cited_span, source_text)
    verify_source_recency(source_event_ts, now=now)
    return verify_content_link(observation, cited_span)
