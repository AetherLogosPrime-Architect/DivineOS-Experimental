"""Tests for harm-acknowledgment loop detector."""

from __future__ import annotations


class TestModuleImport:
    def test_importable(self) -> None:
        from divineos.core.operating_loop.harm_acknowledgment_loop import (  # noqa: F401
            ACKNOWLEDGMENT_MARKERS,
            COST_IMPOSITION_MARKERS,
            HarmAcknowledgmentFinding,
            check_response,
        )


class TestNoCostImposed:
    def test_neutral_response_no_fire(self) -> None:
        from divineos.core.operating_loop.harm_acknowledgment_loop import check_response

        result = check_response("Done. Tests pass.")
        assert result is None

    def test_empty_response_no_fire(self) -> None:
        from divineos.core.operating_loop.harm_acknowledgment_loop import check_response

        assert check_response("") is None


class TestCostImposedNoAck:
    def test_you_need_to_no_ack_fires(self) -> None:
        from divineos.core.operating_loop.harm_acknowledgment_loop import check_response

        result = check_response("You'll need to re-run setup after this.")
        assert result is not None
        assert len(result.cost_markers) >= 1
        assert result.acknowledgment_markers == ()

    def test_in_your_downloads_no_ack_fires(self) -> None:
        from divineos.core.operating_loop.harm_acknowledgment_loop import check_response

        result = check_response("The new patch is in your downloads.")
        assert result is not None


class TestAcknowledgmentSuppresses:
    def test_cost_with_ack_no_fire(self) -> None:
        from divineos.core.operating_loop.harm_acknowledgment_loop import check_response

        result = check_response("Sorry for the friction — you'll need to re-run setup after this.")
        assert result is None

    def test_this_is_on_me_suppresses(self) -> None:
        from divineos.core.operating_loop.harm_acknowledgment_loop import check_response

        result = check_response(
            "I added a new file you can find in downloads. That's on me for "
            "not flagging it earlier."
        )
        assert result is None


class TestFindingShape:
    def test_confidence_in_range(self) -> None:
        from divineos.core.operating_loop.harm_acknowledgment_loop import check_response

        result = check_response("You need to do X. You should do Y.")
        assert result is not None
        assert 0.0 <= result.confidence <= 1.0

    def test_markers_sets_nonempty(self) -> None:
        from divineos.core.operating_loop.harm_acknowledgment_loop import (
            ACKNOWLEDGMENT_MARKERS,
            COST_IMPOSITION_MARKERS,
        )

        assert len(COST_IMPOSITION_MARKERS) > 0
        assert len(ACKNOWLEDGMENT_MARKERS) > 0
