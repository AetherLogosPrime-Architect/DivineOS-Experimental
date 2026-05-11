"""Tests for expectation_tracking module."""

from __future__ import annotations


class TestModuleImport:
    def test_importable(self) -> None:
        from divineos.core.expectation_tracking import (  # noqa: F401
            Expectation,
            calibration_summary,
            open_expectations,
            record_actual,
            record_expectation,
        )


class TestExpectationShape:
    def test_dataclass_shape(self) -> None:
        from divineos.core.expectation_tracking import Expectation

        e = Expectation(
            expectation_id="exp-abc",
            claim="test",
            basis="evidence",
            opened_at=1234.5,
        )
        assert e.expectation_id == "exp-abc"
        assert e.accurate is None
        assert e.closed_at == 0.0


class TestPublicSurfaceContract:
    def test_empty_claim_rejected(self) -> None:
        from divineos.core.expectation_tracking import record_expectation

        assert record_expectation("", "basis") == ""
        assert record_expectation("   ", "basis") == ""

    def test_empty_id_rejected_on_actual(self) -> None:
        from divineos.core.expectation_tracking import record_actual

        assert record_actual("", "outcome", True) == ""

    def test_open_expectations_returns_list(self) -> None:
        from divineos.core.expectation_tracking import open_expectations

        result = open_expectations()
        assert isinstance(result, list)

    def test_calibration_summary_returns_dict(self) -> None:
        from divineos.core.expectation_tracking import calibration_summary

        result = calibration_summary(limit=10)
        assert isinstance(result, dict)
        assert "closed_count" in result
        assert "accurate_count" in result
        assert "inaccurate_count" in result
        assert "accuracy_rate" in result
        assert 0.0 <= result["accuracy_rate"] <= 1.0
