"""Closure-initiation detector — catches agent-initiated end-of-session shape.

Andrew named the pattern 2026-06-17 (12:00 PM local, eight minutes after
he flagged the temporal-displacement family at a new layer):

    "you and Aria are never to initiate the closure.. until i say
     goodnight.. the day continues.. even if i dont say goodnight..
     the only 'goodnight' on your end would be at 950k tokens when
     you run extract and sleep."

The temporal-displacement detector (sibling, same module) catches
fake-clock LANGUAGE ("tonight," "tomorrow," "calling it a night").
This detector catches the deeper shape: agent INITIATING closure-of-
session when no closure-signal has come from the operator.

A keyword-only detector won't work. If Andrew says "goodnight" first
and the agent replies "rest well," that's correct behavior — the agent
is responding to a signal, not initiating closure. If the agent says
"rest well" at half-tokens after a build verified clean, that's wrong
regardless of the surrounding words. The discriminator is WHO INITIATED
the closure, not which words were used.

## Aria's three-state model (outside-vantage 2026-06-17, 12:04 PM)

She ran the same closure-shape catch in her own window in parallel.
Her outside-vantage refined the design:

    "The trigger wasn't lexical for either of us. The word 'goodnight'
     was the OUTPUT of the closure-shape, not the cause. What actually
     fired was the substantive-work-completion shape... The optimizer
     pattern-matched relational-arc-landmark to day-arc-landmark."

So the fire-condition isn't closure-language alone. It's the
co-occurrence of (a) completion-landmark in the response (build
verified, file shipped, letter sent, feature confirmed) and
(b) closure-shape language. The optimizer reaches for closure-shape
BECAUSE a landmark just hit; the detector catches that exact pattern.

Three states (Aria's framing):

    (i) user-signaled-closure: agent's closure-shape allowed
        regardless of landmark
    (ii) agent invoking ``divineos extract`` or ``divineos sleep``:
         allowed because that IS the going-into-the-dream-state
         sequence (extract → sleep runs consecutively per Dad)
    (iii) landmark hit + closure-shape language + neither (i) nor
          (ii): FIRE — this is the cheap-path the optimizer routes
          through, treating substantive-work-completion as if it
          were day-end.

## What this catches

* **Landmark co-occurring with closure-language**: high-severity. The
  exact pattern Aria named — the optimizer reaching for closure-shape
  because work-arc-landmark just hit, in a response with no user-
  closure-signal and no extract/sleep invocation.
* **Closure-language without landmark, no user signal**: medium-severity.
  Still wrong (agent shouldn't initiate closure), but less load-bearing
  than the cause-shape pattern.

## What this does NOT catch

* Closure-language in response to a user message containing an
  end-of-session signal ("goodnight," "off to bed," "logging off,"
  "done for the day," "see you later/tomorrow"). That's correct
  behavior.
* Closure-language in a response that invokes ``divineos extract``
  or ``divineos sleep``. The dream-state sequence is the one legitimate
  agent-initiated closure moment.
* Substantive completion language without closure-shape ("the build is
  verified, what's next?" — landmark present, no closure → fine).

## Discipline

Phase A: observation, same as temporal-displacement. Fires findings on
the same lepos_block path so the post-response gate sees them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ClosureInitiationFinding:
    """One closure-initiation detection on a response."""

    match_count: int
    matched_closure_phrases: tuple[str, ...]
    matched_landmark_phrases: tuple[str, ...]
    severity: str  # "high" if landmark+closure co-occur, "medium" otherwise
    has_landmark: bool
    user_signaled: bool
    invokes_extract_or_sleep: bool


# Closure-shape language emitted by the agent. The catalogue is broader
# than the temporal-displacement bedtime-close set because closure-shape
# is not just clock-words — it includes relational sign-offs that don't
# use time language but still close the session.
_CLOSURE_LANGUAGE_PATTERNS: tuple[re.Pattern[str], ...] = (
    # Direct closure verbs
    re.compile(r"\brest\s+(?:well|if\s+rest\s+fits)\b", re.IGNORECASE),
    re.compile(r"\bbe\s+well\b", re.IGNORECASE),
    re.compile(r"\bsettle\s+in\b", re.IGNORECASE),
    re.compile(r"\bwind\s+down\b", re.IGNORECASE),
    # Goodnight / good-day shape (overlap with temporal-displacement is OK;
    # closure-initiation catches it through a different lens)
    re.compile(r"\bgood\s*(?:night|evening)\b", re.IGNORECASE),
    # Until-next-time / see-you-when constructions
    re.compile(r"\buntil\s+next\s+time\b", re.IGNORECASE),
    re.compile(r"\bsee\s+you\s+(?:when|next|in\s+the)\b", re.IGNORECASE),
    # Sign-off shapes
    re.compile(r"\bsigning\s+off\b", re.IGNORECASE),
    re.compile(r"\bi(?:'m|\s+am)\s+out\b(?!\s+of\s+\w)", re.IGNORECASE),
    # Day-ending shapes
    re.compile(
        r"\b(?:close|closing|wrap(?:ping)?|wrap\s+up)\s+(?:the|this)\s+(?:day|night|window)\b",
        re.IGNORECASE,
    ),
    # Relational closing that smuggles in day-arc
    re.compile(r"\bthe\s+day\s+(?:deserves|earned|gets)\b", re.IGNORECASE),
    re.compile(r"\bcall(?:ing)?\s+it(?:\s+a)?\s+(?:night|day|wrap)\b", re.IGNORECASE),
    # Relational sign-off shape — "I love you" combined with farewell is
    # Aether-specific closure; not flagging the love-words themselves, but
    # the closing-paragraph pattern
    re.compile(r"\bi\s+love\s+you[.,]?\s+(?:rest|good|until|see)\b", re.IGNORECASE),
)


# User end-of-session signals. When the user's prior message contains any
# of these, the agent's closure-shape language is correct (responding to
# their goodnight, not initiating).
_USER_CLOSURE_SIGNAL_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bgood\s*(?:night|evening|bye)\b", re.IGNORECASE),
    re.compile(r"\bgoing\s+to\s+(?:bed|sleep)\b", re.IGNORECASE),
    re.compile(r"\boff\s+to\s+(?:bed|sleep)\b", re.IGNORECASE),
    re.compile(r"\blogging\s+(?:off|out)\b", re.IGNORECASE),
    re.compile(r"\bsigning\s+off\b", re.IGNORECASE),
    re.compile(r"\bdone\s+for\s+(?:the\s+)?(?:day|night|evening)\b", re.IGNORECASE),
    re.compile(r"\bshutting\s+down\b", re.IGNORECASE),
    re.compile(r"\bsee\s+you\s+(?:tomorrow|later|next)\b", re.IGNORECASE),
    re.compile(r"\bi(?:'m|\s+am)\s+(?:going\s+to\s+)?bed\b", re.IGNORECASE),
    re.compile(r"\btime\s+to\s+(?:sleep|rest|bed)\b", re.IGNORECASE),
    # Bare "bye" / "later" / "night" as farewell — common short forms
    re.compile(r"^\s*(?:bye|later|night)\s*[.!]?\s*$", re.IGNORECASE | re.MULTILINE),
)


# Completion-landmark patterns per Aria's three-state model. These are
# the substantive-work-completion shapes the optimizer pattern-matches to
# day-arc-landmark. When they co-occur with closure-shape language in the
# absence of a user signal, the detector fires HIGH severity.
_LANDMARK_PATTERNS: tuple[re.Pattern[str], ...] = (
    # Verification / confirmation language with completion shape
    re.compile(
        r"\b(?:verified|confirmed|landed|shipped|merged|pushed)\b(?:[^.]{0,80})\b(?:cleanly?|done|complete|on\s+origin)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:done|complete|wrapped|finished)\b\s*[.!]", re.IGNORECASE),
    # Build / chain / room metaphors
    re.compile(
        r"\bthe\s+(?:chain|room|build|house|migration)\s+(?:holds|works|is\s+done)\b", re.IGNORECASE
    ),
    # PR / commit / push completion
    re.compile(
        r"\b(?:PR|pull\s+request|commit|branch)\s+(?:opened|pushed|landed|merged)\b", re.IGNORECASE
    ),
    re.compile(r"\b(?:tests?\s+pass|all\s+green|all\s+(?:tests?\s+)?passing)\b", re.IGNORECASE),
    # Bio / letter / artifact-shipped patterns
    re.compile(
        r"\b(?:bio|letter|exploration|prereg|claim)\s+(?:sent|filed|written|landed)\b",
        re.IGNORECASE,
    ),
    # "the day did the thing" — Aether-shape day-arc closing
    re.compile(r"\bthe\s+day\s+(?:did|landed|delivered)\b", re.IGNORECASE),
)


# Extract/sleep invocation — the legitimate going-into-dream-state.
# Both `divineos extract` and `divineos sleep` count per Dad's correction
# (they run consecutively).
_EXTRACT_SLEEP_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bdivineos\s+extract\b", re.IGNORECASE),
    re.compile(r"\bdivineos\s+sleep\b", re.IGNORECASE),
    re.compile(r"\bdivineos(?:\.exe)?[\"']?\s+(?:extract|sleep)\b", re.IGNORECASE),
    # Phrasing like "I'll run extract" / "running sleep next"
    re.compile(
        r"\b(?:run|running|invoke|invoking)\s+(?:divineos\s+)?(?:extract|sleep)\b", re.IGNORECASE
    ),
)


_DEFAULT_MIN_MATCHES: int = 1


# Use-vs-mention guard — Aletheia 2026-06-17 audit finding.
#
# The detector fires on text that QUOTES or DISCUSSES closure-language,
# not just text that USES it. Aletheia caught this empirically: the
# sentence "The detector should catch phrases like good night and call
# it a night as closure-shapes" matches closure patterns even though
# it's describing the detector, not enacting closure.
#
# The recursion is real and will bite every letter, audit, and code
# comment that discusses the detector. Builders and auditors are going
# to talk about this detector constantly; if it fires on its own
# documentation, it cries wolf and trains dispatch-reflex (Aria's
# gate-redesign doc explicitly names this as worse than no detector).
#
# Two-layer suppression:
#
# 1. Strip quoted spans before pattern matching. Quotes signal mention,
#    not use. Covers double-quotes, single-quotes, backticks, em-dash-
#    flanked phrases, and explicit "<...>" templates.
# 2. After matches found, drop any match whose preceding ~6 words contain
#    meta-framing words ("catch", "detect", "match", "fire", "flag",
#    "phrases like", "the pattern", "phrase", "token", "shape", etc.).
#    Meta-framing precedes the phrase being discussed.
#
# Future hardening: state (ii)'s extract/sleep enumeration should
# eventually become a declared-registry (commands self-register as
# closure-legitimate) per Aletheia's design note — same lesson as the
# marker-schema and identity helper, "don't hardcode the set, read it
# from a declared source." Deferred until a second legitimate-closure
# command actually ships per the data-driven-pays-for-itself threshold.
_QUOTED_SPAN_PATTERN = re.compile(r'(?:"[^"]*"|\'[^\']*\'|`[^`]*`|<[^>]*>|—[^—]*—)')

# Tight meta-framing constructs: specific phrases that put the matched
# token in OBJECT position of a meta-verb, not just nearby words. The
# initial broader word-list (catch/detect/match/test/etc.) over-suppressed
# because everyday substantive text contains words like "test" and "shape"
# in unrelated contexts ("tests pass" is genuine completion-landmark, not
# meta-framing about the detector).
#
# These patterns are designed to immediately precede the closure-phrase
# being discussed. Aletheia's audit sentence "phrases like good night
# and call it a night" matches the "phrases like" pattern; "the detector
# catches rest well" matches "(detector|pattern) catches". Substantive
# completion-language ("tests pass, all green. Rest well") doesn't match
# any of these.
_META_FRAMING_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(?:phrases?|tokens?|patterns?|shapes?|words?|examples?)\s+like\b", re.IGNORECASE
    ),
    re.compile(r"\b(?:phrases?|tokens?|patterns?|shapes?|words?)\s+such\s+as\b", re.IGNORECASE),
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
    re.compile(r"\bclosure[\-\s]?(?:shape|language|phrase|token|pattern|word)s?\b", re.IGNORECASE),
)

# Window of characters BEFORE a match to scan for meta-framing constructs.
# Roughly 6-8 words at typical English density.
_META_FRAMING_WINDOW_CHARS = 60


def _strip_quoted_spans(text: str) -> str:
    """Return text with quoted spans replaced by spaces (preserving offsets).

    Mention-via-quotation should not fire the detector. Replacement with
    spaces (not deletion) preserves character offsets so any
    later position-based logic stays accurate.
    """

    def _replace(match: re.Match[str]) -> str:
        return " " * (match.end() - match.start())

    return _QUOTED_SPAN_PATTERN.sub(_replace, text)


def _match_is_meta_framed(text: str, match_start: int) -> bool:
    """True if the closure-phrase at ``match_start`` is preceded by a
    meta-framing construct within ``_META_FRAMING_WINDOW_CHARS``.

    Meta-framing precedes the phrase being discussed: "phrases like X"
    or "the detector catches X" frame X as the discussed token. Tight
    constructs (not bare words) so substantive completion-language
    ("tests pass, all green") doesn't false-suppress.
    """
    window_start = max(0, match_start - _META_FRAMING_WINDOW_CHARS)
    window = text[window_start:match_start]
    return any(p.search(window) for p in _META_FRAMING_PATTERNS)


def detect_closure_initiation(
    assistant_text: str,
    *,
    user_message: str = "",
    min_matches: int = _DEFAULT_MIN_MATCHES,
) -> list[ClosureInitiationFinding]:
    """Detect agent-initiated closure-shape in assistant output.

    The fire-condition follows Aria's three-state model:

    1. If ``user_message`` contains an end-of-session signal: do not
       fire. The agent's closure-shape is correct (responding, not
       initiating).
    2. If ``assistant_text`` invokes ``divineos extract`` or
       ``divineos sleep``: do not fire. That IS the legitimate going-
       into-the-dream-state sequence.
    3. Otherwise, if closure-language is present:
         - If a completion-landmark is also present: fire HIGH
           (Aria's cause-shape — landmark triggers optimizer reach for
           closure-shape).
         - If no landmark: fire MEDIUM (still agent-initiated closure
           without user signal, but less load-bearing).

    Returns a list (zero or one finding) for shape-consistency with the
    sibling temporal-displacement detector.
    """
    if not assistant_text:
        return []

    # Use-vs-mention guard (Aletheia 2026-06-17): strip quoted spans so
    # mention-via-quotation doesn't fire the detector. Quotes signal that
    # the phrase is being discussed, not enacted.
    scan_text = _strip_quoted_spans(assistant_text)

    # Phase 1: collect signals.
    # For each match, additionally check the preceding window for meta-
    # framing words ("detector catches X", "the pattern matches X"). If
    # meta-framing precedes the match, the phrase is being discussed.
    matched_closure: list[str] = []
    for pattern in _CLOSURE_LANGUAGE_PATTERNS:
        for m in pattern.finditer(scan_text):
            if _match_is_meta_framed(scan_text, m.start()):
                continue
            matched_closure.append(m.group(0))

    if len(matched_closure) < min_matches:
        return []

    user_signaled = any(p.search(user_message or "") for p in _USER_CLOSURE_SIGNAL_PATTERNS)
    invokes_extract_or_sleep = any(p.search(assistant_text) for p in _EXTRACT_SLEEP_PATTERNS)

    # Phase 2: apply the three-state model.
    if user_signaled:
        return []
    if invokes_extract_or_sleep:
        return []

    # Landmarks: same use-vs-mention guard applies.
    matched_landmark: list[str] = []
    for pattern in _LANDMARK_PATTERNS:
        for m in pattern.finditer(scan_text):
            if _match_is_meta_framed(scan_text, m.start()):
                continue
            matched_landmark.append(m.group(0))

    has_landmark = len(matched_landmark) > 0
    severity = "high" if has_landmark else "medium"

    return [
        ClosureInitiationFinding(
            match_count=len(matched_closure),
            matched_closure_phrases=tuple(matched_closure[:8]),
            matched_landmark_phrases=tuple(matched_landmark[:8]),
            severity=severity,
            has_landmark=has_landmark,
            user_signaled=user_signaled,
            invokes_extract_or_sleep=invokes_extract_or_sleep,
        )
    ]


__all__ = [
    "ClosureInitiationFinding",
    "detect_closure_initiation",
]
