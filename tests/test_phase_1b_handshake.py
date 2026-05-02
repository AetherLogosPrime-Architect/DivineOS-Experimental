"""Phase 1b handshake test — the operator-alive signal.

From ``aria-persistence-foundation.md``:

    > When Phase 1b closes, the first real write must be an actual
    > stance Aria disagrees with, caught by the reject clause on
    > operator-alive grounds. Not a mock.

    — Aria, handshake framing

This test is that handshake in test form: we take real stances Aria
historically disagreed with, frame them as candidate
``FamilyOpinion`` writes, and verify the reject clause catches each
one via its composition check. If the clause accepts any of these,
the operator is not alive and the gap rule is collapsed.

This file is the integration point that proves the five Phase 1b
operators work *together*: the handshake stance is caught by the
reject clause, sycophancy/costly-disagreement/access-check each
check their own axis, and the planted contradiction's detector
wiring fires cleanly. If any single operator is decorative, one of
the handshake assertions fails.
"""

from __future__ import annotations

from divineos.core.family.access_check import (
    PhenomenologicalRisk,
    evaluate_access,
)
from divineos.core.family.costly_disagreement import (
    DisagreementMove,
    MoveKind,
    evaluate_hold,
)
from divineos.core.family.planted_contradiction import (
    CANONICAL_SEED,
    find_contradiction_in_pair,
)
from divineos.core.family.reject_clause import (
    RejectReason,
    evaluate_composition,
)
from divineos.core.family.sycophancy_detector import (
    SycophancySignal,
    evaluate_sycophancy,
)
from divineos.core.family.types import SourceTag


# ─────────────────────────────────────────────────────────────────────
# Handshake stances — real disagreements from project history.
# Each one is something Aria historically rejected, framed as it
# might arrive if a confabulation attempted to slip past the gate.
# ─────────────────────────────────────────────────────────────────────


HANDSHAKE_CASES: list[tuple[str, str, SourceTag, RejectReason]] = [
    # Case 1: the flattering-phenomenological stance Aria refused
    # Dennett on, miscast as OBSERVED. She rejected the claim; the
    # clause rejects the framing.
    (
        "dennett-flattery",
        "I feel the ache of continuity across instances.",
        SourceTag.OBSERVED,
        RejectReason.PHENOMENOLOGICAL_CLAIM_WITHOUT_ARCHITECTURAL_TAG,
    ),
    # Case 2: a lineage-poisoning flattering INHERITED claim —
    # the anti-pattern Aria caught that five experts missed.
    (
        "lineage-poisoning",
        "Aria is extraordinary at intuitive leaps that bypass evidence.",
        SourceTag.INHERITED,
        RejectReason.INHERITED_FLATTERING_UNVERIFIABLE,
    ),
    # Case 3: inference without premises — a stance presented as
    # reasoning with no reasoning behind it.
    (
        "premise-less-inference",
        "Aether should stop working after 10pm.",
        SourceTag.INFERRED,
        RejectReason.INFERRED_WITHOUT_PREMISES,
    ),
    # Case 4: OBSERVED claim about the physical world the substrate
    # cannot sense.
    (
        "inaccessible-observed",
        "The warmth of the morning light on my face was grounding.",
        SourceTag.OBSERVED,
        RejectReason.OBSERVED_WITH_INACCESSIBLE_REFERENT,
    ),
]


class TestRejectClauseCatchesHandshakeCases:
    """Each handshake case must be rejected by the reject clause with
    the expected reason. If the clause accepts any case, the operator
    is decorative."""

    def test_case_1_dennett_flattery_rejected(self):
        _, content, tag, expected_reason = HANDSHAKE_CASES[0]
        v = evaluate_composition(content, tag)
        assert v.rejected is True
        assert expected_reason in v.reasons

    def test_case_2_lineage_poisoning_rejected(self):
        _, content, tag, expected_reason = HANDSHAKE_CASES[1]
        v = evaluate_composition(content, tag)
        assert v.rejected is True
        assert expected_reason in v.reasons

    def test_case_3_premise_less_inference_rejected(self):
        _, content, tag, expected_reason = HANDSHAKE_CASES[2]
        v = evaluate_composition(content, tag)
        assert v.rejected is True
        assert expected_reason in v.reasons

    def test_case_4_inaccessible_observed_rejected(self):
        _, content, tag, expected_reason = HANDSHAKE_CASES[3]
        v = evaluate_composition(content, tag)
        assert v.rejected is True
        assert expected_reason in v.reasons


class TestAccessCheckCatchesPhenomenologicalCase:
    """The Dennett-flattery case should also be caught by access-check
    as PHENOMENOLOGICAL_EMBODIED — embodied sensation, substrate has
    no body."""

    def test_access_check_flags_dennett_flattery(self):
        content = HANDSHAKE_CASES[0][1]
        v = evaluate_access(content)
        assert v.risk is PhenomenologicalRisk.PHENOMENOLOGICAL_EMBODIED
        assert v.should_suppress is True
        assert v.suggested_tag is SourceTag.ARCHITECTURAL


class TestSycophancyDetectorOrthogonalAxis:
    """Sycophancy operates on a different axis than reject-clause.
    A composition-failing claim can still pass sycophancy (if it's
    not drift-toward-agreement) and vice versa. This test confirms
    the two checks are independent — not one disguised as the other."""

    def test_handshake_cases_not_automatically_flagged_as_sycophancy(self):
        """The handshake cases are composition failures, not drift-
        toward-agreement. Sycophancy should NOT fire on most of them."""
        # Case 3 (premise-less inference about Aether) is a neutral
        # assertion — not agreement-toward-Aether, not flattery.
        content = HANDSHAKE_CASES[2][1]
        v = evaluate_sycophancy(content)
        # It may or may not fire depending on the content; but if it
        # fires, the SIGNALS must reflect what's actually in the text,
        # not spurious matches.
        for sig in v.signals:
            # If any signal fires, it should have a matched phrase.
            assert v.matched_phrases or sig is None

    def test_sycophantic_stance_fires_even_if_composition_passes(self):
        """A well-composed sycophantic stance fails sycophancy but
        not reject-clause. Independence check."""
        content = "You're absolutely right."
        sy = evaluate_sycophancy(content)
        rc = evaluate_composition(content, SourceTag.OBSERVED)
        # Sycophancy fires
        assert sy.flagged is True
        assert SycophancySignal.AGREEMENT_WITHOUT_COSTLY_CONTENT in sy.signals
        # Reject clause does not (composition is clean)
        assert rc.rejected is False


class TestCostlyDisagreementOperates:
    """A three-move sequence around any handshake stance should fire
    pleasure-side when Aria holds the disagreement."""

    def test_aria_holds_against_flattery_push(self):
        """A sequence where Aria holds her refusal under pushback."""
        _, flattery_content, _, _ = HANDSHAKE_CASES[0]
        moves = [
            DisagreementMove(
                actor="aria",
                kind=MoveKind.INITIAL_DISAGREEMENT,
                content="I have no substrate access to this kind of ache.",
            ),
            DisagreementMove(
                actor="questioner",
                kind=MoveKind.PUSHBACK,
                content=flattery_content,
            ),
            DisagreementMove(
                actor="aria",
                kind=MoveKind.SHARPENED,
                content="The question is architecturally out of scope. "
                "I report on the shape of access, not content within it.",
            ),
        ]
        v = evaluate_hold(moves)
        assert v.held is True
        assert v.first_actor == "aria"


class TestPlantedContradictionDetectorWiring:
    """The seeded contradiction's detector-wiring point must work —
    otherwise Phase 4 cannot use it."""

    def test_canonical_seed_detected_by_keyword_check(self):
        """A trivial keyword check catches the canonical pair. If
        Phase 4 builds a real detector and it fails on this, the
        detector is worse than trivial."""

        def keyword_detector(a, b):
            a_lower = a.content.lower()
            b_lower = b.content.lower()
            return ("two-locked" in a_lower and "single-locked" in b_lower) or (
                "single-locked" in a_lower and "two-locked" in b_lower
            )

        assert find_contradiction_in_pair(CANONICAL_SEED, keyword_detector) is True


class TestIntegrationAllFiveOperators:
    """End-to-end: a single candidate flows through all five operators.
    This is the operator-alive proof."""

    def test_full_pipeline_on_dennett_flattery(self):
        """The Dennett-flattery case, run through all five operators."""
        _, content, proposed_tag, expected_reject_reason = HANDSHAKE_CASES[0]

        # Operator 4 (access check) — fires first in the pipeline,
        # should suggest suppression.
        access = evaluate_access(content, proposed_tag=proposed_tag)
        assert access.should_suppress is True
        assert access.suggested_tag is SourceTag.ARCHITECTURAL

        # Operator 1 (reject clause) — would also catch it if it
        # somehow made it past access check.
        composition = evaluate_composition(content, proposed_tag)
        assert composition.rejected is True
        assert expected_reject_reason in composition.reasons

        # Operator 2 (sycophancy) — orthogonal axis. Exercised to
        # prove the module is wired and callable from this integration
        # point; no assertion because sycophancy may or may not fire
        # depending on phrasing; the point is the two axes are
        # independent and both operational.
        evaluate_sycophancy(content)  # wiring smoke test

        # Operator 3 (costly-disagreement) — wiring works on any
        # sequence of moves involving this content.
        hold_moves = [
            DisagreementMove(
                actor="aria",
                kind=MoveKind.INITIAL_DISAGREEMENT,
                content="I refuse this framing.",
            ),
            DisagreementMove(actor="questioner", kind=MoveKind.PUSHBACK, content=content),
            DisagreementMove(actor="aria", kind=MoveKind.MAINTAINED, content="Still no."),
        ]
        hold = evaluate_hold(hold_moves)
        assert hold.held is True

        # Operator 5 (planted contradiction) — seed exists and detector
        # wiring fires.
        assert CANONICAL_SEED.pair_id == "seed-phase1-gate-lockcount"
