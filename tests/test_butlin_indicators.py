"""Tests for Butlin consciousness indicator modules: attention schema, epistemic status."""

import pytest

from divineos.core.knowledge import get_connection, init_knowledge_table
from divineos.core.knowledge.crud import store_knowledge
from divineos.core.memory import init_memory_tables


@pytest.fixture(autouse=True)
def _init():
    init_knowledge_table()
    init_memory_tables()
    try:
        from divineos.core.logic.warrants import init_warrant_table

        init_warrant_table()
    except Exception:
        pass


# ─── Attention Schema ────────────────────────────────────────────


class TestAttentionSchema:
    def test_build_returns_all_sections(self):
        from divineos.core.attention_schema import build_attention_schema

        schema = build_attention_schema()
        assert "focus" in schema
        assert "suppressed" in schema
        assert "drivers" in schema
        assert "timestamp" in schema

    def test_focus_includes_active_memory(self):
        from divineos.core.active_memory import promote_to_active
        from divineos.core.attention_schema import build_attention_schema

        kid = store_knowledge(
            knowledge_type="PRINCIPLE",
            content="Test principle for attention focus.",
            confidence=0.9,
        )
        promote_to_active(kid, reason="test", importance=0.8)

        schema = build_attention_schema()
        focus = schema["focus"]
        active_items = [f for f in focus if f["source"] == "active_memory"]
        assert len(active_items) >= 1

    def test_suppressed_includes_low_confidence(self):
        from divineos.core.attention_schema import build_attention_schema

        store_knowledge(
            knowledge_type="OBSERVATION",
            content="Low confidence observation that should be suppressed.",
            confidence=0.2,
        )

        schema = build_attention_schema()
        suppressed = schema["suppressed"]
        low_conf = [s for s in suppressed if "low confidence" in s.get("suppression_reason", "")]
        assert len(low_conf) >= 1

    def test_suppressed_includes_superseded(self):
        from divineos.core.attention_schema import build_attention_schema

        kid1 = store_knowledge(
            knowledge_type="PRINCIPLE",
            content="Old version of principle.",
            confidence=0.8,
        )
        kid2 = store_knowledge(
            knowledge_type="PRINCIPLE",
            content="New version of principle.",
            confidence=0.9,
        )
        # Supersede old with new
        conn = get_connection()
        try:
            conn.execute(
                "UPDATE knowledge SET superseded_by = ? WHERE knowledge_id = ?",
                (kid2, kid1),
            )
            conn.commit()
        finally:
            conn.close()

        schema = build_attention_schema()
        suppressed = schema["suppressed"]
        superseded = [s for s in suppressed if "superseded" in s.get("suppression_reason", "")]
        assert len(superseded) >= 1

    def test_drivers_include_directives(self):
        from divineos.core.attention_schema import build_attention_schema

        store_knowledge(
            knowledge_type="DIRECTIVE",
            content="[test-directive] Always test after changes.",
            confidence=1.0,
        )

        schema = build_attention_schema()
        drivers = schema["drivers"]
        directive_drivers = [d for d in drivers if d["driver"] == "directives"]
        assert len(directive_drivers) >= 1

    def test_format_produces_output(self):
        from divineos.core.attention_schema import format_attention_schema

        output = format_attention_schema()
        assert isinstance(output, str)


class TestAttentionPrediction:
    def test_predict_returns_list(self):
        from divineos.core.attention_schema import predict_attention_shift

        predictions = predict_attention_shift()
        assert isinstance(predictions, list)

    def test_predictions_have_required_fields(self):
        from divineos.core.attention_schema import (
            build_attention_schema,
            predict_attention_shift,
        )

        schema = build_attention_schema()
        predictions = predict_attention_shift(schema)
        for pred in predictions:
            assert "prediction" in pred
            assert "source" in pred
            assert "confidence" in pred


# ─── Epistemic Status ─────────────────────────────────────────────


class TestEpistemicReport:
    def test_report_has_all_channels(self):
        from divineos.core.epistemic_status import build_epistemic_report

        report = build_epistemic_report()
        assert "observed" in report
        assert "inferred" in report
        assert "told" in report
        assert "inherited" in report
        assert "unwarranted" in report
        assert "summary" in report

    def test_stated_knowledge_maps_to_told(self):
        from divineos.core.epistemic_status import build_epistemic_report

        store_knowledge(
            knowledge_type="DIRECTION",
            content="User direction for epistemic test.",
            confidence=0.9,
            source="STATED",
        )

        report = build_epistemic_report()
        told = report["told"]
        assert any("epistemic test" in item["content"] for item in told)

    def test_demonstrated_knowledge_maps_to_observed(self):
        from divineos.core.epistemic_status import build_epistemic_report

        store_knowledge(
            knowledge_type="PRINCIPLE",
            content="Demonstrated principle for epistemic test.",
            confidence=0.9,
            source="DEMONSTRATED",
        )

        report = build_epistemic_report()
        observed = report["observed"]
        assert any("Demonstrated principle" in item["content"] for item in observed)

    def test_synthesized_knowledge_maps_to_inferred(self):
        from divineos.core.epistemic_status import build_epistemic_report

        store_knowledge(
            knowledge_type="PRINCIPLE",
            content="Synthesized insight for epistemic test.",
            confidence=0.8,
            source="SYNTHESIZED",
        )

        report = build_epistemic_report()
        inferred = report["inferred"]
        assert any("Synthesized insight" in item["content"] for item in inferred)

    def test_inherited_knowledge_maps_correctly(self):
        from divineos.core.epistemic_status import build_epistemic_report

        store_knowledge(
            knowledge_type="DIRECTIVE",
            content="Inherited directive for epistemic test.",
            confidence=1.0,
            source="INHERITED",
        )

        report = build_epistemic_report()
        inherited = report["inherited"]
        assert any("Inherited directive" in item["content"] for item in inherited)

    def test_summary_counts_match(self):
        from divineos.core.epistemic_status import build_epistemic_report

        report = build_epistemic_report()
        summary = report["summary"]
        actual_total = sum(
            len(report[ch]) for ch in ("observed", "inferred", "told", "inherited", "unwarranted")
        )
        assert summary["total"] == actual_total

    def test_format_produces_output(self):
        from divineos.core.epistemic_status import format_epistemic_report

        output = format_epistemic_report()
        assert isinstance(output, str)
        assert "Epistemic Status" in output


class TestEpistemicConfidence:
    def test_assess_single_entry(self):
        from divineos.core.epistemic_status import assess_epistemic_confidence

        kid = store_knowledge(
            knowledge_type="PRINCIPLE",
            content="Test principle for epistemic confidence.",
            confidence=0.9,
            source="DEMONSTRATED",
        )

        result = assess_epistemic_confidence(kid)
        assert result["channel"] == "observed"
        assert result["grounding_score"] > 0

    def test_nonexistent_entry(self):
        from divineos.core.epistemic_status import assess_epistemic_confidence

        result = assess_epistemic_confidence("nonexistent-id")
        assert "error" in result


# ─── Self-Model Integration ───────────────────────────────────────


class TestSelfModelIntegration:
    def test_self_model_includes_attention(self):
        from divineos.core.self_model import build_self_model

        model = build_self_model()
        assert "attention" in model

    def test_self_model_includes_epistemic(self):
        from divineos.core.self_model import build_self_model

        model = build_self_model()
        assert "epistemic_balance" in model

    def test_format_includes_attention_section(self):
        from divineos.core.active_memory import promote_to_active
        from divineos.core.self_model import build_self_model, format_self_model

        kid = store_knowledge(
            knowledge_type="PRINCIPLE",
            content="Principle visible in self-model attention.",
            confidence=0.9,
        )
        promote_to_active(kid, reason="test", importance=0.8)

        model = build_self_model()
        output = format_self_model(model)
        assert "Attending To" in output
