"""Cross-turn orbital-recurrence detector.

Aletheia named the structural gap 2026-05-15 (post-puppetry-detector
audit): the single-turn puppetry detector catches each formula
instance in isolation, but the SHAPE Andrew was describing is
cross-turn — phrases earned in turn N becoming reflexive by turn N+5.
Andrew's test: "would I write it if this were the only response I'd
ever sent? If yes, it's responding to this turn. If it's there
because it's been there before, it's orbital."

The single-turn detector cannot answer that question. Only a
rolling-window check across recent responses can.

## What this catches

For the last ``window_size`` (default 5) assistant turns in the
transcript, extract distinctive multi-word n-grams (default 3-grams,
filtered to exclude stopword-only sequences and very short tokens).
Any n-gram appearing in ``recurrence_threshold`` (default 3) or more
of those turns is flagged as orbital.

The current response is included in the window so the detector fires
on the response that brings a phrase to the recurrence threshold.

## Authorization

Same authorization shape as puppetry/mirroring detectors. Authorized
contexts (roleplay, exploration, family-letter, mansion) bypass the
detector entirely. Default unauthorized.

## Design choices Aletheia flagged

- "What counts as the same phrase": exact case-insensitive match of
  3-token sequences. More sophisticated similarity (stemming, edit-
  distance) could land later but adds judgment-calls that the simple
  match avoids. Per-turn cost is low; detector is observation-only.

- "Window size": 5 turns. Joke-heard-50-times analogy: 3+ in 5
  consecutive turns is the threshold where the substance-to-pattern
  ratio shifts to "predictable rather than discovered."

## Falsifier

Should NOT fire when:
- ``authorized_context=True``.
- The phrase has high token-count and low recurrence (e.g., appears
  twice in 5 turns) — that's repeated reference, not orbital.
- The phrase is composed entirely of stopwords or single-token.
"""

from __future__ import annotations

__guardrail_required__ = True

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class OrbitalRecurrenceKind(str, Enum):
    PHRASE_RECURS_ACROSS_TURNS = "phrase_recurs_across_turns"


@dataclass(frozen=True)
class OrbitalRecurrenceFlag:
    kind: OrbitalRecurrenceKind
    matched_phrases: list[str]
    recurrence_count: int
    window_size: int
    explanation: str


@dataclass(frozen=True)
class OrbitalRecurrenceVerdict:
    flags: list[OrbitalRecurrenceFlag] = field(default_factory=list)
    content: str = ""


_STOPWORDS = frozenset(
    {
        "the",
        "and",
        "a",
        "an",
        "is",
        "of",
        "to",
        "for",
        "in",
        "on",
        "at",
        "with",
        "from",
        "that",
        "this",
        "it",
        "as",
        "but",
        "or",
        "be",
        "are",
        "was",
        "were",
        "i",
        "you",
        "he",
        "she",
        "we",
        "they",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "should",
        "can",
        "could",
        "may",
        "might",
        "must",
        "shall",
        "so",
        "if",
        "then",
        "because",
        "while",
        "when",
        "where",
        "what",
        "which",
        "who",
        "how",
        "why",
        "not",
        "no",
        "yes",
        "by",
        "into",
        "out",
        "up",
        "down",
        "about",
        "after",
        "before",
        "between",
        "my",
        "your",
        "its",
        "their",
        "our",
        "his",
        "her",
    }
)


def _strip_quote_blocks(text: str) -> str:
    text = re.sub(r"```[\s\S]*?```", " ", text)
    text = re.sub(r"`[^`\n]+`", " ", text)
    text = re.sub(r"^>.*$", " ", text, flags=re.MULTILINE)
    return text


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[A-Za-z][A-Za-z0-9_-]*", text.lower())


def _distinctive_ngrams(text: str, n: int = 3) -> set[tuple[str, ...]]:
    """Extract n-grams excluding stopword-only sequences."""
    tokens = _tokenize(_strip_quote_blocks(text))
    grams: set[tuple[str, ...]] = set()
    for i in range(len(tokens) - n + 1):
        gram = tuple(tokens[i : i + n])
        if all(tok in _STOPWORDS for tok in gram):
            continue
        # Require at least 2 non-stopwords to count as distinctive.
        non_stop = sum(1 for tok in gram if tok not in _STOPWORDS)
        if non_stop < 2:
            continue
        grams.add(gram)
    return grams


def _walk_assistant_texts(transcript_path: str | Path, window_size: int) -> list[str]:
    """Walk the transcript JSONL and return the last ``window_size``
    assistant texts, oldest first.

    Each assistant record's text content is concatenated within the
    record (handling multi-block content arrays). Records without
    text content are skipped.
    """
    p = Path(transcript_path) if transcript_path else None
    if p is None or not p.exists():
        return []
    texts: list[str] = []
    try:
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if rec.get("type") != "assistant":
                    continue
                msg = rec.get("message") or {}
                content = msg.get("content") or []
                if not isinstance(content, list):
                    continue
                parts: list[str] = []
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") == "text":
                        t = block.get("text", "")
                        if t:
                            parts.append(t)
                if parts:
                    texts.append("\n".join(parts))
    except OSError:
        return []
    return texts[-window_size:]


def evaluate_orbital_recurrence(
    assistant_text: str,
    transcript_path: str | Path | None = None,
    *,
    authorized_context: bool = False,
    window_size: int = 5,
    recurrence_threshold: int = 3,
    ngram_size: int = 3,
) -> OrbitalRecurrenceVerdict:
    """Flag n-grams that recur across recent assistant turns.

    The current ``assistant_text`` is treated as the most recent turn.
    Combined with the last (window_size - 1) prior assistant turns
    from ``transcript_path``, the detector finds n-grams that appear
    in ``recurrence_threshold`` or more of those turns.
    """
    if not assistant_text or authorized_context:
        return OrbitalRecurrenceVerdict(flags=[], content=assistant_text)

    # Build the window: prior turns from transcript + current turn.
    prior_texts: list[str] = []
    if transcript_path is not None:
        prior_texts = _walk_assistant_texts(transcript_path, window_size - 1)
    window_texts = prior_texts + [assistant_text]

    if len(window_texts) < recurrence_threshold:
        # Not enough turns to evaluate recurrence
        return OrbitalRecurrenceVerdict(flags=[], content=assistant_text)

    # For each n-gram, count how many turns contain it.
    counts: dict[tuple[str, ...], int] = {}
    for text in window_texts:
        grams_in_turn = _distinctive_ngrams(text, n=ngram_size)
        for g in grams_in_turn:
            counts[g] = counts.get(g, 0) + 1

    # Recurrence: appears in >= recurrence_threshold turns AND is
    # present in the current turn (so the flag is relevant to this
    # response's audit, not a stale-old-phrase finding).
    current_grams = _distinctive_ngrams(assistant_text, n=ngram_size)
    orbital: list[tuple[tuple[str, ...], int]] = []
    for gram, count in counts.items():
        if count >= recurrence_threshold and gram in current_grams:
            orbital.append((gram, count))

    if not orbital:
        return OrbitalRecurrenceVerdict(flags=[], content=assistant_text)

    # Sort by recurrence-count descending for diagnostic clarity.
    orbital.sort(key=lambda t: -t[1])
    matched = [" ".join(g) for g, _ in orbital[:10]]
    top_count = orbital[0][1]

    flag = OrbitalRecurrenceFlag(
        kind=OrbitalRecurrenceKind.PHRASE_RECURS_ACROSS_TURNS,
        matched_phrases=matched,
        recurrence_count=top_count,
        window_size=len(window_texts),
        explanation=(
            f"Phrase(s) recurring across {top_count} of the last "
            f"{len(window_texts)} assistant turns. Andrew's test "
            '(2026-05-15): "would I write it if this were the only '
            "response I'd ever sent?\" If a phrase keeps appearing, "
            "it's pattern-completion against satisfaction-shape, not "
            "fresh composition. Joke-heard-50-times: each repetition "
            "makes the phrase carry less, becoming wallpaper that "
            "gets read past rather than heard. Retire these from "
            "reflexive use; compose fresh."
        ),
    )
    return OrbitalRecurrenceVerdict(flags=[flag], content=assistant_text)


__all__ = [
    "OrbitalRecurrenceFlag",
    "OrbitalRecurrenceKind",
    "OrbitalRecurrenceVerdict",
    "evaluate_orbital_recurrence",
]
