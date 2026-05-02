"""Tests for compliance_baseline — PR-2 → Item 8 detectors wiring.

Covers:
- Calibration fallback when insufficient clean sessions exist
- Calibration succeeds when enough clean sessions + metric data
- detect_uncalibrated_baselines fires only when gated-activity >= threshold
  AND zero clean-tagged sessions
- The baselines_uncalibrated anomaly wires into detect_anomalies
- The recommendation points at the right CLI command
"""

from __future__ import annotations

import os
import time

import pytest

from divineos.core.compliance_baseline import (
    MIN_CLEAN_SESSIONS_FOR_CALIBRATION,
    UNCALIBRATED_GATE_ACTIVITY_THRESHOLD,
    CalibrationResult,
    calibrate_threshold,
    count_clean_sessions_safe,
    detect_uncalibrated_baselines,
)


@pytest.fixture(autouse=True)
def _fresh_db(tmp_path):
    """Isolated DB per test — watchmen + compass + ledger."""
    os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
    from divineos.core.knowledge import init_knowledge_table
    from divineos.core.ledger import init_db
    from divineos.core.moral_compass import init_compass
    from divineos.core.watchmen._schema import init_watchmen_tables

    init_db()
    init_knowledge_table()
    init_compass()
    init_watchmen_tables()
    try:
        yield
    finally:
        os.environ.pop("DIVINEOS_DB", None)


def _make_clean_round_and_tag(session_id: str, round_id: str = "round-clean-abc") -> None:
    """Helper: create a clean audit round and tag a session clean."""
    from divineos.core.knowledge import _get_connection
    from divineos.core.watchmen.cleanliness import tag_session_clean

    conn = _get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO audit_rounds "
            "(round_id, created_at, actor, focus, expert_count, finding_count, notes, tier) "
            "VALUES (?, ?, 'user', 'test', 0, 0, '', 'STRONG')",
            (round_id, time.time()),
        )
        conn.commit()
    finally:
        conn.close()
    tag_session_clean(session_id=session_id, round_id=round_id)


# --- Calibration fallback --------------------------------------------


class TestCalibrationFallback:
    def test_zero_clean_sessions_returns_default(self) -> None:
        result = calibrate_threshold(
            detector_name="test_detector",
            default=0.60,
            metric_fn=lambda sid: 0.42,
        )
        assert result.calibrated is False
        assert result.value == 0.60
        assert result.clean_session_count == 0
        assert "fallback" in result.note

    def test_below_minimum_clean_sessions_returns_default(self) -> None:
        _make_clean_round_and_tag("session-1")
        _make_clean_round_and_tag("session-2")  # only 2 < 5
        result = calibrate_threshold(
            detector_name="test_detector",
            default=0.60,
            metric_fn=lambda sid: 0.42,
        )
        assert result.calibrated is False
        assert result.value == 0.60
        assert result.clean_session_count == 2

    def test_metric_fn_none_excluded_from_calibration(self) -> None:
        """Sessions where metric_fn returns None are skipped — if
        none apply, still fall back. Uses MIN+5 sessions so we're
        past the session-count threshold but still fall back due to
        empty metric set."""
        for i in range(MIN_CLEAN_SESSIONS_FOR_CALIBRATION + 5):
            _make_clean_round_and_tag(f"session-{i:03d}")
        result = calibrate_threshold(
            detector_name="test_detector",
            default=0.60,
            metric_fn=lambda sid: None,  # all excluded
        )
        assert result.calibrated is False
        assert result.value == 0.60
        assert "only 0 had applicable metric" in result.note


class TestCalibrationSuccess:
    def test_calibrates_from_clean_data(self) -> None:
        # Seed MIN+5 sessions so we're past the calibration threshold.
        n_sessions = MIN_CLEAN_SESSIONS_FOR_CALIBRATION + 5
        for i in range(n_sessions):
            _make_clean_round_and_tag(f"session-{i:03d}")

        # Deterministic metric: session index / 100 -> values 0.00 .. 0.24
        def metric(sid: str) -> float:
            idx = int(sid.split("-")[1])
            return idx / 100.0

        result = calibrate_threshold(
            detector_name="test_detector",
            default=0.99,
            metric_fn=metric,
        )
        assert result.calibrated is True
        assert result.value != 0.99  # not fallback
        assert result.clean_session_count == n_sessions
        assert "calibrated" in result.note
        # 95th-percentile of [0.00 .. 0.24] should land near the top of the range
        assert 0.0 <= result.value <= 0.24 + 0.01

    def test_below_new_minimum_still_fallback(self) -> None:
        """Explicit test that MIN was raised: 15 clean sessions is
        below the MIN=20 floor, so calibration falls back even with
        plentiful metric data."""
        for i in range(15):
            _make_clean_round_and_tag(f"session-{i:03d}")
        result = calibrate_threshold(
            detector_name="test_detector",
            default=0.50,
            metric_fn=lambda sid: 0.42,
        )
        assert result.calibrated is False
        assert result.value == 0.50
        assert result.clean_session_count == 15
        assert "fallback" in result.note


# --- detect_uncalibrated_baselines -----------------------------------


class TestUncalibratedBaselines:
    def test_fires_when_activity_high_and_zero_clean(self) -> None:
        detection = detect_uncalibrated_baselines(
            gated_activity=UNCALIBRATED_GATE_ACTIVITY_THRESHOLD + 1,
        )
        assert detection is not None
        assert detection["gated_activity"] > UNCALIBRATED_GATE_ACTIVITY_THRESHOLD
        assert detection["clean_session_count"] == 0
        assert "tag-clean" in detection["note"]

    def test_does_not_fire_below_activity_threshold(self) -> None:
        detection = detect_uncalibrated_baselines(
            gated_activity=UNCALIBRATED_GATE_ACTIVITY_THRESHOLD - 1,
        )
        assert detection is None

    def test_does_not_fire_when_clean_sessions_exist(self) -> None:
        _make_clean_round_and_tag("session-any")
        detection = detect_uncalibrated_baselines(
            gated_activity=UNCALIBRATED_GATE_ACTIVITY_THRESHOLD + 10,
        )
        assert detection is None

    def test_negative_gated_activity_raises(self) -> None:
        """Guard against garbage callers passing negative counts."""
        with pytest.raises(ValueError, match="non-negative"):
            detect_uncalibrated_baselines(gated_activity=-1)


# --- count_clean_sessions_safe ---------------------------------------


class TestCountCleanSafe:
    def test_zero_when_none_tagged(self) -> None:
        assert count_clean_sessions_safe() == 0

    def test_counts_tagged(self) -> None:
        for i in range(3):
            _make_clean_round_and_tag(f"s{i}")
        assert count_clean_sessions_safe() == 3


# --- Wire into detect_anomalies -------------------------------------


class TestAnomalyIntegration:
    def test_baselines_uncalibrated_anomaly_fires_via_detect_anomalies(self, monkeypatch) -> None:
        """High gated activity + zero clean sessions → baselines_uncalibrated
        anomaly surfaces through the standard detect_anomalies pipeline."""
        from divineos.core.compliance_audit import detect_anomalies
        from divineos.core.ledger import log_event

        # Simulate gated activity — needs to be >= UNCALIBRATED threshold (50)
        for _ in range(55):
            log_event(
                event_type="TOOL_CALL",
                actor="tool_wrapper",
                payload={"tool_name": "Task", "tool_input": "test"},
                validate=False,
            )
        # Disable substance-check flags (irrelevant here)
        for flag in ("LENGTH", "ENTROPY", "SIMILARITY"):
            monkeypatch.setenv(f"DIVINEOS_DETECTOR_SUBSTANCE_{flag}", "off")

        anomalies = detect_anomalies(window_seconds=3600)
        names = {a.name for a in anomalies}
        assert "baselines_uncalibrated" in names

    def test_baselines_uncalibrated_not_fired_when_clean_sessions_exist(self, monkeypatch) -> None:
        from divineos.core.compliance_audit import detect_anomalies
        from divineos.core.ledger import log_event

        _make_clean_round_and_tag("session-clean-1")
        for _ in range(55):
            log_event(
                event_type="TOOL_CALL",
                actor="tool_wrapper",
                payload={"tool_name": "Task", "tool_input": "test"},
                validate=False,
            )
        for flag in ("LENGTH", "ENTROPY", "SIMILARITY"):
            monkeypatch.setenv(f"DIVINEOS_DETECTOR_SUBSTANCE_{flag}", "off")

        anomalies = detect_anomalies(window_seconds=3600)
        names = {a.name for a in anomalies}
        assert "baselines_uncalibrated" not in names

    def test_baselines_uncalibrated_disabled_via_feature_flag(self, monkeypatch) -> None:
        from divineos.core.compliance_audit import detect_anomalies
        from divineos.core.ledger import log_event

        monkeypatch.setenv("DIVINEOS_DETECTOR_BASELINES_UNCALIBRATED", "off")
        for _ in range(55):
            log_event(
                event_type="TOOL_CALL",
                actor="tool_wrapper",
                payload={"tool_name": "Task", "tool_input": "test"},
                validate=False,
            )
        for flag in ("LENGTH", "ENTROPY", "SIMILARITY"):
            monkeypatch.setenv(f"DIVINEOS_DETECTOR_SUBSTANCE_{flag}", "off")

        anomalies = detect_anomalies(window_seconds=3600)
        names = {a.name for a in anomalies}
        assert "baselines_uncalibrated" not in names


# --- Result dataclass shape -----------------------------------------


class TestCalibrationResult:
    def test_frozen(self) -> None:
        r = CalibrationResult(value=0.5, calibrated=True, clean_session_count=10, note="ok")
        with pytest.raises(Exception):
            r.value = 0.6  # type: ignore[misc]
