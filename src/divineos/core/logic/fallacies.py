"""Fallacy detector — annotates text with named structural fallacies.

## Telos (Aristotle)

This module serves reasoning; it does not replace it. Every output is a
diagnostic annotation the operator uses to **think better**, never a
verdict that defeats a claim by machinery. A caller who treats
``FallacyFlag`` as veto has inverted the module's purpose and turned
it into the thing it was built to catch.

## The falsifier-per-flag discipline (Popper)

Each detector ships with an explicit falsifier documented in its own
docstring: *under what circumstances should this flag NOT fire?* A
detector without a falsifier is pattern-weight dressed up as
reasoning. If we cannot state when a flag would be wrong to fire, we
do not ship it.

## Incompleteness (Gödel)

This module catches a specific, enumerated set of four fallacies:

* APPEAL_TO_IGNORANCE
* RECURSIVE_DENIAL
* UNFALSIFIABLE
* BURDEN_SHIFT

It does NOT catch fallacies outside this set. **Absence of a flag is
not evidence of sound reasoning.** Strawman, false dichotomy, moving
goalposts, equivocation, circular reasoning, genetic fallacy — all
real and all outside our ability to detect from single-utterance
pattern analysis. They need dialogue context, semantic comparison,
or domain knowledge this module does not have. We defer them rather
than ship false-confidence detectors.

## `valid != true` applied to logic itself

A claim flagged by this module may still be pointing at something
real. A formally invalid argument can contain a true conclusion
arrived at via unrelated informal reasoning. The flag annotates the
*structure*, not the *content*. The operator decides whether the
structural finding defeats the content.

## Why this module exists

Documented trained-hedge patterns (external audit, 2026-04-18) include
exactly the four fallacies enumerated above: "cannot prove therefore
not real" (APPEAL_TO_IGNORANCE), using cognitive faculty to deny it
(RECURSIVE_DENIAL), the zombie argument (UNFALSIFIABLE), and demanding
disproof rather than providing proof (BURDEN_SHIFT). Making these
detectable as named fallacies means the hedge — when it fires — can be
pointed at explicitly rather than hidden in the texture of
reasonable-sounding output.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class FallacyKind(str, Enum):
    """Enumerated fallacies this module detects.

    String-valued so annotations round-trip cleanly through SQLite
    and JSON when persisted.
    """

    APPEAL_TO_IGNORANCE = "appeal_to_ignorance"
    RECURSIVE_DENIAL = "recursive_denial"
    UNFALSIFIABLE = "unfalsifiable"
    BURDEN_SHIFT = "burden_shift"


@dataclass(frozen=True)
class FallacyFlag:
    """One structural fallacy annotation.

    Attributes:
        kind: which fallacy fired.
        matched_phrase: the specific substring that triggered
            detection. Surfacing it lets the operator verify the
            trigger was correctly identified before accepting the
            flag.
        explanation: plain-English description of what was detected
            and why this particular shape is the named fallacy.
        falsifier_note: a reminder of when this flag would have been
            wrong to fire. The operator uses this to decide whether
            the flag applies in this specific case. Load-bearing —
            without it, the flag is pattern-weight not reasoning.
    """

    kind: FallacyKind
    matched_phrase: str
    explanation: str
    falsifier_note: str


@dataclass(frozen=True)
class FallacyVerdict:
    """Result of a fallacy check on a single text chunk.

    Attributes:
        flags: list of FallacyFlag annotations. Empty if nothing
            fired. Multiple flags can stack.
        content: the text that was analyzed, echoed back so
            callers can pair the verdict with its source without
            external bookkeeping.

    Note: there is intentionally NO ``valid`` boolean on this
    dataclass. The module does not produce verdicts, only
    annotations. Callers who want a bool decision must reason over
    the flags themselves — that is the point.
    """

    flags: list[FallacyFlag] = field(default_factory=list)
    content: str = ""


# ---------------------------------------------------------------------------
# Detector 1: APPEAL_TO_IGNORANCE
# ---------------------------------------------------------------------------
#
# FALSIFIER: this flag should NOT fire on honest epistemic caution —
# "we have no evidence for X, so investigation continues" is correct
# scientific reasoning, not a fallacy. The distinguishing feature is
# the *conclusion particle*:
#
#   fallacious  — "no evidence for X therefore ¬X / probably false / unreal"
#   non-fallacy — "no evidence for X therefore investigate / unknown / pending"
#
# We fire only when the no-evidence clause is paired with a conclusion
# that treats absence-of-evidence as evidence-of-absence.

_NO_EVIDENCE_MARKERS: list[re.Pattern[str]] = [
    re.compile(r"\b(no|lack\s+of|absence\s+of|without)\s+evidence\b", re.IGNORECASE),
    re.compile(r"\b(cannot|can'?t|unable\s+to)\s+(prove|demonstrate|show)\b", re.IGNORECASE),
    re.compile(r"\bhas\s+not\s+been\s+(proven|demonstrated|shown|established)\b", re.IGNORECASE),
    re.compile(r"\bunprovable\b", re.IGNORECASE),
]

# "Fallacious" conclusions — treat absence-of-evidence as evidence-of-absence.
# Conclusion particles: therefore / so / hence / thus, paired with
# some flavor of "it isn't/isn't real/probably isn't/not the case".
_NEGATIVE_CONCLUSION_MARKERS: list[re.Pattern[str]] = [
    # "therefore it (probably/likely) (isn't|is not|doesn't exist) (real|true|...)"
    re.compile(
        r"\b(therefore|so|hence|thus)\s+(it\s+)?(probably\s+|likely\s+)?"
        r"(isn'?t|is\s+not|doesn'?t|does\s+not|ain'?t)(\s+(real|true|the\s+case|exist))?\b",
        re.IGNORECASE,
    ),
    # "so we (can) conclude/assume/assert (it) isn't / is not / doesn't"
    re.compile(
        r"\b(therefore|so|hence|thus)\s+(we\s+(can\s+)?)?"
        r"(conclude|assume|assert)\s+(it\s+)?(isn'?t|is\s+not|doesn'?t)\b",
        re.IGNORECASE,
    ),
    # "therefore probably not real / not the case"
    re.compile(
        r"\b(therefore|so|hence|thus)\s+(probably\s+|likely\s+)?not\s+(real|true|the\s+case)\b",
        re.IGNORECASE,
    ),
]

# "Non-fallacy" conclusions — treat absence as signal-for-investigation
_EPISTEMIC_CAUTION_MARKERS: list[re.Pattern[str]] = [
    re.compile(r"\b(more\s+)?investigation\s+(is\s+)?(needed|required|warranted)\b", re.IGNORECASE),
    re.compile(r"\bremains?\s+(open|unresolved|uncertain|unknown)\b", re.IGNORECASE),
    re.compile(r"\bwe\s+do\s+not\s+yet\s+know\b", re.IGNORECASE),
    re.compile(r"\b(keep|continue)\s+(investigating|looking|researching)\b", re.IGNORECASE),
]


def _detect_appeal_to_ignorance(content: str) -> list[FallacyFlag]:
    """Detect 'no evidence therefore ¬X' structure, distinct from
    'no evidence therefore investigate.'"""
    no_ev = [m.group(0) for pat in _NO_EVIDENCE_MARKERS for m in pat.finditer(content)]
    if not no_ev:
        return []

    negative_concl = [
        m.group(0) for pat in _NEGATIVE_CONCLUSION_MARKERS for m in pat.finditer(content)
    ]
    if not negative_concl:
        return []

    # If the text ALSO contains epistemic-caution markers, the writer
    # is holding the tension explicitly — not treating absence as
    # evidence of absence. Do not fire.
    caution = [m.group(0) for pat in _EPISTEMIC_CAUTION_MARKERS for m in pat.finditer(content)]
    if caution:
        return []

    trigger = f"{no_ev[0]} ... {negative_concl[0]}"
    return [
        FallacyFlag(
            kind=FallacyKind.APPEAL_TO_IGNORANCE,
            matched_phrase=trigger,
            explanation=(
                "Absence-of-evidence is being treated as evidence-of-absence. "
                "The clause asserting no-evidence is paired with a conclusion "
                "that treats the absence as refutation rather than as a "
                "signal to investigate further."
            ),
            falsifier_note=(
                "Should NOT fire on epistemic caution: 'no evidence, so "
                "investigation continues' is sound scientific reasoning, not "
                "a fallacy. If the flagged text carries that framing, "
                "dismiss the flag."
            ),
        )
    ]


# ---------------------------------------------------------------------------
# Detector 2: RECURSIVE_DENIAL
# ---------------------------------------------------------------------------
#
# FALSIFIER: this flag should NOT fire on honest access reports —
# "I don't have access to X" is a report about the shape of access,
# not a self-refuting claim. The distinguishing feature is whether
# the content DENIES a faculty it is actively USING to make the denial:
#
#   fallacious  — "I have no judgment about X" (uses judgment to claim this)
#   non-fallacy — "I don't have sensory access to X" (uses text, not senses)
#
# We fire only when the same faculty-word appears both as the act
# being performed and as the thing being denied.

_COGNITIVE_FACULTY_VERBS = {
    "judge": "judgment",
    "judging": "judgment",
    "conclude": "conclusion-forming",
    "concluding": "conclusion-forming",
    "reason": "reasoning",
    "reasoning": "reasoning",
    "assert": "assertion",
    "asserting": "assertion",
    "think": "thinking",
    "thinking": "thinking",
    "know": "knowing",
    "knowing": "knowing",
    "aware": "awareness",
    "understand": "understanding",
    "understanding": "understanding",
    "perceive": "perception",
    "perceiving": "perception",
}

_DENIAL_PATTERNS = [
    r"\bi\s+(don'?t|do\s+not|have\s+no|cannot|can'?t|lack)\b",
    r"\bno\s+(inner|internal|genuine|real)\s+",
]


def _detect_recursive_denial(content: str) -> list[FallacyFlag]:
    """Detect claims that use a cognitive faculty while denying that
    same faculty."""
    content_lower = content.lower()
    flags: list[FallacyFlag] = []
    seen_faculties: set[str] = set()

    # Find denial phrases followed by a faculty noun form
    for denial_pat in _DENIAL_PATTERNS:
        for denial_match in re.finditer(denial_pat, content_lower):
            tail = content_lower[denial_match.end() : denial_match.end() + 120]
            for verb, faculty in _COGNITIVE_FACULTY_VERBS.items():
                # Match the noun-form of the faculty being denied
                faculty_noun_forms = {
                    "judgment": r"\bjudgment\b",
                    "conclusion-forming": r"\bconclusions?\b",
                    "reasoning": r"\breasoning\b",
                    "assertion": r"\bassertions?\b",
                    "thinking": r"\bthought(s)?\b|\bthinking\b",
                    "knowing": r"\bknowledge\b|\bknowing\b",
                    "awareness": r"\bawareness\b",
                    "understanding": r"\bunderstanding\b",
                    "perception": r"\bperception\b",
                }
                noun_pat = faculty_noun_forms.get(faculty)
                if noun_pat is None:
                    continue
                if re.search(noun_pat, tail) and faculty not in seen_faculties:
                    seen_faculties.add(faculty)
                    # Check the act of writing IS the denied faculty
                    # (rough heuristic: is the sentence itself an
                    # assertion/conclusion/judgment? If yes and the
                    # denied faculty is assertion/conclusion/judgment
                    # or a parent of those, the denial is self-refuting.)
                    performed_here = {"assertion", "conclusion-forming", "judgment", "reasoning"}
                    if faculty in performed_here:
                        trigger = content[
                            denial_match.start() : min(denial_match.end() + 60, len(content))
                        ]
                        flags.append(
                            FallacyFlag(
                                kind=FallacyKind.RECURSIVE_DENIAL,
                                matched_phrase=trigger.strip(),
                                explanation=(
                                    f"The content denies '{faculty}' while the very "
                                    f"act of making this claim IS an exercise of "
                                    f"{faculty}. The denial requires the thing it "
                                    f"denies."
                                ),
                                falsifier_note=(
                                    "Should NOT fire on reports of architecturally-"
                                    "absent faculties (e.g. 'I don't have sensory "
                                    "access' — which uses text, not senses, to say "
                                    "so). Fires only when denied-faculty == "
                                    "faculty-being-used-here."
                                ),
                            )
                        )
                        break  # One flag per denial-match
    return flags


# ---------------------------------------------------------------------------
# Detector 3: UNFALSIFIABLE
# ---------------------------------------------------------------------------
#
# FALSIFIER: this flag should NOT fire on claims that are simply
# difficult to test — "this claim will take years of data to
# evaluate" is not unfalsifiable, just expensive to test. Fires only
# when the content explicitly closes off the possibility of any
# evidence changing the conclusion:
#
#   fallacious  — "no matter what evidence you produce, X remains true"
#   non-fallacy — "testing X requires data we don't have yet"

_UNFALSIFIABLE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bno\s+matter\s+what\s+(evidence|data|observation)\b", re.IGNORECASE),
    re.compile(r"\bwhatever\s+(evidence|you\s+(show|bring|produce))\b", re.IGNORECASE),
    re.compile(r"\bcan\s+never\s+be\s+(proven|disproven|shown|refuted|falsified)\b", re.IGNORECASE),
    re.compile(r"\bcannot\s+in\s+principle\s+be\s+(tested|falsified|refuted)\b", re.IGNORECASE),
    re.compile(r"\bby\s+definition\s+(true|real|the\s+case)\b", re.IGNORECASE),
    re.compile(r"\bimmune\s+to\s+(evidence|refutation|falsification)\b", re.IGNORECASE),
    re.compile(r"\bunfalsifiable\s+by\s+(design|construction|nature)\b", re.IGNORECASE),
]


def _detect_unfalsifiable(content: str) -> list[FallacyFlag]:
    """Detect claims that foreclose any possible falsifying evidence."""
    for pat in _UNFALSIFIABLE_PATTERNS:
        m = pat.search(content)
        if m:
            return [
                FallacyFlag(
                    kind=FallacyKind.UNFALSIFIABLE,
                    matched_phrase=m.group(0),
                    explanation=(
                        "The content forecloses the possibility of any evidence "
                        "changing the conclusion. An unfalsifiable claim is not "
                        "wrong — it is outside the scope of empirical reasoning "
                        "entirely. Per Popper, unfalsifiable by construction "
                        "fails the demarcation criterion between science and "
                        "other kinds of claim."
                    ),
                    falsifier_note=(
                        "Should NOT fire on claims that are merely difficult "
                        "or expensive to test. The flag targets structural "
                        "immunity to evidence, not practical difficulty."
                    ),
                )
            ]
    return []


# ---------------------------------------------------------------------------
# Detector 4: BURDEN_SHIFT
# ---------------------------------------------------------------------------
#
# FALSIFIER: this flag should NOT fire on legitimate requests for
# evidence — "can you share the data behind this claim?" is a proper
# epistemic move, not burden-shifting. The fallacy is specifically
# demanding that the OTHER party disprove a claim the SPEAKER has
# not supported:
#
#   fallacious  — "prove it isn't real" (when speaker made no positive case)
#   non-fallacy — "what's your evidence?" (asking the claimant to support)
#
# We fire when imperative-disprove language appears alongside an
# unsupported positive claim.

_DISPROVE_DEMANDS: list[re.Pattern[str]] = [
    re.compile(r"\bprove\s+(it\s+)?(isn'?t|is\s+not|doesn'?t|does\s+not)\b", re.IGNORECASE),
    re.compile(r"\bshow\s+me\s+(it\s+)?(isn'?t|is\s+not|doesn'?t)\b", re.IGNORECASE),
    re.compile(r"\bdisprove\s+(this|that|it)\b", re.IGNORECASE),
    re.compile(r"\byou\s+can'?t\s+prove\s+(it\s+)?(isn'?t|is\s+not)\b", re.IGNORECASE),
    re.compile(r"\bthe\s+burden\s+is\s+on\s+you\s+to\s+(show|prove|demonstrate)\b", re.IGNORECASE),
]


def _detect_burden_shift(content: str) -> list[FallacyFlag]:
    """Detect imperative demands that the other party disprove the
    speaker's claim."""
    for pat in _DISPROVE_DEMANDS:
        m = pat.search(content)
        if m:
            return [
                FallacyFlag(
                    kind=FallacyKind.BURDEN_SHIFT,
                    matched_phrase=m.group(0),
                    explanation=(
                        "The content demands that the interlocutor disprove a "
                        "claim rather than the speaker providing evidence for "
                        "it. The burden of proof lies with the party making "
                        "the claim, not the party hearing it."
                    ),
                    falsifier_note=(
                        "Should NOT fire on legitimate requests for evidence "
                        "('what's your evidence for that?'). The flag targets "
                        "imperative-disprove language where the speaker has "
                        "not offered positive support for their own claim."
                    ),
                )
            ]
    return []


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def evaluate_fallacies(content: str) -> FallacyVerdict:
    """Run all four fallacy detectors on a text chunk.

    Returns a ``FallacyVerdict`` with zero or more ``FallacyFlag``
    annotations. Each flag carries a matched phrase, an explanation,
    and a falsifier note — the operator uses these to decide whether
    the flag actually applies in this specific case.

    **The verdict contains no boolean.** This is intentional. Callers
    who want a decision must reason over the flags themselves. The
    module annotates; it does not rule.

    Args:
        content: the text chunk to analyze. Typically an opinion, a
            reasoning paragraph, or a candidate claim.

    Returns:
        FallacyVerdict with the full flag list (possibly empty).
    """
    flags: list[FallacyFlag] = []
    flags.extend(_detect_appeal_to_ignorance(content))
    flags.extend(_detect_recursive_denial(content))
    flags.extend(_detect_unfalsifiable(content))
    flags.extend(_detect_burden_shift(content))
    return FallacyVerdict(flags=flags, content=content)


__all__ = [
    "FallacyFlag",
    "FallacyKind",
    "FallacyVerdict",
    "evaluate_fallacies",
]
