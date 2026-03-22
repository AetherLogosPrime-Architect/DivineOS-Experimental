"""Tests for the HUD (Heads-Up Display) system."""

from divineos.core.hud import (
    SLOT_BUILDERS,
    SLOT_ORDER,
    add_goal,
    build_hud,
    complete_goal,
    load_hud_snapshot,
    save_hud_snapshot,
    update_context_budget,
    update_session_health,
    update_task_state,
)
from divineos.core.memory import init_memory_tables, set_core


class TestSlotBuilders:
    """Each slot builder should return a non-empty string without crashing."""

    def test_all_slots_registered(self):
        for name in SLOT_ORDER:
            assert name in SLOT_BUILDERS, f"Slot '{name}' in SLOT_ORDER but not in SLOT_BUILDERS"

    def test_identity_slot_empty(self):
        init_memory_tables()
        result = SLOT_BUILDERS["identity"]()
        assert "I Am" in result or "haven't set" in result

    def test_identity_slot_with_data(self):
        init_memory_tables()
        set_core("user_identity", "A developer building DivineOS")
        result = SLOT_BUILDERS["identity"]()
        assert "A developer building DivineOS" in result
        assert "My user" in result

    def test_active_goals_slot_empty(self):
        result = SLOT_BUILDERS["active_goals"]()
        assert "Goals" in result

    def test_recent_lessons_slot_empty(self):
        result = SLOT_BUILDERS["recent_lessons"]()
        assert "Learned" in result

    def test_session_health_slot_empty(self):
        result = SLOT_BUILDERS["session_health"]()
        assert "Health" in result or "Session" in result

    def test_context_budget_slot_empty(self):
        result = SLOT_BUILDERS["context_budget"]()
        assert "Context" in result or "Budget" in result

    def test_active_knowledge_slot_empty(self):
        init_memory_tables()
        result = SLOT_BUILDERS["active_knowledge"]()
        assert "Know" in result

    def test_warnings_slot_empty(self):
        result = SLOT_BUILDERS["warnings"]()
        assert "Warning" in result

    def test_task_state_slot_empty(self):
        result = SLOT_BUILDERS["task_state"]()
        assert "Task" in result


class TestBuildHud:
    """The full HUD should render all slots into a single dashboard."""

    def test_full_hud_renders(self):
        init_memory_tables()
        hud = build_hud()
        assert "HEADS-UP DISPLAY" in hud
        assert "===" in hud

    def test_hud_contains_all_sections(self):
        init_memory_tables()
        hud = build_hud()
        # Should have content from multiple slots
        assert "---" in hud  # separator between slots

    def test_hud_specific_slots(self):
        init_memory_tables()
        hud = build_hud(slots=["identity"])
        assert "I Am" in hud or "haven't set" in hud

    def test_hud_ignores_unknown_slots(self):
        init_memory_tables()
        hud = build_hud(slots=["identity", "nonexistent_slot"])
        assert "HEADS-UP DISPLAY" in hud


class TestSlotUpdates:
    """Mutable slots should update and reflect in the HUD."""

    def test_update_session_health(self):
        update_session_health(corrections=2, encouragements=5, grade="B")
        result = SLOT_BUILDERS["session_health"]()
        assert "B" in result
        assert "2" in result

    def test_update_context_budget(self):
        update_context_budget(used_pct=45)
        result = SLOT_BUILDERS["context_budget"]()
        assert "45%" in result
        assert "Plenty" in result or "freely" in result

    def test_context_budget_compression_imminent(self):
        update_context_budget(used_pct=85)
        result = SLOT_BUILDERS["context_budget"]()
        assert "85%" in result
        assert "imminent" in result

    def test_update_task_state(self):
        update_task_state(current="Building HUD", next_task="Run tests")
        result = SLOT_BUILDERS["task_state"]()
        assert "Building HUD" in result
        assert "Run tests" in result

    def test_task_state_accumulates_done(self):
        update_task_state(current="Task A", done=["Task 0"])
        update_task_state(current="Task B", done=["Task A"])
        result = SLOT_BUILDERS["task_state"]()
        assert "Task B" in result
        assert "Task A" in result
        assert "Task 0" in result


class TestGoals:
    """Goal tracking should support add, complete, and display."""

    def test_add_goal(self):
        add_goal("Wire up the HUD system", original_words="yes wire them up")
        result = SLOT_BUILDERS["active_goals"]()
        assert "Wire up the HUD system" in result
        assert "yes wire them up" in result

    def test_complete_goal(self):
        add_goal("Build the dashboard")
        complete_goal("dashboard")
        result = SLOT_BUILDERS["active_goals"]()
        assert "[x]" in result

    def test_complete_nonexistent_goal(self):
        assert complete_goal("something that doesn't exist") is False


class TestSnapshot:
    """HUD snapshots should save and reload."""

    def test_save_and_load_snapshot(self):
        init_memory_tables()
        save_hud_snapshot()
        loaded = load_hud_snapshot()
        assert loaded is not None
        assert "HEADS-UP DISPLAY" in loaded

    def test_load_nonexistent_snapshot(self):
        # With a fresh tmp_path, there's no snapshot yet
        # but the HUD dir might exist from other tests in the session
        # The function should handle missing files gracefully
        from divineos.core.hud import _get_hud_dir

        snapshot_path = _get_hud_dir() / "last_snapshot.md"
        if snapshot_path.exists():
            snapshot_path.unlink()
        result = load_hud_snapshot()
        assert result is None
