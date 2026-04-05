"""Extended tests for attention schema — covering uncovered paths."""

import json
from pathlib import Path

import pytest

from divineos.core.knowledge import get_connection, init_knowledge_table
from divineos.core.knowledge.crud import store_knowledge
from divineos.core.memory import init_memory_tables


@pytest.fixture(autouse=True)
def _init():
    init_knowledge_table()
    init_memory_tables()


class TestBuildAttentionCompleteness:
    """Completeness tracking in build_attention_schema."""

    def test_completeness_all_succeed(self):
        from divineos.core.attention_schema import build_attention_schema

        schema = build_attention_schema()
        comp = schema["completeness"]
        assert comp["total"] == 3
        assert comp["succeeded"] >= 1
        assert isinstance(comp["failed"], list)
        assert comp["complete"] == (len(comp["failed"]) == 0)

    def test_completeness_fields_present(self):
        from divineos.core.attention_schema import build_attention_schema

        schema = build_attention_schema()
        comp = schema["completeness"]
        assert "total" in comp
        assert "succeeded" in comp
        assert "failed" in comp
        assert "complete" in comp


class TestGetCurrentFocus:
    """Focus items from active memory, goals, and recent events."""

    def test_focus_includes_goals_from_file(self):
        from divineos.core.attention_schema import _get_current_focus

        goal_dir = Path("data/hud")
        goal_dir.mkdir(parents=True, exist_ok=True)
        goals_path = goal_dir / "active_goals.json"
        goals_path.write_text(
            json.dumps([{"text": "Build testing tools", "status": "active"}]),
            encoding="utf-8",
        )
        try:
            focus = _get_current_focus()
            goal_items = [f for f in focus if f["source"] == "goal"]
            assert len(goal_items) >= 1
            assert goal_items[0]["type"] == "GOAL"
            assert goal_items[0]["importance"] == 0.9
        finally:
            goals_path.unlink(missing_ok=True)

    def test_focus_skips_completed_goals(self):
        from divineos.core.attention_schema import _get_current_focus

        goal_dir = Path("data/hud")
        goal_dir.mkdir(parents=True, exist_ok=True)
        goals_path = goal_dir / "active_goals.json"
        goals_path.write_text(
            json.dumps([{"text": "Done task", "status": "completed"}]),
            encoding="utf-8",
        )
        try:
            focus = _get_current_focus()
            goal_items = [f for f in focus if f["source"] == "goal"]
            assert len(goal_items) == 0
        finally:
            goals_path.unlink(missing_ok=True)

    def test_focus_handles_missing_goals_file(self):
        from divineos.core.attention_schema import _get_current_focus

        focus = _get_current_focus()
        assert isinstance(focus, list)

    def test_focus_handles_event_table_mismatch(self):
        """The events table query may fail (table is system_events), but focus still works."""
        from divineos.core.attention_schema import _get_current_focus

        # _get_current_focus queries 'events' but ledger uses 'system_events'
        # This should not crash — it silently skips recent events
        focus = _get_current_focus()
        assert isinstance(focus, list)


class TestGetSuppressed:
    """Suppressed items — low confidence, superseded, archived."""

    def test_suppressed_low_confidence(self):
        from divineos.core.attention_schema import _get_suppressed

        store_knowledge(
            knowledge_type="OBSERVATION",
            content="Very uncertain observation for suppression test.",
            confidence=0.15,
        )
        suppressed = _get_suppressed()
        low_conf = [s for s in suppressed if "low confidence" in s["suppression_reason"]]
        assert len(low_conf) >= 1

    def test_suppressed_superseded(self):
        from divineos.core.attention_schema import _get_suppressed

        kid1 = store_knowledge(knowledge_type="PRINCIPLE", content="Old principle.", confidence=0.8)
        kid2 = store_knowledge(knowledge_type="PRINCIPLE", content="New principle.", confidence=0.9)
        conn = get_connection()
        try:
            conn.execute(
                "UPDATE knowledge SET superseded_by = ? WHERE knowledge_id = ?",
                (kid2, kid1),
            )
            conn.commit()
        finally:
            conn.close()

        suppressed = _get_suppressed()
        superseded = [s for s in suppressed if "superseded" in s["suppression_reason"]]
        assert len(superseded) >= 1

    def test_suppressed_returns_list(self):
        from divineos.core.attention_schema import _get_suppressed

        result = _get_suppressed()
        assert isinstance(result, list)


class TestGetAttentionDrivers:
    """Drivers that explain WHY attention is focused where it is."""

    def test_directive_driver(self):
        from divineos.core.attention_schema import _get_attention_drivers

        store_knowledge(
            knowledge_type="DIRECTIVE",
            content="[test] Always run tests.",
            confidence=1.0,
        )
        drivers = _get_attention_drivers()
        dir_drivers = [d for d in drivers if d["driver"] == "directives"]
        assert len(dir_drivers) >= 1
        assert dir_drivers[0]["strength"] == 1.0

    def test_lesson_driver(self):
        from divineos.core.attention_schema import _get_attention_drivers
        from divineos.core.knowledge.lessons import record_lesson

        record_lesson("test_category", "Test lesson for attention driver test.", "test-session")
        drivers = _get_attention_drivers()
        lesson_drivers = [d for d in drivers if d["driver"] == "active_lesson"]
        assert len(lesson_drivers) >= 1

    def test_returns_list(self):
        from divineos.core.attention_schema import _get_attention_drivers

        result = _get_attention_drivers()
        assert isinstance(result, list)


class TestPredictAttentionShift:
    """Attention predictions from various signals."""

    def test_predict_from_lesson_drivers(self):
        from divineos.core.attention_schema import predict_attention_shift

        schema = {
            "focus": [],
            "suppressed": [],
            "drivers": [
                {
                    "driver": "active_lesson",
                    "description": "Lesson: Repeated test pattern for prediction.",
                    "effect": "heightened attention",
                    "strength": 0.8,
                }
            ],
        }
        predictions = predict_attention_shift(schema)
        lesson_preds = [p for p in predictions if p["source"] == "lesson_gravity"]
        assert len(lesson_preds) >= 1

    def test_predict_capped_at_5(self):
        from divineos.core.attention_schema import predict_attention_shift

        schema = {
            "focus": [],
            "suppressed": [],
            "drivers": [
                {
                    "driver": "active_lesson",
                    "description": f"Lesson {i}",
                    "effect": "test",
                    "strength": 0.5 + i * 0.05,
                }
                for i in range(10)
            ],
        }
        predictions = predict_attention_shift(schema)
        assert len(predictions) <= 5

    def test_predict_strongest_lesson_wins(self):
        from divineos.core.attention_schema import predict_attention_shift

        schema = {
            "focus": [],
            "suppressed": [],
            "drivers": [
                {
                    "driver": "active_lesson",
                    "description": "Weak lesson",
                    "effect": "test",
                    "strength": 0.2,
                },
                {
                    "driver": "active_lesson",
                    "description": "Strong lesson",
                    "effect": "test",
                    "strength": 0.9,
                },
            ],
        }
        predictions = predict_attention_shift(schema)
        lesson_preds = [p for p in predictions if p["source"] == "lesson_gravity"]
        assert len(lesson_preds) == 1  # only strongest
        assert "Strong lesson" in lesson_preds[0]["prediction"]


class TestFormatAttentionSchema:
    """Format output — coverage of all rendering branches."""

    def test_format_with_all_sections(self):
        from divineos.core.attention_schema import format_attention_schema

        schema = {
            "focus": [
                {
                    "source": "goal",
                    "content": "Build tests",
                    "importance": 0.9,
                    "type": "GOAL",
                    "reason": "user-set",
                },
                {
                    "source": "active_memory",
                    "content": "Use snake_case",
                    "importance": 0.8,
                    "type": "PRINCIPLE",
                    "reason": "auto-promoted",
                },
                {
                    "source": "recent_event",
                    "content": "Test run completed",
                    "importance": 0.6,
                    "type": "TEST_EVENT",
                    "reason": "recency",
                },
            ],
            "suppressed": [
                {
                    "content": "Old fact",
                    "type": "OBSERVATION",
                    "confidence": 0.2,
                    "suppression_reason": "low confidence (0.20)",
                }
            ],
            "drivers": [
                {
                    "driver": "directives",
                    "description": "3 active directives",
                    "effect": "baseline filter",
                    "strength": 1.0,
                }
            ],
            "completeness": {
                "total": 3,
                "succeeded": 3,
                "failed": [],
                "complete": True,
            },
        }
        output = format_attention_schema(schema)
        assert "What I'm Attending To" in output
        assert "Goals (highest priority)" in output
        assert "Active Knowledge" in output
        assert "Recent Events" in output
        assert "Why This Focus" in output
        assert "What I'm NOT Attending To" in output

    def test_format_incomplete_schema(self):
        from divineos.core.attention_schema import format_attention_schema

        schema = {
            "focus": [],
            "suppressed": [],
            "drivers": [],
            "completeness": {
                "total": 3,
                "succeeded": 0,
                "failed": ["focus", "suppressed", "drivers"],
                "complete": False,
            },
        }
        output = format_attention_schema(schema)
        assert "Completeness" in output
        assert "partial" in output

    def test_format_no_data(self):
        from divineos.core.attention_schema import format_attention_schema

        output = format_attention_schema({"focus": [], "suppressed": [], "drivers": []})
        assert "No attention data" in output
