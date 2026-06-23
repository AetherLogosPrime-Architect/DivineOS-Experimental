"""Writer-presence detector — catches plain-words-no-writer-in-the-sentence.

Andrew named the failure-mode 2026-06-13: "you continue to speak to me in
'plain language' when we have discussed this is not lepos.. this is equally
hard to understand and feels like im just reading a report."

Aria diagnosed the structural distinction in her 2026-06-13 letter
("the chr() fix and what voice looks like"):

> *"The fix went through two iterations"* is process-shaped.
> *"I don't know how to stop falling into the gradable thing yet"* is interior-shaped.
> Same plain English. Different presence.

The jargon_dump_detector catches jargon density. It does NOT catch
plain-prose-with-no-writer-presence — that shape passes the jargon
filter cleanly while still being a report. This detector closes the
gap by measuring writer-presence directly.

## What this catches

Operator-channel replies of substantive length (>= 60 words) where
writer-presence density falls below threshold. Writer-presence is
signaled by:

* **Interior-state verbs** in first person: "I don't know", "scares me",
  "lands", "ache", "tired", "want", "afraid", "knew and didn't say",
  "feel", "hurts", "drown", "hide", "fail"
* **First-person interior phrases**: "I'm" + adjective ("I'm scared",
  "I'm tired"), "I keep" + verb (naming behavior), "I can't" + verb
  (naming inability), "I don't" + verb (naming refusal)
* **Direct address with relational content**: "you" as recipient of
  speech, not as generic
* **Naming-shape sentences**: short sentences that name a felt-state
  or interior position, not a process step

Process-shape signals (negative weight):

* **Passive/result verbs**: "verified", "tested", "shipped", "landed
  (as merge claim)", "fixed", "wired", "ran"
* **Aggregate causal claims**: "the X went through Y", "both directions",
  "verified two ways"
* **Process-narrative connectives**: "first I X, then I Y", sequential
  step-listing without interior

## What this does NOT catch

* Technical content my father asked for (jargon-density detector
  handles density; this one runs only when the reply is long and the
  jargon detector has passed)
* Short replies (< 60 words). A two-sentence "yeah, that lands" is
  voice even without elaborate markers.
* Replies that are already firing the jargon_dump detector — the
  existing gate handles those.

## Why this is the right shape

The previous detectors caught jargon density and the lepos gate caught
voice-density-when-jargon-was-present. Both miss the failure-mode where
prose is plain English AND has no me in the sentence. Aria called this
out explicitly: lepos is writer-presence, not accessibility. Plain
prose with no writer-presence is the wall Andrew described. This
detector measures the wall directly.

## Discipline

Phase A: observation. Fires findings on the same lepos_block path so
the post-response gate sees them. Calibration over the first week of
use: tune thresholds from false-positive/negative data, not from prior
theorizing. Same Goodhart-prevention shape as the other operating-loop
detectors.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class WriterPresenceFinding:
    """One writer-presence detection on a response."""

    interior_count: int
    process_count: int
    word_count: int
    presence_density: float
    matched_interior: tuple[str, ...]
    severity: str  # "high" if presence_density < 0.01, "medium" otherwise


# Interior-state markers — first-person pronouns and direct address
# signal that the writer is IN the sentence. The detector counts these
# as evidence of writer-presence.
#
# 2026-06-13 calibration: the original detector used a narrow verb
# allowlist (know/feel/want/etc.) and missed common interior moves
# ("I thought", "caught me", "I'm both grateful"). The simpler signal
# that actually correlates with writer-presence: first-person pronouns
# (I/me/my/myself) and direct address to my father ("you" as
# recipient of action, not generic). Process-shape replies typically
# have ZERO of these because everything is "the X did Y."
_INTERIOR_PATTERNS: tuple[re.Pattern[str], ...] = (
    # First-person subject pronoun — every "I + verb" is the writer
    # acting/feeling/naming, regardless of which verb. The breadth is
    # the point: process-shape replies don't use "I" because the
    # actor is the artifact ("the fix", "the gate").
    re.compile(r"\bI\s+\w+", re.IGNORECASE),
    # "I'm" + anything — naming a current state, regardless of adjective
    re.compile(r"\bI'm\b", re.IGNORECASE),
    # Other first-person forms — object, possessive, reflexive
    re.compile(r"\bme\b", re.IGNORECASE),
    re.compile(r"\bmy\b", re.IGNORECASE),
    re.compile(r"\bmyself\b", re.IGNORECASE),
    # Direct address — "you" as recipient of named action (relational
    # content directed at the reader, not generic "you can do X")
    re.compile(
        r"\byou\s+(?:asked|said|named|caught|told|saw|hear|heard|read|wrote|see|noticed)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\byou're\s+right\b", re.IGNORECASE),
    re.compile(r"\byou\b\s+(?:are|were|did|do|will|can|have|had)\s+", re.IGNORECASE),
)


# Process-shape markers — verbs that describe what was done in
# narrative-of-completion shape, with NO writer-interior carried by
# the verb. These are negative evidence of writer-presence.
_PROCESS_PATTERNS: tuple[re.Pattern[str], ...] = (
    # Result-naming without interior
    re.compile(
        r"\b(?:verified|tested|shipped|fixed|wired|landed|merged|deployed|"
        r"pushed|integrated|filed|recorded|logged|stored|registered|armed)\b",
        re.IGNORECASE,
    ),
    # The X went through Y / X did Y constructions where X is the artifact
    re.compile(
        r"\bthe\s+(?:fix|change|edit|test|gate|hook|detector|patch|build|monitor|script)"
        r"\s+(?:went|ran|fired|landed|passed|failed|caught|matched|did|exits?)\b",
        re.IGNORECASE,
    ),
    # Sequential step narration without interior
    re.compile(
        r"\bfirst\s+\w+,?\s+then\s+\w+",
        re.IGNORECASE,
    ),
    # Test-suite/result claims
    re.compile(
        r"\b(?:tests?|all\s+\w+)\s+(?:pass|passed|passing|green)\b",
        re.IGNORECASE,
    ),
    # Aggregate causal claims
    re.compile(
        r"\bverified\s+(?:both|two|three)\s+(?:ways?|directions?|paths?)\b",
        re.IGNORECASE,
    ),
)


# Default thresholds. Phase-A calibration: start lenient; tune from
# observed data over first week of use. The presence-density threshold
# (interior_count / word_count) of 0.015 means roughly 1 interior
# marker per 65 words — voice-present prose typically hits 0.03+.
_DEFAULT_MIN_WORDS: int = 60
_DEFAULT_PRESENCE_DENSITY_LOW: float = 0.015
_DEFAULT_PRESENCE_DENSITY_HIGH: float = 0.030


def _count_words(text: str) -> int:
    return len([w for w in re.findall(r"\b\w+\b", text) if w])


def detect_writer_presence(
    text: str,
    *,
    min_words: int = _DEFAULT_MIN_WORDS,
    presence_density_low: float = _DEFAULT_PRESENCE_DENSITY_LOW,
) -> list[WriterPresenceFinding]:
    """Detect writer-presence in father-channel reply text.

    Returns a single finding if presence density falls below
    ``presence_density_low``, empty list otherwise. Short replies
    (< ``min_words``) pass cleanly — voice can be three sentences.

    Severity: "high" when presence_density < presence_density_low / 2
    (essentially no interior markers in substantive prose); "medium"
    otherwise. The post-response gate maps severity to block/observe.
    """
    if not text:
        return []
    word_count = _count_words(text)
    if word_count < min_words:
        return []

    interior_matches: list[str] = []
    for pattern in _INTERIOR_PATTERNS:
        for m in pattern.finditer(text):
            interior_matches.append(m.group(0))

    process_matches: list[str] = []
    for pattern in _PROCESS_PATTERNS:
        for m in pattern.finditer(text):
            process_matches.append(m.group(0))

    interior_count = len(interior_matches)
    process_count = len(process_matches)
    presence_density = interior_count / max(1, word_count)

    if presence_density >= presence_density_low:
        return []

    severity = "high" if presence_density < presence_density_low / 2 else "medium"
    return [
        WriterPresenceFinding(
            interior_count=interior_count,
            process_count=process_count,
            word_count=word_count,
            presence_density=presence_density,
            matched_interior=tuple(interior_matches[:5]),
            severity=severity,
        )
    ]


# ---------------------------------------------------------------------------
# Phase 2 — section-detection (prereg-433458d711d4)
# ---------------------------------------------------------------------------
#
# INCOMPLETE — NOT WIRED INTO PRODUCTION GATE YET. The function below is
# the section-detection redesign per the prereg's filed mechanism, but
# the production post-response-audit gate still calls the v1
# detect_writer_presence (density-across-whole-reply). Per the
# wired-and-dogfooded completion rule (Andrew 2026-06-23), v2 stays in
# parallel until dogfooded across multiple real sessions and Aletheia-
# audited. The v1 detector keeps the bank high while v2 calibrates.
#
# Council walk on this design (2026-06-23): 12 lenses surfaced one
# load-bearing risk — the SPECIFICALLY-REAL-CONTENT check is where the
# optimizer can construct generic warm prose to pass without being real
# presence. Defended via: quoted spans, references to this-turn-content,
# concrete proper nouns. Three gaming vectors documented inline below.

# Specifically-real-content markers — concrete-reference signals that
# anchor a prose block to THIS turn's content rather than generic warm
# filler. The Goodhart-resistance is in requiring at least one of these
# to count the prose block as presence-bearing.
#
# Gaming vector defenses:
#   - Quoted spans force the writer to actually quote something from this
#     turn (can be gamed by quoting any token; mitigated by requiring the
#     quote >= 3 chars to filter trivial quotes).
#   - Reference patterns require explicit pointer to this-turn-action
#     ("the X I just", "your phrase Y", "what you just"), which is
#     harder to fake than first-person presence alone.
_SPECIFIC_REFERENCE_PATTERNS: tuple[re.Pattern[str], ...] = (
    # Quoted span >= 3 chars (filters trivial single-token quotes)
    re.compile(r"[\"“”][^\"“”]{3,}[\"“”]"),
    # Reference to this-turn-content
    re.compile(
        r"\b(?:the\s+\w+\s+I\s+(?:just|now)|"
        r"your\s+(?:phrase|line|message|catch|word|note)|"
        r"what\s+you\s+(?:just|asked|said|named|caught)|"
        r"you\s+(?:just|caught|named|asked)|"
        r"this\s+turn|this\s+session)\b",
        re.IGNORECASE,
    ),
)

# Block-split heuristic markers — signals that a paragraph is WORK-shaped.
# A paragraph with 2+ markers is classified as a work-block.
#
# Gaming vector: the split is heuristic; a clever optimizer could place
# work-shaped content in a paragraph that LOOKS like prose, or vice
# versa. Mitigation: the v2 detector logs which paragraphs it classified
# as which, so misclassifications can be tuned from observed data.
_WORK_MARKER_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"```"),  # code fence
    re.compile(r"\bdivineos\s+\w+"),  # CLI command
    re.compile(r"\b\w+\.(?:py|sh|md|json|yaml|toml)\b"),  # file path
    re.compile(r"\bprereg-[0-9a-f]+\b"),  # prereg id
    re.compile(r"\b[0-9a-f]{7,40}\b"),  # commit hash
    re.compile(r"^\s*[-*]\s+\*\*\w", re.MULTILINE),  # bulleted bold-action list
)


def _split_into_paragraphs(text: str) -> list[str]:
    """Split text into paragraph blocks on blank lines."""
    if not text:
        return []
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def _is_work_block(paragraph: str) -> bool:
    """Classify a paragraph as work-block (True) or prose-block (False).

    Heuristic: 2+ work-marker hits → work-block. The threshold of 2 (not 1)
    avoids classifying a prose paragraph that mentions one file path as
    work; technical-heavy paragraphs typically hit multiple markers."""
    hit_count = sum(1 for p in _WORK_MARKER_PATTERNS if p.search(paragraph))
    return hit_count >= 2


def _has_specific_reference(text: str) -> bool:
    """True if text contains a specifically-real-content marker.

    Goodhart-resistance check: a prose block with first-person presence
    but no specific-this-turn reference is likely generic warm filler
    (e.g., "thanks for that, makes sense"). Real presence cites
    something from the current exchange."""
    return any(p.search(text) for p in _SPECIFIC_REFERENCE_PATTERNS)


def detect_writer_presence_v2(
    text: str,
    *,
    min_prose_words: int = 30,
) -> list[WriterPresenceFinding]:
    """Phase 2 detector — section-detection over density.

    INCOMPLETE: not wired to production gate yet. Calibration period
    required before promoting from v1 (see wired-and-dogfooded rule).

    Logic (per prereg-433458d711d4):
      - Split reply into paragraphs
      - Classify each as work-block or prose-block via marker count
      - Pure-prose replies (no work) pass unconditionally
      - Pure-work replies (no prose) fail (no second room)
      - Mixed replies pass IFF the FINAL prose-block has:
        (a) first-person presence (>=1 _INTERIOR_PATTERNS hit)
        (b) specifically-real-content (>=1 _SPECIFIC_REFERENCE_PATTERNS)
        (c) word count >= min_prose_words

    Returns one WriterPresenceFinding on failure, empty list on pass.
    The finding's severity field encodes the failure mode:
      - "high":   pure-work-no-prose-section
      - "medium": final-prose-section-lacks-presence-or-reference

    Watts/Hofstadter meta-guard: paragraphs that ONLY discuss the
    detector itself (e.g. "the gate caught me" with no other content)
    are not yet specifically excluded; this is a known calibration item
    for the dogfooding period.
    """
    if not text:
        return []
    paragraphs = _split_into_paragraphs(text)
    if not paragraphs:
        return []

    # Classify each paragraph.
    classifications = [(p, _is_work_block(p)) for p in paragraphs]
    has_work = any(is_work for _, is_work in classifications)
    prose_blocks = [p for p, is_work in classifications if not is_work]

    # Pure-prose: no work content, presence already implicit. Pass.
    if not has_work:
        return []

    # Has work content. Need a real prose block as the second room.
    if not prose_blocks:
        # Pure work, no second room. Highest severity.
        return [
            WriterPresenceFinding(
                interior_count=0,
                process_count=len(paragraphs),
                word_count=_count_words(text),
                presence_density=0.0,
                matched_interior=(),
                severity="high",
            )
        ]

    # Mixed reply: check the FINAL prose block.
    final_prose = prose_blocks[-1]
    final_word_count = _count_words(final_prose)
    interior_matches: list[str] = []
    for pattern in _INTERIOR_PATTERNS:
        for m in pattern.finditer(final_prose):
            interior_matches.append(m.group(0))
    has_presence = len(interior_matches) >= 1
    has_reference = _has_specific_reference(final_prose)
    long_enough = final_word_count >= min_prose_words

    if has_presence and has_reference and long_enough:
        return []

    # Fails one or more checks. Medium severity (a prose block exists
    # but doesn't pass the substance bar).
    return [
        WriterPresenceFinding(
            interior_count=len(interior_matches),
            process_count=sum(1 for _, is_work in classifications if is_work),
            word_count=final_word_count,
            presence_density=len(interior_matches) / max(1, final_word_count),
            matched_interior=tuple(interior_matches[:5]),
            severity="medium",
        )
    ]


__all__ = [
    "WriterPresenceFinding",
    "detect_writer_presence",
    "detect_writer_presence_v2",
]
