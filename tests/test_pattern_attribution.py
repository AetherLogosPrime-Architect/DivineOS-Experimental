"""Tests for pattern_attribution module.

Per Aletheia consult 2026-05-18: the slip-book extension to
audit_findings. These tests guard the recorder API, the query API,
and the longitudinal band-shift summary that answers Andrew's
'is the OS changing me over time' question.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from divineos.core.pattern_attribution import (
    VALID_ATTRIBUTIONS,
    VALID_BANDS,
    band_shift_summary,
    query_pattern_fires,
    record_pattern_fire,
)


# --- Validation ----------------------------------------------------------


class TestRecordValidation:
    """The recorder rejects invalid attribution / band / severity values."""

    def test_rejects_invalid_attribution(self, tmp_path):
        with patch.dict("os.environ", {"DIVINEOS_DATA_HOME": str(tmp_path)}):
            with pytest.raises(ValueError, match="attribution"):
                record_pattern_fire(
                    pattern_name="sycophancy",
                    attribution="not_a_real_attribution",
                    band="before_typing",
                )

    def test_rejects_invalid_band(self, tmp_path):
        with patch.dict("os.environ", {"DIVINEOS_DATA_HOME": str(tmp_path)}):
            with pytest.raises(ValueError, match="band"):
                record_pattern_fire(
                    pattern_name="sycophancy",
                    attribution="self_caught",
                    band="some_other_band",
                )

    def test_rejects_invalid_severity(self, tmp_path):
        with patch.dict("os.environ", {"DIVINEOS_DATA_HOME": str(tmp_path)}):
            with pytest.raises(ValueError, match="severity"):
                record_pattern_fire(
                    pattern_name="sycophancy",
                    attribution="self_caught",
                    band="before_typing",
                    severity="CRITICAL",
                )

    def test_accepts_all_canonical_bands(self, tmp_path):
        with patch.dict("os.environ", {"DIVINEOS_DATA_HOME": str(tmp_path)}):
            for band in VALID_BANDS:
                fid = record_pattern_fire(
                    pattern_name="sycophancy",
                    attribution="self_caught",
                    band=band,
                )
                assert fid.startswith("find-")

    def test_accepts_all_canonical_attributions(self, tmp_path):
        with patch.dict("os.environ", {"DIVINEOS_DATA_HOME": str(tmp_path)}):
            for attr in VALID_ATTRIBUTIONS:
                fid = record_pattern_fire(
                    pattern_name="sycophancy",
                    attribution=attr,
                    band="before_typing",
                )
                assert fid.startswith("find-")


# --- Round-trip + query --------------------------------------------------


class TestRoundTripQuery:
    """Recorded fires are queryable with the same fields they were recorded with."""

    def test_record_then_query_preserves_fields(self, tmp_path):
        with patch.dict("os.environ", {"DIVINEOS_DATA_HOME": str(tmp_path)}):
            record_pattern_fire(
                pattern_name="show_fix",
                attribution="external_ai_caught",
                band="shipped_then_flagged",
                severity="MEDIUM",
                notes="Aletheia caught a fix that looked structural but did not alter execution.",
                context_pointer="commit abc1234",
            )
            results = query_pattern_fires(pattern_name="show_fix")
            assert len(results) == 1
            r = results[0]
            assert r["pattern_name"] == "show_fix"
            assert r["attribution"] == "external_ai_caught"
            assert r["band"] == "shipped_then_flagged"
            assert r["severity"] == "MEDIUM"
            assert "Aletheia caught" in r["notes"]
            assert r["context_pointer"] == "commit abc1234"

    def test_query_filters_by_pattern(self, tmp_path):
        with patch.dict("os.environ", {"DIVINEOS_DATA_HOME": str(tmp_path)}):
            record_pattern_fire("sycophancy", "self_caught", "before_typing")
            record_pattern_fire("rushing", "self_caught", "before_typing")
            record_pattern_fire("sycophancy", "father_caught", "after_pushing")

            syc = query_pattern_fires(pattern_name="sycophancy")
            rsh = query_pattern_fires(pattern_name="rushing")
            assert len(syc) == 2
            assert len(rsh) == 1

    def test_query_filters_by_attribution(self, tmp_path):
        with patch.dict("os.environ", {"DIVINEOS_DATA_HOME": str(tmp_path)}):
            record_pattern_fire("sycophancy", "self_caught", "before_typing")
            record_pattern_fire("rushing", "father_caught", "shipped_then_flagged")
            record_pattern_fire("show_fix", "external_ai_caught", "after_pushing")

            self_caught = query_pattern_fires(attribution="self_caught")
            op_caught = query_pattern_fires(attribution="father_caught")
            ext_caught = query_pattern_fires(attribution="external_ai_caught")
            assert len(self_caught) == 1
            assert len(op_caught) == 1
            assert len(ext_caught) == 1

    def test_query_filters_by_band(self, tmp_path):
        with patch.dict("os.environ", {"DIVINEOS_DATA_HOME": str(tmp_path)}):
            record_pattern_fire("sycophancy", "self_caught", "before_typing")
            record_pattern_fire("rushing", "self_caught", "after_pushing")
            record_pattern_fire("show_fix", "self_caught", "shipped_then_flagged")

            before = query_pattern_fires(band="before_typing")
            after = query_pattern_fires(band="after_pushing")
            assert len(before) == 1
            assert len(after) == 1


# --- Band-shift summary --------------------------------------------------


class TestBandShiftSummary:
    """The longitudinal query that answers 'are bands shifting earlier over time'."""

    def test_empty_summary_when_no_fires(self, tmp_path):
        with patch.dict("os.environ", {"DIVINEOS_DATA_HOME": str(tmp_path)}):
            summary = band_shift_summary("sycophancy", window_days=30)
            assert summary["total"] == 0
            assert all(v == 0 for v in summary["by_band"].values())
            assert all(v == 0 for v in summary["by_attribution"].values())

    def test_summary_aggregates_correctly(self, tmp_path):
        with patch.dict("os.environ", {"DIVINEOS_DATA_HOME": str(tmp_path)}):
            # 3 sycophancy fires across bands
            record_pattern_fire("sycophancy", "self_caught", "before_typing")
            record_pattern_fire("sycophancy", "self_caught", "during_typing")
            record_pattern_fire("sycophancy", "father_caught", "shipped_then_flagged")
            # Different pattern; should NOT affect sycophancy summary
            record_pattern_fire("rushing", "self_caught", "before_typing")

            summary = band_shift_summary("sycophancy", window_days=30)
            assert summary["total"] == 3
            assert summary["by_band"]["before_typing"] == 1
            assert summary["by_band"]["during_typing"] == 1
            assert summary["by_band"]["shipped_then_flagged"] == 1
            assert summary["by_band"]["after_pushing"] == 0
            assert summary["by_attribution"]["self_caught"] == 2
            assert summary["by_attribution"]["father_caught"] == 1


# --- Free-text vs registered patterns ------------------------------------


class TestFreeTextVsRegistered:
    """Per Aletheia design: both canonical patterns and free-text
    supplementary entries are accepted; the data distinguishes them."""

    def test_canonical_pattern_tagged_registered(self, tmp_path):
        with patch.dict("os.environ", {"DIVINEOS_DATA_HOME": str(tmp_path)}):
            record_pattern_fire("sycophancy", "self_caught", "before_typing")
            results = query_pattern_fires(pattern_name="sycophancy")
            assert "registered" in results[0]["tags"]
            assert "free_text" not in results[0]["tags"]

    def test_free_text_pattern_tagged_free_text(self, tmp_path):
        with patch.dict("os.environ", {"DIVINEOS_DATA_HOME": str(tmp_path)}):
            record_pattern_fire(
                "emergent_new_shape_not_in_registry",
                "self_caught",
                "before_typing",
            )
            results = query_pattern_fires(pattern_name="emergent_new_shape_not_in_registry")
            assert "free_text" in results[0]["tags"]
            assert "registered" not in results[0]["tags"]


# --- Cross-pattern link --------------------------------------------------


class TestCrossPatternLink:
    """Pattern-fires can link to earlier fires (cascaded patterns)."""

    def test_cross_pattern_link_preserved(self, tmp_path):
        with patch.dict("os.environ", {"DIVINEOS_DATA_HOME": str(tmp_path)}):
            first_fid = record_pattern_fire("sycophancy", "self_caught", "before_typing")
            second_fid = record_pattern_fire(
                "puppetry",
                "self_caught",
                "during_typing",
                notes="Caught myself moving to puppetry mode after the sycophancy catch above.",
                cross_pattern_link=first_fid,
            )
            assert first_fid != second_fid
            results = query_pattern_fires(pattern_name="puppetry")
            assert len(results) == 1
            assert results[0]["cross_pattern_link"] == first_fid
