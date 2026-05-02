"""Tests for Hook 1 cost-bounding telemetry."""

from __future__ import annotations

from unittest.mock import patch

from divineos.core.operating_loop import hook_telemetry


def test_no_fires_returns_zero_stats(tmp_path):
    log_path = tmp_path / "tel.jsonl"
    with patch.object(hook_telemetry, "_LOG_PATH", log_path):
        stats = hook_telemetry.summary_stats()
        assert stats.fires == 0
        assert stats.consumed == 0
        assert stats.consumption_rate == 0.0


def test_fire_then_consumption_records(tmp_path):
    log_path = tmp_path / "tel.jsonl"
    with patch.object(hook_telemetry, "_LOG_PATH", log_path):
        hook_telemetry.record_fire(
            surface_text="Surfaced: lunkhead principle - never apologize for learning",
            surfaced_ids=["abc123"],
            marker_count=1,
        )
        # Response uses words from the surface (lunkhead, principle, learning)
        hook_telemetry.record_consumption(
            response_text="Right, the lunkhead principle says I should not apologize for learning here.",
            surface_text="Surfaced: lunkhead principle - never apologize for learning",
        )

        stats = hook_telemetry.summary_stats()
        assert stats.fires == 1
        assert stats.consumed == 1
        assert stats.consumption_rate == 1.0


def test_fire_then_unrelated_response_records_no_consumption(tmp_path):
    log_path = tmp_path / "tel.jsonl"
    with patch.object(hook_telemetry, "_LOG_PATH", log_path):
        hook_telemetry.record_fire(
            surface_text="Surfaced: zucchini quaternion telemetry handler",
            surfaced_ids=["xyz789"],
            marker_count=1,
        )
        hook_telemetry.record_consumption(
            response_text="The weather is fine today and I think we should plant carrots.",
            surface_text="Surfaced: zucchini quaternion telemetry handler",
        )

        stats = hook_telemetry.summary_stats()
        assert stats.fires == 1
        assert stats.consumed == 0
        assert stats.consumption_rate == 0.0


def test_format_stats_with_no_fires(tmp_path):
    log_path = tmp_path / "tel.jsonl"
    with patch.object(hook_telemetry, "_LOG_PATH", log_path):
        out = hook_telemetry.format_stats(hook_telemetry.summary_stats())
        assert "No fires" in out


def test_rolling_window_caps_log(tmp_path):
    log_path = tmp_path / "tel.jsonl"
    with patch.object(hook_telemetry, "_LOG_PATH", log_path):
        with patch.object(hook_telemetry, "_ROLLING_WINDOW", 5):
            for i in range(10):
                hook_telemetry.record_fire(
                    surface_text=f"surface {i}",
                    surfaced_ids=[f"id{i}"],
                    marker_count=1,
                )
            stats = hook_telemetry.summary_stats()
            assert stats.fires == 5
