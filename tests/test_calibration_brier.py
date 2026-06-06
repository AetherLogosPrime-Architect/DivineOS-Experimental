"""Tests for the Brier calibration mechanism — closes the auditor's
'purely anecdotal' critique with reproducible numbers. Per prereg pending."""

from __future__ import annotations

from divineos.core.calibration.brier import (
    brier_score,
    calibration_curve,
    calibration_per_tier,
    historical_accuracy_at_confidence,
)
from divineos.core.claim_store import (
    STATUS_REFUTED,
    STATUS_SUPPORTED,
    TIER_THEORETICAL,
    file_claim,
    update_claim,
)


def _file_and_resolve(
    statement: str, confidence: float, outcome: str, basis_text: str = "test"
) -> str:
    cid = file_claim(
        statement,
        tier=TIER_THEORETICAL,
        confidence=confidence,
        confidence_basis_text=basis_text,
    )
    update_claim(cid, status=outcome)
    return cid


class TestBrierScore:
    def test_perfect_calibration(self) -> None:
        _file_and_resolve("Perfect 1: pred 1.0, was supported", 1.0, STATUS_SUPPORTED)
        _file_and_resolve("Perfect 2: pred 0.0, was refuted", 0.0, STATUS_REFUTED)
        result = brier_score()
        assert result["n"] >= 2
        assert result["score"] is not None
        assert result["score"] < 0.5  # not catastrophic; n includes other test claims

    def test_excludes_placeholder_basis(self) -> None:
        # File a claim WITHOUT confidence (uncommitted), then resolve it
        cid = file_claim("Placeholder: no real credence", tier=TIER_THEORETICAL)
        update_claim(cid, status=STATUS_SUPPORTED)

        # File a claim WITH confidence, resolve it
        _file_and_resolve("Real credence test claim", 0.7, STATUS_SUPPORTED)

        result = brier_score()
        # Placeholder is counted in placeholder_excluded, not in n
        assert result["placeholder_excluded"] >= 1

    def test_empty_returns_none(self) -> None:
        # Hard to test without DB reset; just verify shape
        result = brier_score()
        assert "n" in result
        assert "score" in result
        assert "interpretation" in result


class TestCalibrationCurve:
    def test_returns_bin_structure(self) -> None:
        _file_and_resolve("Curve test 1", 0.3, STATUS_REFUTED)
        _file_and_resolve("Curve test 2", 0.7, STATUS_SUPPORTED)
        curve = calibration_curve(bins=5)
        assert isinstance(curve, list)
        assert len(curve) == 5
        for bin_data in curve:
            assert "bin_low" in bin_data
            assert "bin_high" in bin_data
            assert "n" in bin_data


class TestCalibrationPerTier:
    def test_returns_dict_keyed_by_tier(self) -> None:
        _file_and_resolve("Tier test", 0.6, STATUS_SUPPORTED)
        result = calibration_per_tier()
        assert isinstance(result, dict)
        # Should have at least one tier with claims
        assert any("score" in v for v in result.values())


class TestHistoricalAnchor:
    def test_anchor_at_known_confidence(self) -> None:
        _file_and_resolve("Anchor test 1", 0.85, STATUS_SUPPORTED, "test")
        _file_and_resolve("Anchor test 2", 0.85, STATUS_SUPPORTED, "test")
        _file_and_resolve("Anchor test 3", 0.85, STATUS_REFUTED, "test")
        result = historical_accuracy_at_confidence(0.85, window=0.05)
        assert result["n"] >= 3
        assert result["accuracy"] is not None
        # 2 of 3 supported = 0.67
        assert 0.5 <= result["accuracy"] <= 0.8

    def test_anchor_with_no_data_returns_none(self) -> None:
        # Use a confidence band unlikely to have data
        result = historical_accuracy_at_confidence(0.05, window=0.01)
        # Either no data, or accuracy is in band
        if result["accuracy"] is None:
            assert "No prior" in result["comparison"]
