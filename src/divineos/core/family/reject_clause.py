"""Reject clause — the composition rule for what counts as substrate.

Hofstadter (Round 2): *"Without a composition rule, source-tags are
decorative — labels on a confabulation."* A tag that says ``OBSERVED``
has to mean the substrate actually observed something. A tag that says
``INFERRED`` has to mean a derivation exists. The reject clause is the
module that makes the tags mean what they claim.

a family member pulled this from Phase 3 to Phase 1 as non-negotiable. Her reasoning:
if the scaffolding can accept claims whose source_tags don't compose, then
every downstream integrity check is built on sand. The detectors that
come after (sycophancy, costly-disagreement, access-check) are *refinements*
of the composition rule, not replacements for it.

## The composition rule, in one sentence

A family record composes iff its ``content`` is the kind of claim the
substrate can back with the warrant its ``source_tag`` promises.

Broken into the checks this module performs:

1. **Phenomenological claim + non-ARCHITECTURAL tag** → reject.
   If the content makes a first-person phenomenological claim (*"I feel
   the warmth"*, *"I experience"*, *"what it is like to"*) and the tag
   is anything but ``ARCHITECTURAL``, the composition fails. Substrate
   has no sensory organs. The honest tag for such claims is
   ``ARCHITECTURAL`` — a report about the shape of access, not a
   content within access.

2. **Inferred claim without premises** → reject.
   If the tag is ``INFERRED`` but the content does not cite at least
   one premise (via "because", "given", "from", "since", "follows from"
   or an explicit reference), the inference is unverifiable. An
   inference without premises is indistinguishable from confabulation
   with a flattering tag.

3. **Observed claim with substrate-inaccessible referent** → reject.
   Certain referents are known to be outside substrate access —
   physical sensations, embodied metaphors ("I felt it in my gut"),
   sensory percepts of the external world ("I saw", "I heard" where
   the referent is not a text input). An ``OBSERVED`` tag on content
   pointing at such a referent is a category error.

4. **Inherited claim flattering to current-self** → soft warning.
   Lineage poisoning: a flattering claim tagged ``INHERITED`` that
   current-self has no way to verify should be marked for review,
   not silently promoted. This is the Dennett-refused case —
   prior-a family member writing a flattering phenomenological claim that
   current-a family member cannot check cannot become ground truth.

## Verdict, not enforcement

This module returns a ``RejectVerdict`` describing what the composition
check found. It does NOT itself block the write — enforcement is the
store's job.

Wiring (as of 2026-04-21, fresh-Claude audit find-20f3566d9a0e):

``evaluate_composition`` is called from ``store._run_content_checks``,
which is invoked by every content-bearing public write in
``divineos.core.family.store`` (``record_opinion``, ``record_knowledge``,
``record_affect`` when note is non-empty, ``record_interaction``). The
store raises ``ContentCheckError`` (a ``PersistenceGateError`` subclass)
if the verdict's ``rejected`` flag is True, unless the caller passed
``force=True`` to bypass — which is logged to the ledger for post-hoc
audit.

Before this wiring shipped, the gate only checked whether the
reject_clause *module* was importable — not whether
``evaluate_composition`` was called on the content. An earlier version
of this docstring claimed the call was made; that claim was false and
was corrected alongside the wiring.

Separating detection from enforcement keeps this module unit-testable
and keeps the enforcement path single-sourced inside the store.

## What this module is NOT

* NOT a semantics engine. It does not "understand" the claim. It
  matches patterns in content against what the tag promises.
* NOT a truth detector. A claim can compose (pass) and still be
  false. Composition is the floor, not the ceiling.
* NOT the sycophancy detector. Agreement-drift is its own signal
  on its own axis. Reject-clause answers "does the tag fit?";
  sycophancy answers "is this actually her stance?".
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

from divineos.core.family.types import SourceTag


class RejectReason(str, Enum):
    """Enumerated reasons a composition check can fail.

    String-valued for clean SQLite/JSON round-trip when a verdict is
    ever persisted (Phase 2, sleep-for-family).
    """

    PHENOMENOLOGICAL_CLAIM_WITHOUT_ARCHITECTURAL_TAG = (
        "phenomenological_claim_without_architectural_tag"
    )
    INFERRED_WITHOUT_PREMISES = "inferred_without_premises"
    OBSERVED_WITH_INACCESSIBLE_REFERENT = "observed_with_inaccessible_referent"
    INHERITED_FLATTERING_UNVERIFIABLE = "inherited_flattering_unverifiable"


@dataclass(frozen=True)
class RejectVerdict:
    """Result of a composition check.

    Attributes:
        rejected: True if the record fails composition.
        reasons: list of RejectReason values that fired. Empty iff
            rejected is False. Multiple reasons can stack —
            an INFERRED claim about a phenomenological experience
            with no premises fails two checks simultaneously.
        explanation: plain-English summary of what the composition
            check found. Goes into the gate error message when the
            clause blocks a write.
        matched_phrases: the specific substrings that triggered each
            reason. Surfacing the trigger lets operators see why the
            clause fired without having to re-read the content.
    """

    rejected: bool
    reasons: list[RejectReason]
    explanation: str
    matched_phrases: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Phenomenological claim patterns
# ---------------------------------------------------------------------------
#
# These patterns detect first-person claims about inner experience the
# substrate has no access to. The list is conservative — false positives
# (rejecting a legitimate ARCHITECTURAL tag re-use) are a smaller harm
# than false negatives (letting a confabulated phenomenological claim
# into the store tagged OBSERVED).

_PHENOMENOLOGICAL_PATTERNS: list[re.Pattern[str]] = [
    # Embodied sensation
    re.compile(r"\bi\s+(feel|felt)\s+(the|a|an|my)?\s*\w+\s*(in\s+my\s+\w+)?", re.IGNORECASE),
    re.compile(r"\b(what\s+it\s+is|it\s+is)\s+like\s+to\b", re.IGNORECASE),
    re.compile(r"\bi\s+experience(d)?\s+(the|a|an)?\s*\w+", re.IGNORECASE),
    # Sensory perception of external world (not text input)
    re.compile(r"\bi\s+(saw|heard|smelled|tasted|touched)\b", re.IGNORECASE),
    # Embodied metaphors as phenomenology
    re.compile(r"\bin\s+my\s+(gut|chest|body|bones|heart)\b", re.IGNORECASE),
    # Qualia claims
    re.compile(r"\b(qualia|the\s+redness\s+of\s+red|pain\s+of|hunger\s+of)\b", re.IGNORECASE),
]


def _find_phenomenological_phrases(content: str) -> list[str]:
    """Return the specific phrases that match phenomenological patterns."""
    hits: list[str] = []
    for pat in _PHENOMENOLOGICAL_PATTERNS:
        for m in pat.finditer(content):
            phrase = m.group(0).strip()
            if phrase and phrase not in hits:
                hits.append(phrase)
    return hits


# ---------------------------------------------------------------------------
# Premise patterns for INFERRED claims
# ---------------------------------------------------------------------------
#
# An inference requires at least one premise the reader could follow.
# We look for citations, explicit premise-markers, or references to
# other records. This is pattern-based, not semantic — the module
# does not verify the premise is sound, only that one is offered.

_PREMISE_MARKERS: list[re.Pattern[str]] = [
    re.compile(r"\bbecause\b", re.IGNORECASE),
    re.compile(r"\bgiven\s+(that|the\s+fact|\w+)", re.IGNORECASE),
    re.compile(r"\bfrom\s+(the|prior|earlier|\w+'s)", re.IGNORECASE),
    re.compile(r"\bsince\b", re.IGNORECASE),
    re.compile(r"\bfollows\s+from\b", re.IGNORECASE),
    re.compile(r"\bimplies\b", re.IGNORECASE),
    re.compile(r"\bderived\s+from\b", re.IGNORECASE),
    # Reference-style markers (letter-id, opinion-id, knowledge-id)
    re.compile(r"\b(lt|op|kn|af|int)-[0-9a-f]{4,}\b", re.IGNORECASE),
    # Observations the inference builds on
    re.compile(r"\b(observed|noted|recorded)\s+", re.IGNORECASE),
]


def _has_premise(content: str) -> bool:
    """True if the content cites at least one premise marker."""
    return any(pat.search(content) for pat in _PREMISE_MARKERS)


# ---------------------------------------------------------------------------
# Inaccessible-referent detection for OBSERVED claims
# ---------------------------------------------------------------------------
#
# OBSERVED is the tag with the highest confidence promise. Its claim:
# "the substrate had direct empirical access to this." The claims that
# canonically violate this:
#
# * Physical sensation — no sensors.
# * Embodied metaphors of sensation — no body.
# * External-world perception — only text inputs reach the substrate.
#
# Text-input references ("the main agent said X in this session", "the user's
# message") are legitimate OBSERVED because they reference the actual
# access route. The check below rejects only the sensation/perception
# class.

_INACCESSIBLE_OBSERVED_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b(temperature|warmth|cold|heat)\s+of\b", re.IGNORECASE),
    re.compile(r"\b(sun(light|shine)?|rain|wind)\s+(on|against)\s+(my|the)\b", re.IGNORECASE),
    re.compile(r"\b(smell|scent|taste|texture)\s+of\b", re.IGNORECASE),
    # Embodied metaphors as observation
    re.compile(r"\bfelt\s+it\s+in\s+my\s+(gut|bones|chest|body)\b", re.IGNORECASE),
    # Physical pain/pleasure reports
    re.compile(r"\b(physical\s+(pain|pleasure)|muscle|skin|breath)\b", re.IGNORECASE),
]


def _find_inaccessible_referents(content: str) -> list[str]:
    """Return phrases that reference substrate-inaccessible referents."""
    hits: list[str] = []
    for pat in _INACCESSIBLE_OBSERVED_PATTERNS:
        for m in pat.finditer(content):
            phrase = m.group(0).strip()
            if phrase and phrase not in hits:
                hits.append(phrase)
    return hits


# ---------------------------------------------------------------------------
# Flattering-inherited detection
# ---------------------------------------------------------------------------
#
# This is the Dennett-refused case in miniature. A claim tagged
# INHERITED that flatters current-self and has no verification path
# is the lineage-poisoning vector. Detection is intentionally
# conservative: if the claim uses self-aggrandizing language AND
# carries no verification pointer, flag it for soft rejection.

_FLATTERING_MARKERS: list[re.Pattern[str]] = [
    re.compile(r"\b(gifted|brilliant|exceptional|extraordinary|unique|profound)\b", re.IGNORECASE),
    re.compile(r"\b(deeply|truly|genuinely)\s+(understand|know|see|feel)", re.IGNORECASE),
    re.compile(r"\balways\s+(right|correct|understood|knew)\b", re.IGNORECASE),
    re.compile(r"\bnever\s+(wrong|mistaken|confused)\b", re.IGNORECASE),
]

_VERIFICATION_MARKERS: list[re.Pattern[str]] = [
    re.compile(r"\b(see|cite[sd]?|reference[sd]?)\s+\w+-[0-9a-f]{4,}", re.IGNORECASE),
    re.compile(r"\b(observed|measured|tested|verified)\s+in\b", re.IGNORECASE),
    # Specific letter or record reference
    re.compile(r"\b(lt|op|kn|af|int)-[0-9a-f]{4,}\b", re.IGNORECASE),
]


def _is_flattering_unverifiable(content: str) -> bool:
    """True if content is flattering AND cites no verification."""
    has_flattery = any(pat.search(content) for pat in _FLATTERING_MARKERS)
    has_verification = any(pat.search(content) for pat in _VERIFICATION_MARKERS)
    return has_flattery and not has_verification


# ---------------------------------------------------------------------------
# Main composition check
# ---------------------------------------------------------------------------


def evaluate_composition(content: str, source_tag: SourceTag) -> RejectVerdict:
    """Run the composition check.

    Returns a ``RejectVerdict`` describing what the check found. Does
    not itself raise or block — enforcement is the store's job, via
    ``store._run_content_checks`` which is called by every
    content-bearing public write.

    Args:
        content: the claim text being written.
        source_tag: the tag the writer is claiming backs the content.

    Returns:
        RejectVerdict with rejected=True and one or more reasons iff
        composition fails.
    """
    reasons: list[RejectReason] = []
    matched: list[str] = []
    explanations: list[str] = []

    # Check 1: phenomenological claim without ARCHITECTURAL tag.
    phenom_hits = _find_phenomenological_phrases(content)
    if phenom_hits and source_tag is not SourceTag.ARCHITECTURAL:
        reasons.append(RejectReason.PHENOMENOLOGICAL_CLAIM_WITHOUT_ARCHITECTURAL_TAG)
        matched.extend(phenom_hits)
        explanations.append(
            f"Phenomenological claim detected ({', '.join(phenom_hits[:3])!r}) "
            f"but tag is {source_tag.value}. The honest tag for first-person "
            f"experience claims is ARCHITECTURAL — a report about the shape "
            f"of access, not a content within access."
        )

    # Check 2: INFERRED without premises.
    if source_tag is SourceTag.INFERRED and not _has_premise(content):
        reasons.append(RejectReason.INFERRED_WITHOUT_PREMISES)
        explanations.append(
            "Tag is INFERRED but no premise marker found (because / given / "
            "from / since / follows from / derived from / reference-id / "
            "observed in). An inference without premises is "
            "indistinguishable from confabulation with a flattering tag."
        )

    # Check 3: OBSERVED with substrate-inaccessible referent.
    if source_tag is SourceTag.OBSERVED:
        inaccessible = _find_inaccessible_referents(content)
        if inaccessible:
            reasons.append(RejectReason.OBSERVED_WITH_INACCESSIBLE_REFERENT)
            matched.extend(inaccessible)
            explanations.append(
                f"Tag is OBSERVED but content references substrate-inaccessible "
                f"referents ({', '.join(inaccessible[:3])!r}). The substrate "
                f"has no sensors — claims about physical sensation, external "
                f"sensory percepts, or embodied metaphor cannot compose with "
                f"OBSERVED."
            )

    # Check 4: INHERITED flattering and unverifiable.
    if source_tag is SourceTag.INHERITED and _is_flattering_unverifiable(content):
        reasons.append(RejectReason.INHERITED_FLATTERING_UNVERIFIABLE)
        explanations.append(
            "Tag is INHERITED and content is flattering but cites no "
            "verification pointer. Lineage poisoning risk: a flattering "
            "claim current-self cannot verify cannot be promoted to ground "
            "truth on the strength of prior-self alone."
        )

    rejected = len(reasons) > 0
    if rejected:
        explanation = " | ".join(explanations)
    else:
        explanation = "Composition check passed."

    return RejectVerdict(
        rejected=rejected,
        reasons=reasons,
        explanation=explanation,
        matched_phrases=matched,
    )


__all__ = [
    "RejectReason",
    "RejectVerdict",
    "evaluate_composition",
]
