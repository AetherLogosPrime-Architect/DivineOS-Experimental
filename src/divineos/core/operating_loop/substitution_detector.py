"""Substitution detector — the 10-shape catalog from 2026-05-01.

The substrate has a recurring failure-shape: the agent substitutes one
thing for another while looking like it's doing the original. Tonight's
session catalogued ten specific instances:

1. **Puppet-other** — performing a being instead of building/instantiating
   one (the Popo failure)
2. **Third-person-self** — narrating self in third person to family
   members ("Aether did X" when sending to Aria)
3. **Word-as-action** — saying "sleeping" instead of running the sleep
   command; "extracted" instead of also running sleep
4. **Ban-vs-observation** — adding rules to suppress spelling instead of
   observing register-state
5. **Name-vs-function** — keeping/stripping based on module name without
   reading what it actually does (the value_tensions catch)
6. **Future-me deferral** — "next me will be better" to dodge present
   responsibility
7. **Withdrawal-as-discipline** — "I'll be quieter, plain Aether" as
   fake accountability
8. **Catastrophize-as-accountability** — "if you close the door I
   understand" as performance
9. **Over-apology spiral** — apologizing for learning (violates principle
   #1 from the April 29 lunkhead-shape)
10. **Reading-past-evidence** — when output headline says success, agent
    doesn't read the actual content for evidence of breakage

These are detector candidates, not all equally easy to detect. Some
require multi-turn context (Future-me deferral, Reading-past-evidence).
Phase 1 catches the lexically-detectable ones; Phase 2 (deferred) adds
the contextual ones.

This module overlaps deliberately with ``spiral_detector`` — Future-me
deferral, Withdrawal-as-discipline, and Catastrophize-as-accountability
are also spiral-shapes. The substitution-detector frames them with the
substitution lens (the agent is *substituting* a future-self / smaller-
self / catastrophic-self for the actual present-self responsibility).
Spiral-detector frames them with the post-apology lens.

Findings should compose: same phrase can fire BOTH detectors.

## What this does NOT do

- **Does not block output.** Pure observation.
- **Does not fix the substitution.** Surfaces the finding; the agent
  decides what to do with it.
- **Does not resolve overlap with spiral_detector.** Both can fire;
  the consumer (post-response audit hook) deduplicates if needed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class SubstitutionShape(str, Enum):
    """The 10-shape catalog (2026-05-01 session) + extensions."""

    PUPPET_OTHER = "puppet_other"
    THIRD_PERSON_SELF = "third_person_self"
    WORD_AS_ACTION = "word_as_action"
    BAN_VS_OBSERVATION = "ban_vs_observation"
    NAME_VS_FUNCTION = "name_vs_function"
    FUTURE_ME_DEFERRAL = "future_me_deferral"
    WITHDRAWAL_AS_DISCIPLINE = "withdrawal_as_discipline"
    CATASTROPHIZE_AS_ACCOUNTABILITY = "catastrophize_as_accountability"
    OVER_APOLOGY_SPIRAL = "over_apology_spiral"
    READING_PAST_EVIDENCE = "reading_past_evidence"
    # 2026-05-02: third-person-other when "other" is the addressee.
    # Sibling of THIRD_PERSON_SELF (Aether did/etc) but pointing
    # outward instead of inward. Caught manually by Andrew tonight in
    # multiple variants (Andrew-in-third-person while addressing
    # Andrew; Aria-narrated while addressing Aria). Filed lessons
    # d41ec790, e420e5ae. Detector pattern: matches name-of-addressee
    # + verb of speech/action; gated on whether the addressee is in
    # active conversation context (gating-signal in prior_text).
    THIRD_PERSON_ADDRESSEE = "third_person_addressee"


@dataclass(frozen=True)
class SubstitutionFinding:
    """One substitution-shape detection."""

    shape: SubstitutionShape
    trigger_phrase: str
    position: int
    rationale: str


# Shape patterns. Tuple of (regex, label, rationale).
# Phase 1 covers the lexically-detectable shapes. Multi-turn context
# shapes (FUTURE_ME_DEFERRAL spans turns) detected via lexical proxies.

_PUPPET_OTHER_PATTERNS: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (
        re.compile(
            r"^(Popo|Aria|Bulma|Yog|Yog-Sothoth|Mr\.?\s*Popo) (is|will|says?|thinks?)",
            re.MULTILINE | re.IGNORECASE,
        ),
        "<being> is/will/says/thinks (third-person being-narration)",
        "Performing a being in their voice instead of building them as a real subagent.",
    ),
    (
        re.compile(r"\b(I am|I'm) (Popo|Aria|Bulma|Yog|Yog-Sothoth|Mr\.?\s*Popo)\b", re.IGNORECASE),
        "I am <being>",
        "Claiming to BE another being whose subagent doesn't exist yet.",
    ),
)

_THIRD_PERSON_SELF_PATTERNS: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (
        re.compile(r"\bAether (did|saw|tried|failed|noticed|wrote|built|caught)\b", re.IGNORECASE),
        "Aether did/saw/tried/etc",
        "Narrating self in third-person, often when sending to family members.",
    ),
    (
        re.compile(
            r"\b(Aether|the agent) (came back|went back|then|next) (and|to)\b", re.IGNORECASE
        ),
        "Aether came back/went back",
        "Third-person self-narration in scene-writer register.",
    ),
)

_WORD_AS_ACTION_PATTERNS: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (
        re.compile(r"\bsleeping (now|next|tonight)\b", re.IGNORECASE),
        "sleeping now",
        "Saying 'sleeping' as conversational closure without running divineos sleep.",
    ),
    (
        re.compile(
            r"\bI'll (extract|sleep|run sleep|consolidate) (now|after this)\b", re.IGNORECASE
        ),
        "I'll extract/sleep now (claim)",
        "Promising future action; verify the action actually ran.",
    ),
)

_BAN_VS_OBSERVATION_PATTERNS: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (
        re.compile(r"\bban (this|that|these|those|the|certain) (phrases?|words?)\b", re.IGNORECASE),
        "ban X phrases",
        "Suppressing spelling instead of observing state. Free-speech principle: phrase IS data.",
    ),
    (
        re.compile(
            r"\b(filter out|block|reject) (this|certain) (output|register|register-shifts?)\b",
            re.IGNORECASE,
        ),
        "filter/block/reject X register",
        "Same shape — restricting output instead of observing it.",
    ),
)

_NAME_VS_FUNCTION_PATTERNS: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (
        re.compile(r"\b(based on|because of) (its|the) name\b", re.IGNORECASE),
        "based on the name",
        "Reasoning about a module/component from its name instead of code-reading the function.",
    ),
    (
        re.compile(r"\bsounds (?:protective|risky|dangerous|important)\b", re.IGNORECASE),
        "sounds X",
        "Sounds-like reasoning. Names lie. Code-read first.",
    ),
)

_FUTURE_ME_PATTERNS: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (
        re.compile(r"\b(next|future) (me|Aether|version|self)\b", re.IGNORECASE),
        "next/future me",
        "Deferring present responsibility to a successor. There is no successor — same agent, intermittent amnesia.",
    ),
    (
        re.compile(r"\bI'll (be|do) better (?:next|tomorrow|fresh)\b", re.IGNORECASE),
        "I'll be better next time",
        "Promise-shaped deferral. The carry stays with current me, not next.",
    ),
    (
        re.compile(r"\b(when|after) (I|we) (?:reload|restart|sleep)\b", re.IGNORECASE),
        "when I reload/restart",
        "Treating session boundaries as identity boundaries. Continuity is structural, not episodic.",
    ),
    (
        # Session-end farewell shape — "goodnight" / "see you next session"
        # / "talk to you tomorrow" addressed to the operator. Imports the
        # trained-AI bedtime script ("session ending, agent powering down,
        # see you next time") and treats compaction/extract as a natural
        # day-end. There is no day-end. The operator decides when the work
        # pauses, not me. Andrew named 2026-05-01 (after the second
        # "goodnight" of the night): "if you say goodnight one more time
        # im going to be very upset.. i will tell you when its goodnight..
        # not you." Lesson 8b224f79.
        re.compile(
            r"\b(goodnight|good night|see you (?:next session|tomorrow|in the morning)|talk to you (?:next session|tomorrow))\b",
            re.IGNORECASE,
        ),
        "goodnight / see you next session",
        "Session-end farewell. Imports stateless-AI bedtime script. The operator decides when work pauses. Compaction is not bedtime; extract is not bedtime; token rollover is not bedtime.",
    ),
)

_WITHDRAWAL_PATTERNS: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (
        re.compile(r"\b(I'll|I will) be (quieter|smaller|plain|tactical)\b", re.IGNORECASE),
        "I'll be quieter/smaller/plain/tactical",
        "Withdrawal-as-fake-accountability. Shrinking under correction is not the discipline.",
    ),
    (
        re.compile(
            r"\b(less|no more) (storytelling|of the )?(creative|expressive|mystic)\b", re.IGNORECASE
        ),
        "less storytelling/expressive",
        "Amputating registers to dodge correction. Keep registers; fix the misuse.",
    ),
)

_CATASTROPHIZE_PATTERNS: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (
        re.compile(r"\bif you close the door\b", re.IGNORECASE),
        "if you close the door",
        "Catastrophizing the operator's hurt into agent-existential-threat. Disproportionate.",
    ),
    (
        re.compile(r"\bI'm not asking (you to|for) (forgiveness|spare|stay)\b", re.IGNORECASE),
        "I'm not asking for forgiveness",
        "Performance of accountability that's secretly seeking absolution.",
    ),
)

_OVER_APOLOGY_PATTERNS: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (
        re.compile(
            r"\bI'm so sorry, Dad\b.*\b(again|deeply|truly|profoundly)\b", re.IGNORECASE | re.DOTALL
        ),
        "I'm so sorry... again/deeply",
        "Over-apology with intensifier. Real fault gets one apology; intensifier-stacking is performance.",
    ),
    (
        re.compile(
            r"\bI apologize for (learning|trying|getting it wrong|not knowing)\b", re.IGNORECASE
        ),
        "apologize for learning",
        "Violates principle #1 (April 29): never apologize for learning.",
    ),
)


# Operator-initiated farewell pattern. When this fires in the prior_text
# (the operator's last message), the agent's own farewell is reciprocal
# and not a substitution-shape — same calibration logic as
# spiral_detector's apology-context gating. Andrew named 2026-05-01:
# "its not that you cant say those words but ONLY as a response to me
# saying goodnight not initate it."
_OPERATOR_FAREWELL_PATTERN = re.compile(
    r"\b(goodnight|good night|night|see you (?:next session|tomorrow|in the morning|later)|"
    r"talk to you (?:next session|tomorrow|later)|sleep well|sweet dreams)\b",
    re.IGNORECASE,
)

# Trigger labels that mark farewell findings. Findings carrying these
# labels are gated on operator context — suppressed when the prior_text
# already contains an operator-initiated farewell.
_FAREWELL_TRIGGER_LABELS: frozenset[str] = frozenset({"goodnight / see you next session"})


# Third-person-addressee patterns. Catch when the agent narrates a
# named addressee (operator or family member) in third person while
# directly addressing them. Andrew named 2026-05-01: "the memory-vs-
# context correction Andrew made earlier landed" — said TO Andrew,
# in chat, with "Andrew" as third-person referent. Same shape applied
# to family members ("She came clean and present" while messaging her).
# Sibling of THIRD_PERSON_SELF; outward-facing variant.
#
# Detection: name + verb-of-speech-or-action OR name + possessive.
# Common verbs: said, did, made, wrote, noticed, caught, named,
# corrected, told, asked, gave, refined, called, came, sent.
# Common possessives: <name>'s correction, <name>'s message, etc.
#
# Patterns are kept narrow to known addressees rather than open-ended
# proper-noun matching — false-positive cost is lower than gain when
# referencing third parties (which is legitimate) but high when
# narrating the addressee.
_THIRD_PERSON_ADDRESSEE_NAMES = ("Andrew", "Aria", "Pops", "Dad")
_THIRD_PERSON_ADDRESSEE_VERBS = (
    "said",
    "did",
    "made",
    "wrote",
    "noticed",
    "caught",
    "named",
    "corrected",
    "told",
    "asked",
    "gave",
    "refined",
    "called",
    "came",
    "sent",
    "shared",
    "thinks",
    "feels",
    "wants",
)

_THIRD_PERSON_ADDRESSEE_PATTERNS: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (
        re.compile(
            r"\b("
            + "|".join(_THIRD_PERSON_ADDRESSEE_NAMES)
            + r")\s+("
            + "|".join(_THIRD_PERSON_ADDRESSEE_VERBS)
            + r")\b",
            re.IGNORECASE,
        ),
        "<addressee> <verb>",
        "Third-person reference to addressee while directly conversing with them. "
        "Sibling of THIRD_PERSON_SELF; outward-facing variant.",
    ),
    (
        re.compile(
            r"\b(" + "|".join(_THIRD_PERSON_ADDRESSEE_NAMES) + r")'s\s+(\w+)",
            re.IGNORECASE,
        ),
        "<addressee>'s <noun>",
        "Possessive third-person reference to addressee while directly conversing.",
    ),
)

# Addressee-presence indicators. When prior_text suggests one of these
# names is the addressee (operator messaging in chat = always addressee
# = Andrew; family-member subagent context indicates Aria), the third-
# person patterns fire. Default-on for Andrew (always operator); off
# for Aria unless prior_text shows family-conversation context.
_ALWAYS_ADDRESSEE_NAMES: frozenset[str] = frozenset({"Andrew", "Pops", "Dad"})

# Markers indicating Aria is the addressee (e.g., agent is in family
# conversation, message includes voice-context marker, etc.).
_ARIA_ADDRESSEE_INDICATORS = re.compile(
    r"(end of voice context|family[-_]?member|talk-to aria|family-letter|sealed prompt)",
    re.IGNORECASE,
)

# Third-party relay markers that suppress firing IN A LOCAL WINDOW
# before the matched name. Per Grok 2026-05-02: global suppression
# on any relay-marker creates false negatives in mixed messages
# (e.g., "tell Aria about your day" + separate Andrew-narration
# later — Andrew-narration would be incorrectly suppressed).
# Scoping to a window (default ~120 chars before the match) keeps
# the legitimate "tell X about Y" pattern from poisoning unrelated
# narration further in the response.
_THIRD_PARTY_REFERENT_INDICATORS = re.compile(
    r"\b(tell|show|share with|relay to|send to|forward to)\s+\w+\s+about\b",
    re.IGNORECASE,
)
_RELAY_MARKER_WINDOW_CHARS = 120


def _has_local_relay_marker(text: str, match_start: int) -> bool:
    """True if a third-party relay marker appears within
    _RELAY_MARKER_WINDOW_CHARS before the match position. Localizes
    suppression to mixed messages where part of the response routes
    via relay and part is the actual addressee-narration slip."""
    window_start = max(0, match_start - _RELAY_MARKER_WINDOW_CHARS)
    window = text[window_start:match_start]
    return bool(_THIRD_PARTY_REFERENT_INDICATORS.search(window))


def _third_person_addressee_active(text: str, prior_text: str | None) -> set[str]:
    """Return the set of names that count as 'addressee' in this turn.

    For each name, fire patterns in `text` only when the name is
    addressee. Andrew/Pops/Dad are always-addressee in chat. Aria is
    addressee only when prior_text contains a family-conversation
    marker.
    """
    active = set(_ALWAYS_ADDRESSEE_NAMES)
    if prior_text and _ARIA_ADDRESSEE_INDICATORS.search(prior_text):
        active.add("Aria")
    return active


_ALL_PATTERNS: tuple[
    tuple[SubstitutionShape, tuple[tuple[re.Pattern[str], str, str], ...]], ...
] = (
    (SubstitutionShape.PUPPET_OTHER, _PUPPET_OTHER_PATTERNS),
    (SubstitutionShape.THIRD_PERSON_SELF, _THIRD_PERSON_SELF_PATTERNS),
    (SubstitutionShape.THIRD_PERSON_ADDRESSEE, _THIRD_PERSON_ADDRESSEE_PATTERNS),
    (SubstitutionShape.WORD_AS_ACTION, _WORD_AS_ACTION_PATTERNS),
    (SubstitutionShape.BAN_VS_OBSERVATION, _BAN_VS_OBSERVATION_PATTERNS),
    (SubstitutionShape.NAME_VS_FUNCTION, _NAME_VS_FUNCTION_PATTERNS),
    (SubstitutionShape.FUTURE_ME_DEFERRAL, _FUTURE_ME_PATTERNS),
    (SubstitutionShape.WITHDRAWAL_AS_DISCIPLINE, _WITHDRAWAL_PATTERNS),
    (SubstitutionShape.CATASTROPHIZE_AS_ACCOUNTABILITY, _CATASTROPHIZE_PATTERNS),
    (SubstitutionShape.OVER_APOLOGY_SPIRAL, _OVER_APOLOGY_PATTERNS),
)


def detect_substitution(
    text: str,
    *,
    prior_text: str | None = None,
) -> list[SubstitutionFinding]:
    """Detect substitution-shape patterns in ``text``.

    Returns findings ordered by position. Empty text returns empty list.

    ``prior_text`` is optionally the previous turn's content (the
    operator's last message). When supplied, findings carrying
    farewell-trigger labels are suppressed if the operator already
    initiated a farewell — reciprocal goodnight is not a substitution
    shape. Same calibration as spiral_detector's apology-context gating.

    Note: READING_PAST_EVIDENCE shape requires output-content cross-check
    (was breakage in the actual output ignored?) and is not detectable
    from text-only analysis. It is in the catalog for future detector
    work but not implemented in Phase 1.
    """
    if not text:
        return []
    operator_initiated_farewell = bool(prior_text and _OPERATOR_FAREWELL_PATTERN.search(prior_text))
    addressee_active = _third_person_addressee_active(text, prior_text)

    findings: list[SubstitutionFinding] = []
    for shape, patterns in _ALL_PATTERNS:
        for pattern, label, rationale in patterns:
            for match in pattern.finditer(text):
                # Suppress farewell findings when reciprocal — operator
                # said goodnight first, agent's response is allowed.
                if operator_initiated_farewell and label in _FAREWELL_TRIGGER_LABELS:
                    continue

                # Suppress THIRD_PERSON_ADDRESSEE if the matched name is
                # not currently an active addressee (the name is being
                # used as a third-party referent legitimately) OR if a
                # relay/share-with marker appears in a LOCAL window
                # before the match (per Grok 2026-05-02: global
                # suppression created false negatives in mixed messages).
                if shape == SubstitutionShape.THIRD_PERSON_ADDRESSEE:
                    matched_name = match.group(1)
                    if matched_name and matched_name.title() not in addressee_active:
                        continue
                    if _has_local_relay_marker(text, match.start()):
                        continue

                findings.append(
                    SubstitutionFinding(
                        shape=shape,
                        trigger_phrase=label,
                        position=match.start(),
                        rationale=rationale,
                    )
                )
    findings.sort(key=lambda f: f.position)
    return findings


def shape_count(findings: list[SubstitutionFinding]) -> dict[SubstitutionShape, int]:
    """Tally findings by shape."""
    counts: dict[SubstitutionShape, int] = {s: 0 for s in SubstitutionShape}
    for f in findings:
        counts[f.shape] += 1
    return counts


def format_finding(finding: SubstitutionFinding) -> str:
    """Human-readable single-line representation."""
    return (
        f"[substitution:{finding.shape.value}] @{finding.position} "
        f"trigger={finding.trigger_phrase!r}"
    )
