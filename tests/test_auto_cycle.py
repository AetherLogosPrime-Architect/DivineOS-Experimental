"""Tests for auto_cycle phase 1 — trigger + pipeline + handshake marker."""

from __future__ import annotations

import pytest

from divineos.core.auto_cycle import (
    FULL_CYCLE_BUDGET_TOKENS,
    MAX_DEFERS,
    Phase1Result,
    StepResult,
    TRIGGER_THRESHOLD,
    clear_handshake_marker,
    load_defer_state,
    read_handshake_marker,
    reset_defer_state,
    run_phase1,
    save_defer_state,
    should_fire,
    write_handshake_marker,
)


# --- trigger logic ---------------------------------------------------------


def test_should_fire_below_threshold_returns_false():
    fire, reason = should_fire(context_pct=0.5, has_active_goal_progress=False, defers_used=0)
    assert fire is False
    assert "below threshold" in reason


def test_should_fire_at_threshold_no_active_work_fires():
    fire, reason = should_fire(
        context_pct=TRIGGER_THRESHOLD, has_active_goal_progress=False, defers_used=0
    )
    assert fire is True
    assert "no active work" in reason


def test_should_fire_defers_when_active_goal_progress():
    fire, reason = should_fire(
        context_pct=TRIGGER_THRESHOLD + 0.01, has_active_goal_progress=True, defers_used=0
    )
    assert fire is False
    assert "deferring" in reason


def test_should_fire_defers_exhausted_fires_regardless_of_active_work():
    # Andrew 2026-07-10: the optimizer can't fake-active-work indefinitely
    # because the defer caps. Test the cap-enforcement branch.
    fire, reason = should_fire(
        context_pct=TRIGGER_THRESHOLD + 0.01,
        has_active_goal_progress=True,
        defers_used=MAX_DEFERS,
    )
    assert fire is True
    assert "exhausted" in reason


def test_should_fire_defer_counter_increments_in_reason():
    _, reason = should_fire(context_pct=0.9, has_active_goal_progress=True, defers_used=1)
    assert "2/3" in reason  # (defers_used + 1) / MAX_DEFERS


# --- defer state persistence -----------------------------------------------


def test_load_defer_state_missing_returns_default(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "divineos.core.auto_cycle.defer_state_path", lambda: tmp_path / "defer.json"
    )
    state = load_defer_state()
    assert state["defers_used"] == 0
    assert state["last_defer_at"] is None


def test_save_and_load_defer_state_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "divineos.core.auto_cycle.defer_state_path", lambda: tmp_path / "defer.json"
    )
    save_defer_state({"defers_used": 2, "last_defer_at": 12345.0, "cycle_start_ts": 12000.0})
    state = load_defer_state()
    assert state["defers_used"] == 2
    assert state["last_defer_at"] == 12345.0


def test_reset_defer_state_removes_file(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "divineos.core.auto_cycle.defer_state_path", lambda: tmp_path / "defer.json"
    )
    save_defer_state({"defers_used": 3, "last_defer_at": 0.0, "cycle_start_ts": 0.0})
    reset_defer_state()
    assert not (tmp_path / "defer.json").exists()


def test_reset_defer_state_no_file_no_raise(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "divineos.core.auto_cycle.defer_state_path", lambda: tmp_path / "defer.json"
    )
    reset_defer_state()  # must not raise on missing file


# --- pipeline dry-run ------------------------------------------------------


def test_run_phase1_dry_run_records_all_steps_would_run():
    result = run_phase1(context_pct=0.85, dry_run=True)
    assert isinstance(result, Phase1Result)
    assert set(result.steps.keys()) == {"commit", "extract", "sleep"}
    for step in result.steps.values():
        assert step.ran is False  # dry-run
        assert step.succeeded is True  # would succeed
        assert "[dry-run]" in step.output_tail


def test_run_phase1_dry_run_cycle_id_is_unique():
    r1 = run_phase1(context_pct=0.85, dry_run=True)
    r2 = run_phase1(context_pct=0.85, dry_run=True)
    assert r1.cycle_id != r2.cycle_id
    assert r1.cycle_id.startswith("auto-cycle-")


def test_run_phase1_records_trigger_context_pct():
    result = run_phase1(context_pct=0.87, dry_run=True)
    assert result.trigger_context_pct == 0.87


# --- handshake marker ------------------------------------------------------


def test_write_and_read_handshake_marker_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr("divineos.core.auto_cycle.marker_path", lambda: tmp_path / "marker.json")
    result = run_phase1(context_pct=0.85, session_id="test-session", dry_run=True)
    write_handshake_marker(result)
    payload = read_handshake_marker()
    assert payload is not None
    assert payload["cycle_id"] == result.cycle_id
    assert payload["trigger_context_pct"] == 0.85
    assert payload["session_id"] == "test-session"
    assert set(payload["steps"].keys()) == {"commit", "extract", "sleep"}
    # Per Aria's schema-confirm: both optional fields must be present.
    for step in payload["steps"].values():
        assert "duration_sec" in step
        assert "error_class" in step


def test_read_handshake_marker_missing_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr("divineos.core.auto_cycle.marker_path", lambda: tmp_path / "marker.json")
    assert read_handshake_marker() is None


def test_read_handshake_marker_corrupt_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr("divineos.core.auto_cycle.marker_path", lambda: tmp_path / "marker.json")
    (tmp_path / "marker.json").write_text("not valid json {", encoding="utf-8")
    assert read_handshake_marker() is None


def test_clear_handshake_marker_removes_file(tmp_path, monkeypatch):
    monkeypatch.setattr("divineos.core.auto_cycle.marker_path", lambda: tmp_path / "marker.json")
    (tmp_path / "marker.json").write_text('{"cycle_id": "test"}', encoding="utf-8")
    clear_handshake_marker()
    assert not (tmp_path / "marker.json").exists()


def test_clear_handshake_marker_missing_no_raise(tmp_path, monkeypatch):
    monkeypatch.setattr("divineos.core.auto_cycle.marker_path", lambda: tmp_path / "marker.json")
    clear_handshake_marker()  # must not raise on missing file


# --- StepResult dataclass shape --------------------------------------------


def test_step_result_all_fields_present():
    step = StepResult(
        ran=True,
        succeeded=True,
        output_tail="ok",
        tokens_used_est=100,
        duration_sec=1.5,
        error_class=None,
    )
    # Frozen dataclass — immutable
    with pytest.raises(AttributeError):
        step.succeeded = False  # type: ignore[misc]


def test_phase1_result_default_values():
    r = Phase1Result(
        phase1_completed_at="2026-07-10T20:00:00Z",
        trigger_context_pct=0.85,
        cycle_id="auto-cycle-abcdef12",
    )
    assert r.steps == {}
    assert r.phase1_tokens_used_est == 0
    assert r.session_id is None


# --- budget-remaining computation ------------------------------------------


def test_budget_remaining_reflects_total_used(tmp_path, monkeypatch):
    monkeypatch.setattr("divineos.core.auto_cycle.marker_path", lambda: tmp_path / "marker.json")
    result = run_phase1(context_pct=0.85, dry_run=True)
    # dry-run uses 0 tokens per step
    assert result.phase1_tokens_used_est == 0
    assert result.budget_remaining_est == FULL_CYCLE_BUDGET_TOKENS
