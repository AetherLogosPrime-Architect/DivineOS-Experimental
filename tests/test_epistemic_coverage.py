"""Extended tests for epistemic status — covering uncovered paths."""

import pytest

from divineos.core.knowledge import init_knowledge_table
from divineos.core.knowledge.crud import store_knowledge
from divineos.core.memory import init_memory_tables


@pytest.fixture(autouse=True)
def _init():
    init_knowledge_table()
    init_memory_tables()
    try:
        from divineos.core.logic.warrants import init_warrant_table

        init_warrant_table()
    except Exception:  # noqa: BLE001
        pass


class TestBuildFromSourceField:
    """Fallback epistemic report from source field when warrants unavailable."""

    def test_fallback_maps_stated_to_told(self):
        from divineos.core.epistemic_status import _build_from_source_field

        entries = [
            {
                "knowledge_id": "k1",
                "knowledge_type": "DIRECTION",
                "content": "User said do X.",
                "confidence": 0.9,
                "maturity": "TESTED",
                "source": "STATED",
            }
        ]
        report = _build_from_source_field(entries)
        assert len(report["told"]) == 1
        assert report["told"][0]["knowledge_id"] == "k1"

    def test_fallback_maps_demonstrated_to_observed(self):
        from divineos.core.epistemic_status import _build_from_source_field

        entries = [
            {
                "knowledge_id": "k2",
                "knowledge_type": "PRINCIPLE",
                "content": "Demonstrated fact.",
                "confidence": 0.8,
                "maturity": "CONFIRMED",
                "source": "DEMONSTRATED",
            }
        ]
        report = _build_from_source_field(entries)
        assert len(report["observed"]) == 1

    def test_fallback_maps_synthesized_to_inferred(self):
        from divineos.core.epistemic_status import _build_from_source_field

        entries = [
            {
                "knowledge_id": "k3",
                "knowledge_type": "OBSERVATION",
                "content": "Derived insight.",
                "confidence": 0.7,
                "maturity": "RAW",
                "source": "SYNTHESIZED",
            }
        ]
        report = _build_from_source_field(entries)
        assert len(report["inferred"]) == 1

    def test_fallback_maps_inherited(self):
        from divineos.core.epistemic_status import _build_from_source_field

        entries = [
            {
                "knowledge_id": "k4",
                "knowledge_type": "DIRECTIVE",
                "content": "Seed directive.",
                "confidence": 1.0,
                "maturity": "CONFIRMED",
                "source": "INHERITED",
            }
        ]
        report = _build_from_source_field(entries)
        assert len(report["inherited"]) == 1

    def test_fallback_unknown_source_is_unwarranted(self):
        from divineos.core.epistemic_status import _build_from_source_field

        entries = [
            {
                "knowledge_id": "k5",
                "knowledge_type": "OBSERVATION",
                "content": "No source.",
                "confidence": 0.5,
                "maturity": "RAW",
                "source": "",
            }
        ]
        report = _build_from_source_field(entries)
        assert len(report["unwarranted"]) == 1

    def test_fallback_skips_superseded(self):
        from divineos.core.epistemic_status import _build_from_source_field

        entries = [
            {
                "knowledge_id": "k6",
                "knowledge_type": "PRINCIPLE",
                "content": "Superseded.",
                "confidence": 0.8,
                "maturity": "REVISED",
                "source": "DEMONSTRATED",
                "superseded_by": "k7",
            }
        ]
        report = _build_from_source_field(entries)
        total = sum(
            len(report[ch]) for ch in ("observed", "inferred", "told", "inherited", "unwarranted")
        )
        assert total == 0

    def test_fallback_summary_correct(self):
        from divineos.core.epistemic_status import _build_from_source_field

        entries = [
            {
                "knowledge_id": "k1",
                "knowledge_type": "DIRECTION",
                "content": "Told.",
                "confidence": 0.9,
                "maturity": "TESTED",
                "source": "STATED",
            },
            {
                "knowledge_id": "k2",
                "knowledge_type": "PRINCIPLE",
                "content": "Observed.",
                "confidence": 0.8,
                "maturity": "CONFIRMED",
                "source": "DEMONSTRATED",
            },
        ]
        report = _build_from_source_field(entries)
        assert report["summary"]["told"] == 1
        assert report["summary"]["observed"] == 1
        assert report["summary"]["total"] == 2


class TestWarrantToChannel:
    def test_empirical(self):
        from divineos.core.epistemic_status import _warrant_to_channel

        assert _warrant_to_channel("EMPIRICAL") == "observed"

    def test_testimonial(self):
        from divineos.core.epistemic_status import _warrant_to_channel

        assert _warrant_to_channel("TESTIMONIAL") == "told"

    def test_inferential(self):
        from divineos.core.epistemic_status import _warrant_to_channel

        assert _warrant_to_channel("INFERENTIAL") == "inferred"

    def test_inherited(self):
        from divineos.core.epistemic_status import _warrant_to_channel

        assert _warrant_to_channel("INHERITED") == "inherited"

    def test_unknown(self):
        from divineos.core.epistemic_status import _warrant_to_channel

        assert _warrant_to_channel("UNKNOWN") == "unwarranted"


class TestSourceToChannel:
    def test_corrected(self):
        from divineos.core.epistemic_status import _source_to_channel

        assert _source_to_channel("CORRECTED") == "told"

    def test_stated(self):
        from divineos.core.epistemic_status import _source_to_channel

        assert _source_to_channel("STATED") == "told"

    def test_demonstrated(self):
        from divineos.core.epistemic_status import _source_to_channel

        assert _source_to_channel("DEMONSTRATED") == "observed"

    def test_empty(self):
        from divineos.core.epistemic_status import _source_to_channel

        assert _source_to_channel("") == "unwarranted"


class TestAssessEpistemicConfidence:
    """Individual entry confidence assessment."""

    def test_with_warrant(self):
        from divineos.core.epistemic_status import assess_epistemic_confidence
        from divineos.core.logic.warrants import create_warrant

        kid = store_knowledge(
            knowledge_type="PRINCIPLE",
            content="Well-grounded principle.",
            confidence=0.9,
            source="DEMONSTRATED",
        )
        create_warrant(kid, "EMPIRICAL", "Observed in test output")

        result = assess_epistemic_confidence(kid)
        assert result["channel"] == "observed"
        assert result["grounding_score"] == 1.0
        assert result["warrant_count"] >= 1
        assert result["combined_confidence"] > 0

    def test_without_warrant(self):
        from divineos.core.epistemic_status import assess_epistemic_confidence

        kid = store_knowledge(
            knowledge_type="OBSERVATION",
            content="Unwarranted observation.",
            confidence=0.5,
            source="",
        )
        result = assess_epistemic_confidence(kid)
        assert result["grounding_score"] <= 0.3  # low grounding without warrant

    def test_nonexistent_returns_error(self):
        from divineos.core.epistemic_status import assess_epistemic_confidence

        result = assess_epistemic_confidence("does-not-exist")
        assert "error" in result


class TestFormatEpistemicReport:
    """Format rendering of epistemic report."""

    def test_format_with_all_channels(self):
        from divineos.core.epistemic_status import format_epistemic_report

        report = {
            "observed": [
                {"maturity": "CONFIRMED", "type": "PRINCIPLE", "content": "Observed fact"}
            ],
            "told": [{"maturity": "TESTED", "type": "DIRECTION", "content": "User told me"}],
            "inferred": [
                {
                    "maturity": "RAW",
                    "type": "OBSERVATION",
                    "content": "I derived this",
                    "warrant_grounds": "logical deduction",
                }
            ],
            "inherited": [{"maturity": "CONFIRMED", "type": "DIRECTIVE", "content": "Seed data"}],
            "unwarranted": [
                {"maturity": "RAW", "type": "OBSERVATION", "content": "No justification"}
            ],
            "summary": {
                "observed": 1,
                "told": 1,
                "inferred": 1,
                "inherited": 1,
                "unwarranted": 1,
                "total": 5,
            },
        }
        output = format_epistemic_report(report)
        assert "Observed (I saw this happen)" in output
        assert "Told (you told me this)" in output
        assert "Inferred (I derived this)" in output
        assert "Inherited (I was born knowing" in output
        assert "Unwarranted" in output
        assert "logical deduction" in output

    def test_format_empty_report(self):
        from divineos.core.epistemic_status import format_epistemic_report

        report = {
            "observed": [],
            "told": [],
            "inferred": [],
            "inherited": [],
            "unwarranted": [],
            "summary": {
                "observed": 0,
                "told": 0,
                "inferred": 0,
                "inherited": 0,
                "unwarranted": 0,
                "total": 0,
            },
        }
        output = format_epistemic_report(report)
        assert "Epistemic Status" in output
        assert "Total: 0" in output
