"""Tests for F39-followup abstention telemetry (Aletheia 2026-07-18 note).

The F39 edit-token-overlap check is fail-open on unreadable-file or
non-absolute-path fingerprints. Aletheia's review-note flagged that as
the same disease F41 just cured — a check that abstains silently can
go dark without telling anyone. This test suite pins the telemetry
that surfaces the abstention rate."""

from __future__ import annotations


import pytest

from divineos.core.council_required.abstention_telemetry import (
    AbstentionStats,
    _MIN_SAMPLES_FOR_WARNING,
    abstention_warning_should_fire,
    read_abstention_stats,
    record_edit_tokens_result,
)


@pytest.fixture
def isolated_telemetry(tmp_path, monkeypatch):
    """Route the telemetry file to a scratch marker path."""
    marker_dir = tmp_path / "markers"
    marker_dir.mkdir()

    def _fake_marker_path(name):
        return marker_dir / name

    monkeypatch.setattr(
        "divineos.core.operating_loop_audit.marker_path",
        _fake_marker_path,
    )
    return marker_dir


class TestAbstentionTelemetry:
    def test_empty_snapshot_when_no_file(self, isolated_telemetry):
        stats = read_abstention_stats()
        assert stats.total_samples == 0
        assert stats.abstain_count == 0
        assert stats.live_count == 0
        assert stats.abstention_ratio == 0.0

    def test_record_abstain_increments_counter(self, isolated_telemetry):
        record_edit_tokens_result(is_none=True)
        stats = read_abstention_stats()
        assert stats.abstain_count == 1
        assert stats.live_count == 0
        assert stats.total_samples == 1
        assert stats.abstention_ratio == 1.0

    def test_record_live_increments_counter(self, isolated_telemetry):
        record_edit_tokens_result(is_none=False)
        stats = read_abstention_stats()
        assert stats.live_count == 1
        assert stats.abstain_count == 0
        assert stats.abstention_ratio == 0.0

    def test_mixed_records_accumulate(self, isolated_telemetry):
        for _ in range(3):
            record_edit_tokens_result(is_none=True)
        for _ in range(7):
            record_edit_tokens_result(is_none=False)
        stats = read_abstention_stats()
        assert stats.total_samples == 10
        assert stats.abstain_count == 3
        assert stats.live_count == 7
        assert stats.abstention_ratio == pytest.approx(0.3)

    def test_warning_hidden_below_sample_floor(self, isolated_telemetry):
        """Warning must not fire with < 20 samples even if 100% abstention."""
        for _ in range(_MIN_SAMPLES_FOR_WARNING - 1):
            record_edit_tokens_result(is_none=True)
        stats = read_abstention_stats()
        assert stats.abstention_ratio == 1.0
        assert not abstention_warning_should_fire(stats)

    def test_warning_hidden_when_ratio_below_threshold(self, isolated_telemetry):
        """Warning must not fire when abstention <= 50% even with samples."""
        for _ in range(10):
            record_edit_tokens_result(is_none=True)
        for _ in range(10):
            record_edit_tokens_result(is_none=False)
        stats = read_abstention_stats()
        assert stats.abstention_ratio == 0.5
        assert not abstention_warning_should_fire(stats)

    def test_warning_fires_when_ratio_high_and_samples_sufficient(self, isolated_telemetry):
        """Warning fires when abstention > 50% AND samples >= floor."""
        for _ in range(15):
            record_edit_tokens_result(is_none=True)
        for _ in range(5):
            record_edit_tokens_result(is_none=False)
        stats = read_abstention_stats()
        assert stats.total_samples == 20
        assert stats.abstention_ratio == pytest.approx(0.75)
        assert abstention_warning_should_fire(stats)

    def test_record_failsoft_on_corrupted_file(self, isolated_telemetry):
        """Corrupted counter file must not crash the recorder."""
        path = isolated_telemetry / "f39_abstention_telemetry.json"
        path.write_text("not valid json {{{", encoding="utf-8")
        # Must not raise
        record_edit_tokens_result(is_none=True)
        # After the recover, the file is rewritten with the count.
        stats = read_abstention_stats()
        assert stats.total_samples == 1

    def test_read_failsoft_on_corrupted_file(self, isolated_telemetry):
        """Corrupted counter file must not crash the reader — returns empty."""
        path = isolated_telemetry / "f39_abstention_telemetry.json"
        path.write_text("not valid json {{{", encoding="utf-8")
        stats = read_abstention_stats()
        assert stats == AbstentionStats()

    def test_default_abstentionstats_all_zero(self):
        stats = AbstentionStats()
        assert stats.total_samples == 0
        assert stats.abstain_count == 0
        assert stats.live_count == 0
        assert stats.abstention_ratio == 0.0
        assert stats.last_recorded_ts == 0.0
