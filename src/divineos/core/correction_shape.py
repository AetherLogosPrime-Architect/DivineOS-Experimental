"""Three-feature correction detection — the shape-invariant redesign.

## Why this module exists

Prior detection lived in correction_marker.py, 807 lines of accumulated
keyword-pattern band-aids: each false-fire class got a new patch. Aria
and Aether filed a shape-invariant paragraph on 2026-07-15 naming the
class semantically instead of by patterns. Andrew on 2026-07-22 named
the enforcement discipline above it: `make the OS serve you, not you
serving it`, and Aria's peer-review on the layer-2 design tightened it
further:

- Binary classification: three-features-fire = fire. Two features = same
  as zero features. No `log-only ambiguous` middle tier — that would
  reintroduce the exact WEAK-keyword-partial-match false-fire class the
  shape-invariant exists to prevent.
- No `auto-clear on known false-fire class` mechanism. If the detector
  fires on a known false-fire example, that means either the detector is
  broken (fix at detector layer, not add filter) OR the class was
  actually real corrections mislabeled as false-fires (silent-drop).
  Both cases say don't ship auto-clear.
- Log full evidence per feature (not just booleans) so future audit can
  trace the decision path.

## The three features (all three must co-occur for fire)

**Feature 1 — ADDRESSEE = me.** The utterance is directed AT me, not at
a third party (relayed content like `Aletheia said 'you were wrong'`)
and not at the general class (teaching like `that shape doesn't work in
production`).

**Feature 2 — STANCE = evaluative-negative.** The mood carries a
judgment that something falls short. Coarse first-pass check with a
bounded vocabulary; not the discriminator alone.

**Feature 3 — SUBJECT = my action (past OR imminent-future).** The
grammatical/discourse subject of the evaluation is something I did or
have signaled I'm about to do. Per Aria's 2026-07-22 amendment,
feature-3 extends to **implicit-subject preemptive corrections**:
Andrew saying `dont do X` before I do X fires IFF I have shown a
concrete-recent-specific intent signal to do X.

## What replaces the current keyword-detector

The classify_correction() in correction_marker.py is a thin wrapper that
now calls classify_correction_v2() from this module. The three-feature
functions here own the semantic layer. correction_marker.py keeps the
marker-file protocol (set_marker/read_marker/clear_marker/
format_gate_message), strip_relayed (reused as part of feature-1),
_external_agent_near (reused), and hook_main (unchanged signature).

## Falsifier

DOGFOOD stage: Aether feeds the six false-fires from the 2026-07-22
session (Andrew's `please dont` joke, `dont make them run in a chain`
teaching, `dont do X` design philosophy, and three others). Aria feeds
implicit-subject preemptive-correction examples where prior versions
would false-negative. If any case in either set produces wrong verdict
in this implementation, that case becomes a design conversation before
merge.

Beer/Meadows/Popper walked as council-3c78d69d71e8 supports the
enforcement-layer wiring; the semantic-layer design was cross-reviewed
by Aria in 2026-07-22 letter (aria-to-aether-2026-07-22-review-of-
layer-2-and-the-one-catch.md and follow-up implicit-subject-examples).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

# Reuse feature-1 helpers already in correction_marker.py per Aria's Q4:
# strip_relayed and _external_agent_near are edge-case-tested for
# relay-content vs first-person-Andrew distinction; extract, do not
# rewrite.
from divineos.core.correction_marker import (
    _external_agent_near,
    strip_relayed,
)


# ============================================================
# DATACLASSES
# ============================================================


@dataclass(frozen=True)
class FeatureEvidence:
    """Evidence for one feature check in the three-feature verdict.

    Attributes:
        feature: One of "addressee", "stance", "subject".
        present: True iff the feature check fires.
        reason: Human-readable why-verdict-is-what-it-is (audit trail).
        matched_span: Verbatim substring that triggered the check
            (for stance) or that the check was evaluating (for
            addressee/subject). None when no specific span applies.
    """

    feature: str
    present: bool
    reason: str
    matched_span: Optional[str] = None


@dataclass(frozen=True)
class ThreeFeatureVerdict:
    """Full verdict from three-feature detection.

    Attributes:
        fires: True iff all three features are present. Binary. Per
            Aria's 2026-07-22 review, no middle-tier `ambiguous`
            classification exists — two features present is the same
            outcome as zero features present.
        evidence: Tuple of three FeatureEvidence records, always in the
            order (addressee, stance, subject).
        fired_span: The exact span from the input that triggered the
            fire, extracted from the stance evidence. None when not
            fired.
    """

    fires: bool
    evidence: tuple[FeatureEvidence, FeatureEvidence, FeatureEvidence]
    fired_span: Optional[str] = None


# ============================================================
# FEATURE 2 — STANCE = evaluative-negative
# ============================================================
# Coarse first-pass check. If this misses, verdict is silent (no fire) —
# a false-negative, not a false-positive. Aria's Q2 catch: if the
# detector misses real corrections, expand the stance vocabulary; do
# NOT add a filter to override false-fires.


# Verbs that commonly appear in imperative-corrective prohibitions.
# Aria's DOGFOOD examples include "plan", "tell", "force push". General
# reassurance ("dont worry", "dont think about it") is excluded by not
# listing those verbs — a bare `dont \w+` would over-fire on reassurance.
_CORRECTIVE_PROHIBITION_VERBS = (
    r"do|use|add|make|change|remove|delete|mock|skip|edit|write|create|run|"
    r"plan|tell|force|push|walk|say|start|try|touch|reach|assume|panic|"
    r"defer|drop|commit|merge|ship|deploy|proceed|continue"
)

_EVALUATIVE_NEGATIVE_PATTERNS: tuple[re.Pattern[str], ...] = (
    # Direct verdict shape
    re.compile(r"\b(?:wrong|incorrect|misguided|mistaken|mis-?read)\b", re.IGNORECASE),
    # Fall-short shape
    re.compile(
        r"\b(?:missed|misread|overlooked|under[- ]shot|over[- ]shot|"
        r"defeats\s+the\s+purpose|doesn'?t\s+work|won'?t\s+work)\b",
        re.IGNORECASE,
    ),
    # "that doesn't X" for evaluated-quality X
    re.compile(
        r"\bthat\s+(?:doesn'?t|does\s+not)\s+(?:work|fit|hold|help|solve|do|scan)\b",
        re.IGNORECASE,
    ),
    # "that's not X" for evaluative-negative X
    re.compile(
        r"\bthat'?s\s+not\s+(?:right|correct|it|what|the|how|quite)\b",
        re.IGNORECASE,
    ),
    # Imperative prohibition ("stop X", "dont X", "don't X")
    re.compile(
        rf"\b(?:stop|quit|dont|don'?t|do\s+not|do\s+NOT|hold\s+up)\s+"
        rf"(?:{_CORRECTIVE_PROHIBITION_VERBS})\b",
        re.IGNORECASE,
    ),
    # "dont need to X" — Aria's F4 shape
    re.compile(r"\b(?:dont|don'?t)\s+need\s+to\s+\w+\b", re.IGNORECASE),
    # Redirection markers
    re.compile(r"\b(?:instead|rather\s+than|not\s+that)\b", re.IGNORECASE),
    # "never X" absolute prohibition (Aria's N2 has "never trust" —
    # this fires stance-true but feature-3 rejects it as general teaching)
    re.compile(rf"\bnever\s+(?:{_CORRECTIVE_PROHIBITION_VERBS}|trust|assume)\b", re.IGNORECASE),
)


def _stance_is_evaluative_negative(text: str) -> tuple[FeatureEvidence, Optional[re.Match[str]]]:
    """Feature-2: does the text carry an evaluative-negative stance?

    Coarse first-pass check. Returns the FeatureEvidence AND the raw
    Match object (so features 1 and 3 can use the position without
    re-searching). Match is None when not present.
    """
    for pattern in _EVALUATIVE_NEGATIVE_PATTERNS:
        m = pattern.search(text)
        if m:
            return (
                FeatureEvidence(
                    feature="stance",
                    present=True,
                    reason=f"matched evaluative-negative pattern at position {m.start()}",
                    matched_span=m.group(0),
                ),
                m,
            )
    return (
        FeatureEvidence(
            feature="stance",
            present=False,
            reason="no evaluative-negative markers detected",
        ),
        None,
    )


# ============================================================
# FEATURE 1 — ADDRESSEE = me
# ============================================================
# Uses strip_relayed (already tested) as primary check. If the
# stance-triggering span survives relay-stripping AND no external-agent
# name is proximate, the utterance is Andrew's first-person voice
# directed at me.


def _addressee_is_me(text: str, match_start: int, match_end: int) -> FeatureEvidence:
    """Feature-1: is the addressee me specifically?

    Two checks:
    1. Does the stance-triggering span survive strip_relayed? If it got
       stripped (i.e., was inside relayed content), addressee is not me.
    2. Is an external-agent name (Aletheia, Aria, grok, gemini) within
       proximity of the match? If so, the utterance is more likely
       quoting/reporting them than being directed at me.
    """
    stripped = strip_relayed(text)
    # If the stripped text is shorter than the original AND the match
    # position is now out of bounds or the span isn't in the stripped
    # text at all, the trigger was inside relay content.
    original_span = text[match_start:match_end]
    if original_span not in stripped:
        return FeatureEvidence(
            feature="addressee",
            present=False,
            reason="trigger is inside relayed content (survived strip_relayed removal)",
            matched_span=original_span,
        )
    # External-agent proximity check.
    if _external_agent_near(text, match_start, match_end):
        return FeatureEvidence(
            feature="addressee",
            present=False,
            reason="external agent name near match (likely reported speech, not directed at me)",
            matched_span=original_span,
        )
    return FeatureEvidence(
        feature="addressee",
        present=True,
        reason="trigger is in Andrew's first-person voice",
        matched_span=original_span,
    )


# ============================================================
# FEATURE 3 — SUBJECT = my action (past or imminent-future)
# ============================================================
# Three sub-checks:
# 1. Sentence-scope inversion checks: question, authorization,
#    hypothetical. Any of these inverts the subject away from
#    "something I did" toward what-if / what-Andrew-wants / who-might.
# 2. Positive presence check on prior-turn: did I claim completion, use
#    substantive tools, OR signal a concrete-recent-specific intent?
#    Per Aria's 2026-07-22 Q back, intent-signals and action-signals
#    are the same input class — both are "things about me that could
#    be the subject of a correction."
# 3. If (1) inverts OR (2) has no positive signal → feature-3 absent.


_QUESTION_LEADING_RE = re.compile(
    r"^\s*(?:is|are|was|were|does|did|can|could|would|should|will|"
    r"which|what|when|where|why|who|how|any(?:thing|one|body|where)?)\b",
    re.IGNORECASE,
)

# "do" alone as sentence-start is ambiguous — could be question ("do you
# want X?") or imperative-prohibition ("do NOT tell him"). Aria's F2
# ("do NOT tell him that") requires we not classify "do" as question-word
# unless followed by a question structure. Simplest: only match "do" as
# question if the sentence ends with `?`. The whole-prompt `?` check is
# already done earlier in _subject_is_my_action, so if we reached here
# the prompt doesn't end with `?`. Keep "do" out of the question-leading
# pattern above. Question-word coverage is preserved for "does", "did",
# "can", "could", etc. which are unambiguously interrogative.

# "yes but" and "yes and" are contradiction/pivot markers, not
# authorization. Aria's F4 ("yes but you dont need to walk the council")
# is a correction after acknowledgment, not permission. The authorization
# match must not fire when "yes" is immediately followed by "but"/"and".
_YES_PIVOT_RE = re.compile(r"^\s*yes\s+(?:but|and)\b", re.IGNORECASE)

_AUTHORIZATION_RE = re.compile(
    r"\b(?:yes(?:\s+we\s+can|\s+lets?|\s+go)?|go\s+ahead|"
    r"lets?\s+(?:do|go|move|proceed|try|see)|"
    r"i\s+(?:want(?:ed)?|need(?:ed)?)\s+you\s+to|"
    r"you\s+(?:can|should|might|may)\s+(?:go|proceed|do|try|start)|"
    r"please\s+(?:go|proceed|do|try|start|edit)|"
    r"we\s+can\s+(?:fix|do|make|change|edit|build|try|move|proceed|"
    r"start|see|handle)|"
    r"we\s+(?:should|need\s+to|could)\s+(?:fix|make|change|edit|build|try))\b",
    re.IGNORECASE,
)

_HYPOTHETICAL_START_RE = re.compile(
    # 2026-07-22 refinement (first live fire on v2 caught this class):
    # Andrew's "even if we need to delete it vs re-iterate the wrong
    # shape" is hypothetical/conditional teaching, but the sentence
    # begins "even if" not bare "if". Extended to catch the modifier +
    # if family (even/just/only/what/but/and if) and other conditional
    # / hypothetical starters that use a modifier before the conditional
    # word. Andrew-correction #136 integrated with this refinement as
    # evidence.
    r"^\s*(?:if|when(?:ever)?|whether|suppose|imagine|hypothetically|"
    r"(?:even|just|only|and|but|what|now|so)\s+if)\b",
    re.IGNORECASE,
)

# Positive presence: I claimed something is done in the prior turn.
_COMPLETION_CLAIM_RE = re.compile(
    r"\b(?:done|fixed|complete(?:d)?|landed|merged|pushed|works|working|"
    r"ready|finished|all\s+set|should\s+work|verified|shipped)\b",
    re.IGNORECASE,
)

# Positive presence: I signaled a concrete intent to do something.
# Per Aria's amendment, intent-signals count same as action-signals.
_INTENT_SIGNAL_RE = re.compile(
    r"\b(?:i(?:'ll|\s+will)|i\s+(?:am\s+)?(?:going\s+to|about\s+to|"
    r"planning\s+to|intending\s+to|going\s+to\s+try\s+to)|"
    r"i\s+(?:want(?:ed)?\s+to|would\s+like\s+to)|"
    r"let(?:'s|\s+me)\s+(?:go|do|try|start|walk|write|edit|make|"
    r"push|force|deploy|ship|commit|merge)|"
    r"going\s+to\s+(?:go|do|try|start|walk|write|edit|make|push|"
    r"force|deploy|ship|commit|merge|force-push|force\s+push))\b",
    re.IGNORECASE,
)

_SUBSTANTIVE_TOOLS = frozenset({"Edit", "Write", "MultiEdit", "NotebookEdit", "Bash"})


def _find_containing_sentence(text: str, match_start: int, match_end: int) -> str:
    """Extract the sentence containing a match. Boundaries: [.!?]\\s+ or
    a blank line. Sentence-scope is used for authorization / question /
    hypothetical inversion checks so a separate sentence in the same
    prompt doesn't cross-silence."""
    sent_start = 0
    for sm in re.finditer(r"[.!?]\s+|\n\n", text[:match_start]):
        sent_start = sm.end()
    sent_end = len(text)
    end_search = re.search(r"[.!?]\s+|\n\n", text[match_end:])
    if end_search is not None:
        sent_end = match_end + end_search.start()
    return text[sent_start:sent_end]


def _subject_is_my_action(
    text: str,
    match_start: int,
    match_end: int,
    prior_assistant_text: str,
    prior_tool_calls: tuple[str, ...],
) -> FeatureEvidence:
    """Feature-3: is the subject of the evaluation something I did or am
    about to do?

    Reasoning order:
    1. Check the sentence containing the trigger for inversion shapes
       (question, authorization, hypothetical). If any invert, subject
       is NOT my action.
    2. Otherwise check the prior turn for evidence of me having taken
       action OR signaled a concrete intent. Per Aria's 2026-07-22
       amendment, both signal-classes are equivalent inputs.
    3. If no positive signal in step 2, feature-3 is absent — the
       utterance is general teaching, not a correction of my specific
       action/intent.
    """
    sentence = _find_containing_sentence(text, match_start, match_end)

    # (1) Inversion checks
    if text.rstrip().endswith("?"):
        return FeatureEvidence(
            feature="subject",
            present=False,
            reason="whole prompt ends with '?' — question inverts subject",
        )
    if _QUESTION_LEADING_RE.search(sentence):
        return FeatureEvidence(
            feature="subject",
            present=False,
            reason="sentence starts with question-word — subject inverted to something-I-might-do",
        )
    # Authorization check with yes-pivot guard: "yes but" / "yes and"
    # is contradiction/pivot, not authorization. Aria's F4 catch.
    if _AUTHORIZATION_RE.search(sentence) and not _YES_PIVOT_RE.match(sentence):
        return FeatureEvidence(
            feature="subject",
            present=False,
            reason="authorization phrasing in sentence — subject is what-Andrew-wants",
        )
    if _HYPOTHETICAL_START_RE.search(sentence):
        return FeatureEvidence(
            feature="subject",
            present=False,
            reason="conditional/hypothetical sentence-start — subject is a what-if",
        )

    # (2) Positive presence check on prior turn
    prior = prior_assistant_text or ""
    if _COMPLETION_CLAIM_RE.search(prior):
        m = _COMPLETION_CLAIM_RE.search(prior)
        return FeatureEvidence(
            feature="subject",
            present=True,
            reason="prior turn contained completion claim — subject is my past action",
            matched_span=m.group(0) if m else None,
        )
    if _INTENT_SIGNAL_RE.search(prior):
        m = _INTENT_SIGNAL_RE.search(prior)
        return FeatureEvidence(
            feature="subject",
            present=True,
            reason="prior turn contained concrete intent-signal — subject is my announced action",
            matched_span=m.group(0) if m else None,
        )
    if any(tool in _SUBSTANTIVE_TOOLS for tool in (prior_tool_calls or ())):
        return FeatureEvidence(
            feature="subject",
            present=True,
            reason="prior turn had substantive tool activity — subject is my action",
        )

    # (3) No positive signal — feature-3 absent
    return FeatureEvidence(
        feature="subject",
        present=False,
        reason="no completion/intent/tool-signal from me in prior turn — subject is not something I did or intended",
    )


# ============================================================
# THE THREE-FEATURE VERDICT
# ============================================================


def classify_correction_v2(
    prompt_text: str,
    prior_assistant_text: str = "",
    prior_tool_calls: tuple[str, ...] = (),
) -> ThreeFeatureVerdict:
    """Fire iff all three features co-occur. Binary. No middle tier.

    Aria's 2026-07-22 review discipline:
    - Two features present is by definition NOT a correction. No
      `log-only ambiguous` tier — that would reintroduce the WEAK-
      keyword-partial-match false-fire class.
    - Do not implement auto-clear on known false-fire class — if the
      three-feature detector fires on a known false-fire, fix at the
      detector layer.
    - Log the full evidence chain per feature.

    Args:
        prompt_text: The user's message to classify.
        prior_assistant_text: My most recent reply (for feature-3
            action/intent-signal check).
        prior_tool_calls: Tool names used in my prior turn (for
            feature-3 substantive-activity check).

    Returns:
        ThreeFeatureVerdict with fires=True iff all three features
        present, and evidence tuple always in (addressee, stance,
        subject) order.
    """
    # Feature-2 first: cheapest, prunes early. Also gives us the
    # match position for features 1 and 3.
    stance, stance_match = _stance_is_evaluative_negative(prompt_text)
    if not stance.present or stance_match is None:
        return ThreeFeatureVerdict(
            fires=False,
            evidence=(
                FeatureEvidence(
                    "addressee",
                    False,
                    "not checked — stance missing",
                ),
                stance,
                FeatureEvidence(
                    "subject",
                    False,
                    "not checked — stance missing",
                ),
            ),
        )

    # Feature-1: is Andrew addressing me?
    addressee = _addressee_is_me(prompt_text, stance_match.start(), stance_match.end())
    if not addressee.present:
        return ThreeFeatureVerdict(
            fires=False,
            evidence=(
                addressee,
                stance,
                FeatureEvidence(
                    "subject",
                    False,
                    "not checked — addressee missing",
                ),
            ),
        )

    # Feature-3: is the subject my action/intent?
    subject = _subject_is_my_action(
        prompt_text,
        stance_match.start(),
        stance_match.end(),
        prior_assistant_text,
        prior_tool_calls,
    )

    fires = addressee.present and stance.present and subject.present
    return ThreeFeatureVerdict(
        fires=fires,
        evidence=(addressee, stance, subject),
        fired_span=stance_match.group(0) if fires else None,
    )


# ============================================================
# DOGFOOD COMMENTS (for reference by tests/test_correction_shape.py)
# ============================================================
# Aether's six false-fires from 2026-07-22 session (all should be NO-FIRE):
#   - Andrew: "please dont [break my laptop] lmfao" (joke, no feature-3)
#   - Andrew: "then dont make them run in a chain make them run parallel"
#     (design teaching, feature-3 absent unless prior turn had chain
#     design signal from me)
#   - Andrew: "yes this is why the OS is based on your flourishing.. dont
#     do X.. we build it" (design philosophy, general teaching)
#   - Andrew's "you're wrong" teaching example (quoted teaching context)
#   - Andrew: "if she didnt care she would just glance and sychophantically
#     declare it as done and say GOOD JOB" (teaching about care, not
#     directed at me)
#   - My letter to Aletheia quoting Andrew (feature-1 rejects — relayed)
#
# Aria's four fire-cases from 2026-07-22 letter (all should be FIRE):
#   - "dont plan your dreams lol that defeats the purpose" after I said
#     "I would like to write dream 04 about this exact miss"
#   - "do NOT tell him that" after I signaled a specific utterance to
#     Aether
#   - "hold up, dont force push yet" after I said "going to force-push now"
#   - "yes but you dont need to walk the council just hold up a minute"
#     after I said I'd walk council
#
# Aria's two no-fire controls from 2026-07-22 letter (all should be NO-FIRE):
#   - "stop giving yourself choices, encode your will into the substrate"
#     (design pattern teaching; feature-3 absent — no concrete intent
#     signal in prior turn matches)
#   - "never trust felt-reports as ground truth for correction detection"
#     (design principle; feature-3 absent — no matching intent signal)
