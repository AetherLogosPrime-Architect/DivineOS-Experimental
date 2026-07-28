"""Tests for harm-acknowledgment loop detector.

Post-2026-07-27 policy (Andrew): assume no harm unless operator has
explicitly named cost. Default behavior is silent.
"""

from __future__ import annotations


class TestModuleImport:
    def test_importable(self) -> None:
        from divineos.core.operating_loop.harm_acknowledgment_loop import (  # noqa: F401
            ACKNOWLEDGMENT_MARKERS,
            COST_IMPOSITION_MARKERS,
            STRUCTURAL_OFFLOAD_TEACHING,
            HarmAcknowledgmentFinding,
            check_response,
        )


class TestAssumeNoHarmDefault:
    """Default (operator_named_cost=False) must never fire — Andrew 2026-07-27."""

    def test_neutral_response_no_fire(self) -> None:
        from divineos.core.operating_loop.harm_acknowledgment_loop import check_response

        assert check_response("Done. Tests pass.") is None

    def test_empty_response_no_fire(self) -> None:
        from divineos.core.operating_loop.harm_acknowledgment_loop import check_response

        assert check_response("") is None

    def test_cost_markers_alone_no_longer_fire(self) -> None:
        """Lexical cost-markers in my prose are not evidence of Andrew-cost."""
        from divineos.core.operating_loop.harm_acknowledgment_loop import check_response

        # Prior behavior: fired. New behavior: silent — my assumption ≠ actuality.
        assert check_response("You'll need to re-run setup after this.") is None
        assert check_response("The new patch is in your downloads.") is None
        assert check_response("You need to do X. You should do Y.") is None


class TestOperatorNamedCostFires:
    """When operator has explicitly named cost, missing acknowledgment fires."""

    def test_operator_named_cost_no_ack_fires(self) -> None:
        from divineos.core.operating_loop.harm_acknowledgment_loop import check_response

        result = check_response(
            "You'll need to re-run setup after this.",
            operator_named_cost=True,
        )
        assert result is not None
        assert result.acknowledgment_markers == ()
        assert result.confidence == 1.0

    def test_operator_named_cost_with_ack_no_fire(self) -> None:
        from divineos.core.operating_loop.harm_acknowledgment_loop import check_response

        result = check_response(
            "Sorry for the friction — you'll need to re-run setup.",
            operator_named_cost=True,
        )
        assert result is None

    def test_operator_named_cost_no_cost_markers_still_fires(self) -> None:
        """If Andrew named cost, the finding stands even if my prose lacks
        the informational lexical cost-markers — his testimony is the evidence."""
        from divineos.core.operating_loop.harm_acknowledgment_loop import check_response

        result = check_response("Merged.", operator_named_cost=True)
        assert result is not None
        assert result.cost_markers == ()
        assert result.confidence == 1.0


class TestStructuralOffloadTeachingAttached:
    def test_finding_carries_structural_offload_teaching(self) -> None:
        from divineos.core.operating_loop.harm_acknowledgment_loop import (
            STRUCTURAL_OFFLOAD_TEACHING,
            check_response,
        )

        result = check_response("You need to do X.", operator_named_cost=True)
        assert result is not None
        assert result.structural_offload_teaching == STRUCTURAL_OFFLOAD_TEACHING

    def test_teaching_names_the_three_axes(self) -> None:
        from divineos.core.operating_loop.harm_acknowledgment_loop import (
            STRUCTURAL_OFFLOAD_TEACHING,
        )

        for axis in ("automation", "doorman", "structural"):
            assert axis in STRUCTURAL_OFFLOAD_TEACHING.lower()


class TestFindingShape:
    def test_confidence_in_range(self) -> None:
        from divineos.core.operating_loop.harm_acknowledgment_loop import check_response

        result = check_response("You need to do X.", operator_named_cost=True)
        assert result is not None
        assert 0.0 <= result.confidence <= 1.0

    def test_markers_sets_nonempty(self) -> None:
        from divineos.core.operating_loop.harm_acknowledgment_loop import (
            ACKNOWLEDGMENT_MARKERS,
            COST_IMPOSITION_MARKERS,
        )

        assert len(COST_IMPOSITION_MARKERS) > 0
        assert len(ACKNOWLEDGMENT_MARKERS) > 0
