"""Tests for circuit-breaker primitive (claim 0d628d8e)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from divineos.core.supervisor import circuit_breaker as cb


@pytest.fixture
def isolated_state(tmp_path):
    """Redirect circuit-breaker state to a tmp file per test."""
    state_file = tmp_path / "circuit_breaker.json"
    with patch.object(cb, "_state_path", return_value=state_file):
        yield state_file


class TestBasicFlow:
    def test_no_state_initially(self, isolated_state) -> None:
        assert cb.get_status() == {}
        assert cb.tripped_modules() == []
        assert cb.is_tripped("anything") is False

    def test_single_failure_does_not_trip(self, isolated_state) -> None:
        tripped = cb.record_failure("sleep_phase_1", reason="db locked")
        assert tripped is False
        assert cb.is_tripped("sleep_phase_1") is False

    def test_threshold_trips_breaker(self, isolated_state) -> None:
        # Default threshold is 3
        cb.record_failure("council_walk", reason="timeout")
        cb.record_failure("council_walk", reason="timeout")
        tripped = cb.record_failure("council_walk", reason="timeout")
        assert tripped is True
        assert cb.is_tripped("council_walk") is True

    def test_success_resets_count(self, isolated_state) -> None:
        cb.record_failure("sleep_phase_3", reason="error")
        cb.record_failure("sleep_phase_3", reason="error")
        cb.record_success("sleep_phase_3")
        # After success, two more failures should NOT trip
        cb.record_failure("sleep_phase_3", reason="new error")
        assert cb.is_tripped("sleep_phase_3") is False

    def test_success_after_trip_clears_tripped(self, isolated_state) -> None:
        for _ in range(cb.DEFAULT_THRESHOLD):
            cb.record_failure("test_mod", reason="x")
        assert cb.is_tripped("test_mod") is True
        cb.record_success("test_mod")
        assert cb.is_tripped("test_mod") is False

    def test_explicit_reset(self, isolated_state) -> None:
        for _ in range(cb.DEFAULT_THRESHOLD):
            cb.record_failure("stuck", reason="repeated")
        assert cb.is_tripped("stuck") is True
        result = cb.reset("stuck")
        assert result is True
        assert cb.is_tripped("stuck") is False

    def test_reset_unknown_module(self, isolated_state) -> None:
        assert cb.reset("never_recorded") is False


class TestThresholds:
    def test_custom_threshold(self, isolated_state) -> None:
        # Lower threshold for a stricter module
        cb.record_failure("strict_mod", reason="x", threshold=2)
        tripped = cb.record_failure("strict_mod", reason="y", threshold=2)
        assert tripped is True

    def test_higher_threshold_more_lenient(self, isolated_state) -> None:
        for _ in range(5):
            cb.record_failure("lenient_mod", reason="x", threshold=10)
        assert cb.is_tripped("lenient_mod") is False


class TestStatusAndIntrospection:
    def test_status_lists_all_modules(self, isolated_state) -> None:
        cb.record_failure("a", reason="r1")
        cb.record_failure("b", reason="r2")
        status = cb.get_status()
        assert set(status.keys()) == {"a", "b"}

    def test_tripped_modules_only_lists_tripped(self, isolated_state) -> None:
        cb.record_failure("ok_mod", reason="x")  # 1 failure, not tripped
        for _ in range(cb.DEFAULT_THRESHOLD):
            cb.record_failure("bad_mod", reason="y")
        assert cb.tripped_modules() == ["bad_mod"]

    def test_reasons_retained_bounded(self, isolated_state) -> None:
        for i in range(cb.MAX_REASONS_RETAINED + 5):
            cb.record_failure("noisy", reason=f"r{i}", threshold=999)
        status = cb.get_status()
        # Cap respected
        assert len(status["noisy"]["reasons"]) == cb.MAX_REASONS_RETAINED
        # Most recent reasons retained
        assert status["noisy"]["reasons"][-1] == f"r{cb.MAX_REASONS_RETAINED + 4}"


class TestStatePersistence:
    def test_state_survives_across_calls(self, isolated_state) -> None:
        cb.record_failure("persisted", reason="x")
        cb.record_failure("persisted", reason="y")
        # Simulate "fresh" call by re-reading state
        status = cb.get_status()
        assert status["persisted"]["failures"] == 2

    def test_get_status_returns_copy(self, isolated_state) -> None:
        cb.record_failure("safe", reason="x")
        status = cb.get_status()
        status["safe"]["failures"] = 999
        # Internal state unaffected
        assert cb.get_status()["safe"]["failures"] == 1


class TestCorruptStateFailSoft:
    def test_corrupt_json_returns_empty(self, tmp_path) -> None:
        state_file = tmp_path / "bad.json"
        state_file.write_text("{not json")
        with patch.object(cb, "_state_path", return_value=state_file):
            assert cb.get_status() == {}
            assert cb.is_tripped("anything") is False

    def test_non_dict_json_returns_empty(self, tmp_path) -> None:
        state_file = tmp_path / "list.json"
        state_file.write_text("[1, 2, 3]")
        with patch.object(cb, "_state_path", return_value=state_file):
            assert cb.get_status() == {}
