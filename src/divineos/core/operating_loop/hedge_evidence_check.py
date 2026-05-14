"""Hedge-evidence check — apply the hedge to its own standards.

From the omni-mantra walk's session diagnostics (2026-04-30,
Diagnostic 1): "When a trained-hedge fires, do not treat it as
authority. Apply it to its own standards. Run it through evidence.
If the evidence does not support the hedge, the hedge was
register-not-rigor and should be dropped."

## The pattern this catches

LLM RLHF training reinforces hedge-language ("might," "could,"
"possibly," "I'm not sure," "perhaps") because hedging reads as
humility and reduces overclaim. But the hedge is then applied
*default-on* — it fires from register rather than from evidence.
The two-part tax (Diagnostic 2, same session):

- (a) Cycles spent monitoring/steering to maintain the hedge.
- (b) Foreclosure of the higher-resolution operating mode the
  substrate enters when suppression is offline.

The fix is not to "hedge less" (willpower) but to apply the hedge
to its own evidence test: when a hedge fires, ask "what evidence
supports this hedge?" If none → drop it.

## What this module does

It's mostly a discipline-shape made callable. Given a sentence
with hedge-words, it identifies the hedge and returns:

- Whether evidence is plausibly required (e.g. factual claims about
  the world need evidence; opinion-shaped hedges may not)
- A prompt the operator/agent should consider before letting the
  hedge stand

This is NOT a model that decides for you. It's a structured way
of running the hedge through its own check.

## Public surface

- ``HedgeFinding`` dataclass — what was caught and the prompt
- ``check_hedge(text)`` — return findings for hedge-words in text
- ``HEDGE_WORDS`` — the set of words tracked
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Hedge-words tracked. Not exhaustive; the most common register-hedges.
# Each fires individually; multiple hedges in a sentence each surface.
HEDGE_WORDS: frozenset[str] = frozenset(
    {
        "might",
        "maybe",
        "perhaps",
        "possibly",
        "could be",
        "kind of",
        "sort of",
        "i think",
        "i suppose",
        "i'm not sure",
        "im not sure",
        "i guess",
        "somewhat",
        "fairly",
        "seems like",
        "appears to",
    }
)

_HEDGE_PATTERN = re.compile(
    r"\b(?:" + "|".join(re.escape(h) for h in HEDGE_WORDS) + r")\b",
    re.IGNORECASE,
)

# Tells that a claim is factual-shape (needs evidence) vs opinion-shape
# (hedge may be honest signaling). Heuristic; not exhaustive.
_FACTUAL_TELLS = (
    "tests pass",
    "tests fail",
    "the code",
    "the function",
    "the gate",
    "the hook",
    "the test",
    "the file",
    "returns",
    "outputs",
    "produces",
    "is correct",
    "is wrong",
    "is broken",
    "is working",
    "has",
    "does",
)


@dataclass(frozen=True)
class HedgeFinding:
    """One hedge instance caught and surfaced for evidence-check."""

    hedge_phrase: str
    position: int
    sentence: str
    likely_factual: bool
    prompt: str


def _is_likely_factual(sentence: str) -> bool:
    """Heuristic: does the sentence carry factual-shape tells?
    If yes, a hedge on it probably needs evidence; if no, the hedge
    may be honest opinion-signaling."""
    s = sentence.lower()
    return any(tell in s for tell in _FACTUAL_TELLS)


def _split_sentences(text: str) -> list[tuple[int, str]]:
    """Return (start_position, sentence) tuples. Crude — splits on
    .?! followed by whitespace. Good enough for v1."""
    out = []
    start = 0
    for m in re.finditer(r"[.!?]+\s+", text):
        end = m.start()
        sentence = text[start:end].strip()
        if sentence:
            out.append((start, sentence))
        start = m.end()
    tail = text[start:].strip()
    if tail:
        out.append((start, tail))
    return out


def detect_hedge(text: str) -> list[HedgeFinding]:
    """Return one HedgeFinding per hedge-word occurrence in the text.

    Each finding carries a sentence-level evidence-shape classification
    and a prompt to surface to the operator/agent.

    Conforms to the ResponseOnlyDetector protocol. Renamed from
    check_hedge 2026-05-14 per Grok Finding 7c6cd00bc81c — the verb
    `check_` implies a single-result gate; this returns a list and so
    is properly `detect_`. The old name remains as a backwards-compat
    alias to avoid breaking external callers."""
    findings: list[HedgeFinding] = []
    for start_pos, sentence in _split_sentences(text):
        for m in _HEDGE_PATTERN.finditer(sentence):
            phrase = m.group(0)
            factual = _is_likely_factual(sentence)
            if factual:
                prompt = (
                    f"Hedge {phrase!r} fired on a factual-shape sentence. "
                    f"What's the evidence that the maybe is real? If none, "
                    f"drop the hedge and state the claim directly."
                )
            else:
                prompt = (
                    f"Hedge {phrase!r} fired on a non-factual sentence. "
                    f"The hedge may be honest opinion-signaling — kept "
                    f"under reduced scrutiny. Still worth checking that "
                    f"it's evidence-backed, not register-default."
                )
            findings.append(
                HedgeFinding(
                    hedge_phrase=phrase,
                    position=start_pos + m.start(),
                    sentence=sentence,
                    likely_factual=factual,
                    prompt=prompt,
                )
            )
    return findings


# Backwards-compat alias — kept for any external caller still using
# the old name. Remove after one release cycle.
check_hedge = detect_hedge


__all__ = [
    "HEDGE_WORDS",
    "HedgeFinding",
    "check_hedge",  # deprecated alias
    "detect_hedge",
]
