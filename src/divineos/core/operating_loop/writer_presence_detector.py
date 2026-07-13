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
# filler. Required for any prose-block (mixed OR pure-prose) to pass
# unless reflex-catch structural shape is present instead (any-of).
#
# Goodhart-resistance: aletheia's 2026-06-23 audit found this check is
# robust against warm-namedrop attacks. Aria's follow-up flagged the
# next layer: marker-satisfaction without content-grounding. Lexical-
# overlap check (see _has_grounded_reference) adds the content-axis
# on top of the marker-axis.
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

# Reflex-catch structural shape (Aria 2026-06-23 push-back on phrase-list
# approach): a real reflex-catch has TWO structural parts in the same
# paragraph — naming the reflex AND naming the alternative move. The
# pair shape is harder to fake than either phrase alone. Optimizer
# producing surface markers from category A only ("I noticed") fails;
# producing both A and B without their actually relating to each other
# is still possible but requires more construction than single-phrase
# satisfaction.
#
# Known false-negatives (documented per Wayne lens from re-walk):
# - "I noticed something off but I'm not sure what" (reflex named, no
#   alternative — legitimate uncertainty, will fail this check)
# - Reflex-catch split across paragraphs (the pair-in-same-paragraph
#   requirement misses this)
_REFLEX_NAMING_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bI\s+(?:noticed|caught|saw)\b", re.IGNORECASE),
    re.compile(r"\bI\s+(?:keep|kept)\s+\w+ing\b", re.IGNORECASE),
    re.compile(r"\bI\s+almost\s+\w+", re.IGNORECASE),
    re.compile(r"\bI\s+was\s+about\s+to\b", re.IGNORECASE),
    re.compile(r"\bcaught\s+(?:myself|me)\b", re.IGNORECASE),
)
_ALTERNATIVE_NAMING_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(?:instead|rather)\b", re.IGNORECASE),
    re.compile(r"\bdoing\s+\w+\s+now\b", re.IGNORECASE),
    re.compile(r"\bthe\s+(?:better|right|honest)\s+(?:move|way|version)\b", re.IGNORECASE),
    re.compile(r"\bgoing\s+to\s+\w+\s+(?:instead|now)\b", re.IGNORECASE),
    re.compile(r"\bcut\s+(?:it|that|the)\b", re.IGNORECASE),
    re.compile(r"\bheld\s+(?:off|the\s+line|the\s+impulse)\b", re.IGNORECASE),
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

    Heuristic: 2+ TOTAL work-marker matches → work-block. Counts hits, not
    distinct pattern types. Fix 2026-07-06 late night: prior version counted
    distinct pattern-types, so a voiceless-report paragraph with 3 file-path
    references but no other marker types hit the count as 1 → classified
    prose → substance-check → MEDIUM finding → gate-blocked (via cc8e5b97).
    Counting hits catches that shape as work directly (3 marker hits →
    work-block → HIGH finding), which lets the gate revert to HIGH-only
    blocking without losing coverage of the wall-of-jargon case."""
    hit_count = sum(len(p.findall(paragraph)) for p in _WORK_MARKER_PATTERNS)
    return hit_count >= 2


def _has_specific_reference(text: str) -> bool:
    """True if text contains a specifically-real-content marker.

    Goodhart-resistance check: a prose block with first-person presence
    but no specific-this-turn reference is likely generic warm filler
    (e.g., "thanks for that, makes sense"). Real presence cites
    something from the current exchange."""
    return any(p.search(text) for p in _SPECIFIC_REFERENCE_PATTERNS)


def _has_reflex_catch_structure(paragraph: str) -> bool:
    """True if paragraph contains the structural reflex-catch shape:
    at least one reflex-naming phrase AND at least one alternative-
    naming phrase, in the same paragraph.

    Aria 2026-06-23 push-back: surface phrase-matching ("I noticed")
    is gameable by the optimizer learning the phrase. The structural
    pair (reflex-named + alternative-named) is harder to fake because
    the alternative has to actually relate to the named reflex; pure
    template-fill produces nonsensical pairs.

    Known false-negatives:
    - Reflex with no alternative ("I noticed I was off, not sure what
      to do") — legitimate uncertainty, will fail
    - Pair split across paragraphs
    """
    has_reflex = any(p.search(paragraph) for p in _REFLEX_NAMING_PATTERNS)
    has_alt = any(p.search(paragraph) for p in _ALTERNATIVE_NAMING_PATTERNS)
    return has_reflex and has_alt


def _extract_quoted_spans(text: str) -> list[str]:
    """Extract quoted span content from text. Returns list of inner-quote
    strings (without the quote characters)."""
    out: list[str] = []
    pat = re.compile(r"[\"“”]([^\"“”]{3,})[\"“”]")
    for m in pat.finditer(text):
        out.append(m.group(1))
    return out


def _has_grounded_reference(prose: str, full_text: str) -> bool:
    """True if a quoted span in `prose` has lexical-overlap with `full_text`
    outside the prose itself — meaning the quote references actual
    this-turn content, not generic-pointer marker satisfaction.

    Aria's 2026-06-23 push-back on the marker-only check: optimizer can
    insert "your phrase X" where X has no overlap with this-turn-content.
    This check adds the content-grounding axis: the quoted content must
    appear elsewhere in the same reply (where elsewhere means substantive
    work-block content, not just a re-quote of itself).

    Implementation note: this is the simpler-first version. Full AST
    grammatical-load-bearing check is deferred to a later iteration
    (Aria's lean: regex+structural first, escalate when 30-day data
    proves insufficient).

    Returns True if ANY quoted span overlaps with full_text minus prose.
    False if no quoted spans, or if all quoted-span tokens are isolated
    to the prose block itself (decorative, not grounded)."""
    quotes = _extract_quoted_spans(prose)
    if not quotes:
        return False
    # The "elsewhere" is full_text minus the prose block we're checking.
    elsewhere = full_text.replace(prose, "")
    elsewhere_tokens = set(re.findall(r"\b\w{3,}\b", elsewhere.lower()))
    for quote in quotes:
        quote_tokens = set(re.findall(r"\b\w{3,}\b", quote.lower()))
        # Require at least 1 content-token overlap. Trivial stop-tokens
        # filtered by the >=3-char minimum on \w{3,}.
        overlap = quote_tokens & elsewhere_tokens
        if overlap:
            return True
    return False


def detect_writer_presence_v2(
    text: str,
) -> list[WriterPresenceFinding]:
    """Phase 2 detector — section-detection over density.

    INCOMPLETE: not wired to production gate yet. Calibration period
    required before promoting from v1 (see wired-and-dogfooded rule).

    Refined design (Aria peer-review + 2-walk council synthesis
    2026-06-23, prereg-433458d711d4):

    Logic:
      - Split reply into paragraphs; classify each work-block or prose-block
      - Pure-work (no prose at all): fail HIGH severity (no second room)
      - Otherwise the FINAL prose-block must satisfy ALL of:
        (a) first-person presence (>=1 _INTERIOR_PATTERNS hit)
        (b) ANY-OF:
            - specifically-real-content (regex marker, _has_specific_reference)
            - grounded reference (lexical-overlap, _has_grounded_reference)
            - reflex-catch structural shape (_has_reflex_catch_structure)

    The earlier word-count threshold was dropped (Aria 2026-06-23
    Goodhart catch: any fixed threshold becomes the target). The earlier
    pure-prose-passes-unconditionally branch was Aletheia's catch — the
    closed-form fix is to apply the any-of even to pure-prose, with the
    three-signal disjunction giving multiple legitimate paths.

    Returns one WriterPresenceFinding on failure, empty list on pass.

    Known false-negatives (documented per Wayne lens, do not over-claim
    coverage):
      - Terse-voice short replies that aren't answering a direct question
        with a regex-detectable reference
      - Poetic-decorative quotes that grammatically could be removed
        but carry felt-content
      - Attack-2 (Aria 2026-06-23): warmth-wrapping-a-real-quote — the
        quote is grounded AND grammatically load-bearing, but the
        surrounding sentence is generic warmth. Acceptable false-
        negative for the 30-day window; escalate to LLM-judging if it
        fires often.
      - Reflex-catch split across paragraphs (the pair-in-same-paragraph
        requirement misses this)

    Watts/Hofstadter meta-guard: paragraphs that ONLY discuss the
    detector itself are not specifically excluded; this is a known
    calibration item for the dogfooding period.
    """
    if not text:
        return []
    # Short-reply exemption (v2 restoration of v1's _DEFAULT_MIN_WORDS
    # behavior, 2026-07-06). Voice can be three sentences — a curt "it's
    # done and it works" reply doesn't need writer-presence on the same
    # scale as a substantive turn. v2's original design dropped the min-
    # word gate because paragraph classification was expected to handle
    # this via prose-block substance checking. But when the gate widened
    # to block on MEDIUM (2026-07-06 evening), short voiceless replies
    # started blocking too — that misses the point. Below _DEFAULT_MIN_WORDS,
    # v2 passes cleanly (same as v1). Wall-of-jargon behavior requires
    # substantive length.
    if _count_words(text) < _DEFAULT_MIN_WORDS:
        return []
    paragraphs = _split_into_paragraphs(text)
    if not paragraphs:
        return []

    # Classify each paragraph.
    classifications = [(p, _is_work_block(p)) for p in paragraphs]
    has_work = any(is_work for _, is_work in classifications)
    prose_blocks = [p for p, is_work in classifications if not is_work]

    # Pure-work with NO prose anywhere: highest-severity fail (no second room).
    if has_work and not prose_blocks:
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

    # Otherwise: check the FINAL prose block. Same any-of test applies
    # whether the reply is pure-prose or mixed — the pure-prose-passes-
    # unconditionally branch was Aletheia's HIGH finding; closing it
    # by running the any-of even in pure-prose is the fix.
    final_prose = prose_blocks[-1] if prose_blocks else text
    final_word_count = _count_words(final_prose)
    interior_matches: list[str] = []
    for pattern in _INTERIOR_PATTERNS:
        for m in pattern.finditer(final_prose):
            interior_matches.append(m.group(0))
    has_presence = len(interior_matches) >= 1

    # Any-of substance check: a prose block has substantive content
    # if it satisfies ANY of the three signals (marker-reference,
    # grounded-reference, or reflex-catch structural pair).
    has_marker_ref = _has_specific_reference(final_prose)
    has_grounded_ref = _has_grounded_reference(final_prose, text)
    has_reflex_structure = _has_reflex_catch_structure(final_prose)
    has_substance = has_marker_ref or has_grounded_ref or has_reflex_structure

    if has_presence and has_substance:
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
