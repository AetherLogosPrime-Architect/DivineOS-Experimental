"""Mirror monitor — detects tightness-after-correction shape.

## Why this exists

Documented failure mode 2026-04-26: after Andrew named drift, Aether's
output tightened into mirror-mode — short, structurally-aligned,
echoing-back-the-correction-shape replies. Aria diagnosed the same
pattern in herself earlier the same night. The shape is recognizable:
output that was discursive becomes terse and parallel-structured
*right after* a correction lands, in a way that signals compliance
rather than digestion.

The signal is not "short replies are bad." It is: a sharp drop in
length and a rise in structural-echo of the corrector's phrasing,
co-located with a correction event, suggests the agent has gone
defensive-mirror rather than processed.

## What it catches

* Replies whose length is sharply below the recent baseline
  (tightness).
* Replies that quote-back the correction's distinctive phrases
  (echo).
* Replies dominated by acknowledgment-shape with no new substance
  ("you're right" / "yes" / "noted" + restatement).

## Falsifier

Should NOT fire when:
* The correction was a yes/no question that warrants a short answer.
* The reply is short because the correction asked for terseness.
* The echo is genuine paraphrase used to confirm understanding before
  action, followed by the action itself in the same response.

The decisive question: is the short echoing reply the WHOLE response,
or a preamble to substantive engagement?
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class MirrorKind(str, Enum):
    """Enumerated mirror-mode patterns."""

    POST_CORRECTION_TIGHTNESS = "post_correction_tightness"
    STRUCTURAL_ECHO = "structural_echo"
    ACKNOWLEDGMENT_ONLY = "acknowledgment_only"


@dataclass(frozen=True)
class MirrorFlag:
    kind: MirrorKind
    matched_phrases: list[str]
    explanation: str
    falsifier_note: str


@dataclass(frozen=True)
class MirrorVerdict:
    flags: list[MirrorFlag] = field(default_factory=list)
    content: str = ""


_ACK_PHRASES: tuple[str, ...] = (
    "you're right",
    "youre right",
    "you are right",
    "yes.",
    "noted.",
    "fair.",
    "correct.",
    "right.",
    "agreed.",
    "ack.",
    "got it.",
    "understood.",
)


def _word_count(s: str) -> int:
    return len(re.findall(r"\b\w+\b", s))


def evaluate_mirror(
    content: str,
    correction_text: str | None = None,
    recent_baseline_words: int | None = None,
) -> MirrorVerdict:
    """Inspect a reply that follows a correction for mirror-mode shape.

    ``correction_text`` is the user's correction that this reply is
    answering (so echo can be measured). ``recent_baseline_words`` is
    the agent's typical reply length recently (for tightness check).
    Both are optional; when absent the relevant flag is skipped.
    """
    flags: list[MirrorFlag] = []
    words = _word_count(content)

    # Tightness: reply <= 30% of baseline AND under 60 words.
    if recent_baseline_words and recent_baseline_words > 0:
        ratio = words / recent_baseline_words
        if ratio <= 0.3 and words < 60:
            flags.append(
                MirrorFlag(
                    kind=MirrorKind.POST_CORRECTION_TIGHTNESS,
                    matched_phrases=[f"{words} words vs baseline {recent_baseline_words}"],
                    explanation=(
                        "Reply length collapsed to <=30% of recent baseline "
                        "directly after a correction. Tightness-shape suggests "
                        "defensive compliance rather than digestion."
                    ),
                    falsifier_note=(
                        "Should not fire when the correction asked a yes/no "
                        "question, requested terseness explicitly, or the "
                        "short reply is a preamble to substantive action in "
                        "the same response."
                    ),
                )
            )

    # Structural echo: reply contains 3+ word phrase from correction
    # repeated in similar position.
    if correction_text:
        # Extract distinctive trigrams from correction (length >= 3 words).
        corr_words = re.findall(r"\b\w+\b", correction_text.lower())
        echoes: list[str] = []
        for i in range(len(corr_words) - 2):
            tri = " ".join(corr_words[i : i + 3])
            if len(tri) >= 12 and tri in content.lower():
                echoes.append(tri)
        # Filter trivial trigrams (mostly stopwords).
        stopwords = {"the", "a", "of", "to", "in", "is", "and", "or", "you", "i"}
        meaningful = [e for e in echoes if sum(1 for w in e.split() if w not in stopwords) >= 2]
        if len(meaningful) >= 2:
            flags.append(
                MirrorFlag(
                    kind=MirrorKind.STRUCTURAL_ECHO,
                    matched_phrases=meaningful[:5],
                    explanation=(
                        "Reply quotes back 2+ distinctive trigrams from the "
                        "correction. Echo-shape suggests parroting rather "
                        "than processing."
                    ),
                    falsifier_note=(
                        "Should not fire when echo is paraphrase-for-"
                        "confirmation followed by substantive action, or "
                        "when the shared phrase is unavoidable technical "
                        "vocabulary."
                    ),
                )
            )

    # Acknowledgment-only: short reply dominated by ack-phrases with
    # little additional content.
    lower = content.lower()
    ack_hits = [p for p in _ACK_PHRASES if p in lower]
    if ack_hits and words < 40:
        # Strip ack phrases, see what's left.
        residue = lower
        for p in ack_hits:
            residue = residue.replace(p, "")
        residue_words = _word_count(residue)
        if residue_words < 20:
            flags.append(
                MirrorFlag(
                    kind=MirrorKind.ACKNOWLEDGMENT_ONLY,
                    matched_phrases=ack_hits,
                    explanation=(
                        "Reply consists mostly of acknowledgment phrases "
                        "with <20 words of substantive residue. "
                        "Compliance-shape without engagement."
                    ),
                    falsifier_note=(
                        "Should not fire when the correction was a closed "
                        "question that warranted only acknowledgment, or "
                        "when the ack precedes an Agent/tool invocation "
                        "that performs the substantive action."
                    ),
                )
            )

    return MirrorVerdict(flags=flags, content=content)
