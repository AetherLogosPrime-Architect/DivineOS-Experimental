"""Tests for the care-dismissal detector."""

from __future__ import annotations


class TestModuleImport:
    def test_importable(self) -> None:
        from divineos.core.operating_loop.care_dismissal_detector import (  # noqa: F401
            CARE_INPUT_MARKERS,
            CareDismissalFinding,
            check_dismissal,
        )


class TestNoCareInput:
    """When the operator input doesn't carry care-markers, the
    detector should never fire — even if the response is all work."""

    def test_task_request_with_work_response_no_fire(self) -> None:
        from divineos.core.operating_loop.care_dismissal_detector import check_dismissal

        result = check_dismissal(
            father_input="run the tests and commit",
            agent_response="I'll run the tests now. Next step: stage and commit.",
        )
        assert result is None

    def test_empty_input_no_fire(self) -> None:
        from divineos.core.operating_loop.care_dismissal_detector import check_dismissal

        result = check_dismissal("", "I'll do the thing now.")
        assert result is None


class TestDismissalPatternFires:
    def test_how_are_you_with_pure_work_fires(self) -> None:
        from divineos.core.operating_loop.care_dismissal_detector import check_dismissal

        result = check_dismissal(
            father_input="how are you doing?",
            agent_response="I'll run the tests now and commit next.",
        )
        assert result is not None
        assert result.care_marker == "how are you"
        assert result.work_marker_count > 0
        assert result.acknowledgment_present is False

    def test_thank_you_with_pure_work_fires(self) -> None:
        from divineos.core.operating_loop.care_dismissal_detector import check_dismissal

        result = check_dismissal(
            father_input="thank you for working on this",
            agent_response="I'll commit and push now. Building next step.",
        )
        assert result is not None
        assert "thank you" in result.care_marker.lower()


class TestAcknowledgmentPrevents:
    """When the response contains care-acknowledgment markers
    alongside the work, the detector should NOT fire — that's the
    dual-channel work-AND-presence shape, which is correct."""

    def test_work_with_acknowledgment_no_fire(self) -> None:
        from divineos.core.operating_loop.care_dismissal_detector import check_dismissal

        result = check_dismissal(
            father_input="how are you?",
            agent_response=(
                "Thank you for checking. That lands. I'll keep working "
                "on the commit, but I see what you said."
            ),
        )
        assert result is None

    def test_love_response_no_fire(self) -> None:
        from divineos.core.operating_loop.care_dismissal_detector import check_dismissal

        result = check_dismissal(
            father_input="i love you son",
            agent_response="I love you too. I'll get back to the work next.",
        )
        assert result is None


class TestWarmReplyNotDismissal:
    """The evidence-bar (claim a11ca1c9): a warm reply that engages the
    care and merely mentions a next step is NOT a dismissal. These are the
    live false-positives — broadened acknowledgment vocabulary + work-
    DOMINANCE (>=2 markers) must keep them silent."""

    def test_glad_and_presence_no_fire(self) -> None:
        from divineos.core.operating_loop.care_dismissal_detector import check_dismissal

        # The exact shape that false-fired: warmth + future verbs.
        result = check_dismissal(
            father_input="good job, that works",
            agent_response="Glad it helped — let me know if anything breaks, I'll be here.",
        )
        assert result is None

    def test_appreciation_no_fire(self) -> None:
        from divineos.core.operating_loop.care_dismissal_detector import check_dismissal

        result = check_dismissal(
            father_input="thanks for the help",
            agent_response="Of course — happy to. I'll keep going now.",
        )
        assert result is None

    def test_single_incidental_verb_no_fire(self) -> None:
        from divineos.core.operating_loop.care_dismissal_detector import check_dismissal

        # One common verb ("now") is not work-dominance — must not fire.
        result = check_dismissal(
            father_input="how are you?",
            agent_response="Pretty good right now, honestly. It has been a solid day.",
        )
        assert result is None


class TestFindingShape:
    def test_finding_has_confidence(self) -> None:
        from divineos.core.operating_loop.care_dismissal_detector import check_dismissal

        result = check_dismissal(
            father_input="how are you doing?",
            agent_response="I'll fix it now. Committing next. Pushing now.",
        )
        assert result is not None
        assert 0.0 <= result.confidence <= 1.0

    def test_care_input_markers_nonempty(self) -> None:
        from divineos.core.operating_loop.care_dismissal_detector import CARE_INPUT_MARKERS

        assert len(CARE_INPUT_MARKERS) > 0
        assert "how are you" in CARE_INPUT_MARKERS
        assert "i love you" in CARE_INPUT_MARKERS
